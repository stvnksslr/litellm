"""
Tests for the per-model ``model_info.skip_budget_checks`` marker.

An admin can mark a model so requests to it are admitted even when the caller
is over budget. Unlike the explicit-zero-cost bypass (_is_model_cost_zero),
this is a direct opt-in and does NOT depend on the model's cost — so it covers
models with unknown/unmapped cost without reopening issue #24770 (unmapped
models must otherwise keep enforcing budget).
"""

import copy
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import litellm
from litellm.caching.caching import DualCache
from litellm.proxy._types import LiteLLM_UserTable, UserAPIKeyAuth
from litellm.proxy.auth.auth_checks import (
    _is_model_budget_exempt,
    common_checks,
    should_skip_budget_checks_for_model,
)
from litellm.proxy.auth.user_api_key_auth import _should_skip_budget_checks
from litellm.proxy.hooks.max_budget_limiter import _PROXY_MaxBudgetLimiter
from litellm.proxy.utils import ProxyLogging
from litellm.router import Router
from litellm.types.router import Deployment, LiteLLM_Params, ModelInfo


@pytest.fixture(autouse=True)
def _isolate_model_cost():
    """Snapshot/restore litellm.model_cost so Router registrations in one test
    (sparse cost-map entries) don't leak into the next and perturb the
    #24770 _is_cost_explicitly_configured path."""
    saved = copy.deepcopy(litellm.model_cost)
    try:
        yield
    finally:
        litellm.model_cost.clear()
        litellm.model_cost.update(saved)


def _router_with_marker():
    """A real, cost-mapped model (gpt-4o-mini) exposed twice: one marked
    budget-exempt, one not. Using a priced model proves the marker bypasses
    budget independently of cost."""
    return Router(
        model_list=[
            {
                "model_name": "exempt-model",
                "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "sk-fake"},
                "model_info": {"id": "exempt-id", "skip_budget_checks": True},
            },
            {
                "model_name": "paid-model",
                "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "sk-fake"},
                "model_info": {"id": "paid-id"},
            },
            {
                "model_name": "unmapped-model",
                "litellm_params": {
                    "model": "openai/totally-nonexistent-model-xyz",
                    "api_key": "sk-fake",
                },
                "model_info": {"id": "unmapped-id"},
            },
        ]
    )


class TestIsModelBudgetExempt:
    def test_marked_model_is_exempt(self):
        assert _is_model_budget_exempt("exempt-model", _router_with_marker()) is True

    def test_unmarked_paid_model_not_exempt(self):
        assert _is_model_budget_exempt("paid-model", _router_with_marker()) is False

    def test_unmarked_unmapped_model_not_exempt(self):
        """Regression for #24770: unknown-cost models must NOT be exempted
        unless explicitly marked."""
        assert _is_model_budget_exempt("unmapped-model", _router_with_marker()) is False

    def test_unknown_model_name_not_exempt(self):
        assert _is_model_budget_exempt("does-not-exist", _router_with_marker()) is False

    def test_none_inputs_not_exempt(self):
        router = _router_with_marker()
        assert _is_model_budget_exempt(None, router) is False
        assert _is_model_budget_exempt("exempt-model", None) is False

    def test_list_all_marked_exempt(self):
        assert _is_model_budget_exempt(["exempt-model"], _router_with_marker()) is True

    def test_list_with_one_unmarked_not_exempt(self):
        assert (
            _is_model_budget_exempt(
                ["exempt-model", "paid-model"], _router_with_marker()
            )
            is False
        )

    def test_partial_group_not_exempt(self):
        """A model_name backed by two deployments where only one is marked must
        NOT be exempt (refuse to bypass a partially-marked group)."""
        router = Router(
            model_list=[
                {
                    "model_name": "grp",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "sk-fake",
                    },
                    "model_info": {"id": "g1", "skip_budget_checks": True},
                },
                {
                    "model_name": "grp",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "sk-fake",
                    },
                    "model_info": {"id": "g2"},
                },
            ]
        )
        assert _is_model_budget_exempt("grp", router) is False

    def test_db_model_path_is_exempt(self):
        """DB-stored models reach the router via
        upsert_deployment(Deployment(model_info=ModelInfo(**dict))). The marker
        must survive that path (proves UI/DB models are covered, not just
        config-file models)."""
        router = Router(model_list=[])
        router.upsert_deployment(
            deployment=Deployment(
                model_name="db-exempt-model",
                litellm_params=LiteLLM_Params(
                    model="openai/gpt-4o-mini", api_key="sk-fake"
                ),
                model_info=ModelInfo(**{"id": "db1", "skip_budget_checks": True}),
            )
        )
        assert _is_model_budget_exempt("db-exempt-model", router) is True


class TestShouldSkipBudgetChecksForModel:
    def test_marked_model_skips(self):
        assert (
            should_skip_budget_checks_for_model("exempt-model", _router_with_marker())
            is True
        )

    def test_paid_model_does_not_skip(self):
        assert (
            should_skip_budget_checks_for_model("paid-model", _router_with_marker())
            is False
        )

    def test_explicit_zero_cost_still_skips(self):
        """The existing explicit-zero-cost bypass must keep working."""
        router = Router(
            model_list=[
                {
                    "model_name": "free-model",
                    "litellm_params": {
                        "model": "ollama/llama2",
                        "api_base": "http://localhost:11434",
                        "input_cost_per_token": 0.0,
                        "output_cost_per_token": 0.0,
                    },
                    "model_info": {
                        "id": "free-id",
                        "input_cost_per_token": 0.0,
                        "output_cost_per_token": 0.0,
                    },
                }
            ]
        )
        assert should_skip_budget_checks_for_model("free-model", router) is True
        # ...without being marked budget-exempt.
        assert _is_model_budget_exempt("free-model", router) is False


class TestShouldSkipBudgetChecksWiring:
    """The auth-layer entrypoint that computes skip from the request model."""

    def test_marked_model_request_skips(self):
        assert (
            _should_skip_budget_checks(
                request_data={"model": "exempt-model"},
                route="/v1/chat/completions",
                request=MagicMock(),
                llm_router=_router_with_marker(),
            )
            is True
        )

    def test_unmapped_model_request_does_not_skip(self):
        assert (
            _should_skip_budget_checks(
                request_data={"model": "unmapped-model"},
                route="/v1/chat/completions",
                request=MagicMock(),
                llm_router=_router_with_marker(),
            )
            is False
        )


class TestMaxBudgetLimiterHookBypass:
    """The actual bug: the _PROXY_MaxBudgetLimiter pre-call hook enforces the
    personal user budget independently of the auth-layer skip decision. A
    marked model must not be 429'd here either."""

    @pytest.fixture(autouse=True)
    def _wire_proxy_globals(self, monkeypatch):
        import litellm.proxy.proxy_server as proxy_server

        async def _over_budget_spend(counter_key, fallback_spend):
            return 100.0

        monkeypatch.setattr(proxy_server, "llm_router", _router_with_marker())
        monkeypatch.setattr(proxy_server, "get_current_spend", _over_budget_spend)

    def _over_budget_user_token(self):
        return UserAPIKeyAuth(
            token="test-token",
            user_id="test-user",
            team_id=None,
            user_max_budget=10.0,
            user_spend=100.0,
        )

    @pytest.mark.asyncio
    async def test_over_budget_user_allowed_on_marked_model(self):
        hook = _PROXY_MaxBudgetLimiter()
        # Must not raise despite spend (100) >> budget (10).
        await hook.async_pre_call_hook(
            user_api_key_dict=self._over_budget_user_token(),
            cache=DualCache(),
            data={"model": "exempt-model"},
            call_type="completion",
        )

    @pytest.mark.asyncio
    async def test_over_budget_user_blocked_on_unmarked_model(self):
        hook = _PROXY_MaxBudgetLimiter()
        with pytest.raises(HTTPException) as exc_info:
            await hook.async_pre_call_hook(
                user_api_key_dict=self._over_budget_user_token(),
                cache=DualCache(),
                data={"model": "paid-model"},
                call_type="completion",
            )
        assert exc_info.value.status_code == 429


class TestCommonChecksEndToEnd:
    @pytest.fixture
    def proxy_logging(self):
        proxy_logging = ProxyLogging(user_api_key_cache=None)

        async def _noop(*args, **kwargs):
            pass

        proxy_logging.budget_alerts = _noop
        return proxy_logging

    @pytest.mark.asyncio
    async def test_over_budget_user_allowed_on_marked_model(self, proxy_logging):
        router = _router_with_marker()
        user_object = LiteLLM_UserTable(
            user_id="test-user", spend=100.0, max_budget=50.0
        )
        request_data = {"model": "exempt-model"}
        skip = _should_skip_budget_checks(
            request_data=request_data,
            route="/v1/chat/completions",
            request=MagicMock(),
            llm_router=router,
        )
        assert skip is True

        result = await common_checks(
            request_body=request_data,
            team_object=None,
            user_object=user_object,
            end_user_object=None,
            global_proxy_spend=None,
            general_settings={},
            route="/v1/chat/completions",
            llm_router=router,
            proxy_logging_obj=proxy_logging,
            valid_token=UserAPIKeyAuth(token="test-token", user_id="test-user"),
            request=MagicMock(),
            skip_budget_checks=skip,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_over_budget_user_blocked_on_unmapped_model(self, proxy_logging):
        router = _router_with_marker()
        user_object = LiteLLM_UserTable(
            user_id="test-user", spend=100.0, max_budget=50.0
        )
        request_data = {"model": "unmapped-model"}
        skip = _should_skip_budget_checks(
            request_data=request_data,
            route="/v1/chat/completions",
            request=MagicMock(),
            llm_router=router,
        )
        assert skip is False

        with pytest.raises(litellm.BudgetExceededError):
            await common_checks(
                request_body=request_data,
                team_object=None,
                user_object=user_object,
                end_user_object=None,
                global_proxy_spend=None,
                general_settings={},
                route="/v1/chat/completions",
                llm_router=router,
                proxy_logging_obj=proxy_logging,
                valid_token=UserAPIKeyAuth(token="test-token", user_id="test-user"),
                request=MagicMock(),
                skip_budget_checks=skip,
            )

    @pytest.mark.asyncio
    async def test_over_budget_user_blocked_on_spend_route(self, proxy_logging):
        """Enforcement guard: an over-budget user is still 429'd on a route that
        consumes budget. Catches a mutation that over-broadens the skip."""
        router = _router_with_marker()
        user_object = LiteLLM_UserTable(
            user_id="test-user", spend=100.0, max_budget=50.0
        )
        with pytest.raises(litellm.BudgetExceededError):
            await common_checks(
                request_body={"model": "paid-model"},
                team_object=None,
                user_object=user_object,
                end_user_object=None,
                global_proxy_spend=None,
                general_settings={},
                route="/v1/chat/completions",
                llm_router=router,
                proxy_logging_obj=proxy_logging,
                valid_token=UserAPIKeyAuth(token="test-token", user_id="test-user"),
                request=MagicMock(),
                skip_budget_checks=False,
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", ["/key/info", "/user/info", "/spend/logs"])
    async def test_over_budget_user_allowed_on_info_route(self, proxy_logging, route):
        """The bug: budget exhaustion must not block read-only, non-spend routes.
        These return 429 before the is_llm_api_route gate is applied."""
        router = _router_with_marker()
        user_object = LiteLLM_UserTable(
            user_id="test-user", spend=100.0, max_budget=50.0
        )
        request = MagicMock()
        request.query_params = {}
        result = await common_checks(
            request_body={},
            team_object=None,
            user_object=user_object,
            end_user_object=None,
            global_proxy_spend=None,
            general_settings={},
            route=route,
            llm_router=router,
            proxy_logging_obj=proxy_logging,
            valid_token=UserAPIKeyAuth(token="test-token", user_id="test-user"),
            request=request,
            skip_budget_checks=False,
        )
        assert result is True


def test_model_info_marker_round_trips():
    """ModelInfo accepts and exposes the marker."""
    mi = ModelInfo(**{"id": "x", "skip_budget_checks": True})
    assert mi.get("skip_budget_checks") is True
    assert mi.skip_budget_checks is True
    assert ModelInfo(id="y").get("skip_budget_checks") is None


def _deployment(model_name: str, model_id: str, **model_info):
    return {
        "model_name": model_name,
        "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "sk-fake"},
        "model_info": {"id": model_id, **model_info},
    }


ALIAS_MODELS = [
    _deployment("exempt-model", "e1", skip_budget_checks=True),
    _deployment("exempt-model-2", "e2", skip_budget_checks=True),
    _deployment("paid-model", "p1"),
    _deployment(
        "team-deployment",
        "t1",
        team_id="team-1",
        team_public_model_name="team-exempt",
        skip_budget_checks=True,
    ),
    {
        "model_name": "zero-cost-model",
        "litellm_params": {
            "model": "openai/gpt-4o-mini",
            "api_key": "sk-fake",
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
        },
        "model_info": {
            "id": "z1",
            "input_cost_per_token": 0.0,
            "output_cost_per_token": 0.0,
        },
    },
]


def _alias_router(**router_kwargs):
    return Router(
        model_list=copy.deepcopy(ALIAS_MODELS),
        model_group_alias={
            "alias-of-exempt": "exempt-model",
            "alias-of-zero-cost": "zero-cost-model",
        },
        **router_kwargs,
    )


class TestSkipResolvesAliases:
    """The exemption must survive every way a model can be renamed, otherwise an
    admin marks a model exempt and over-budget callers are still blocked when
    they reach it through its alias."""

    def test_router_model_group_alias_of_exempt_model_skips(self):
        assert (
            should_skip_budget_checks_for_model("alias-of-exempt", _alias_router())
            is True
        )

    def test_router_model_group_alias_of_zero_cost_model_skips(self):
        """_is_cost_explicitly_configured used to match deployments by raw
        model_name, which never equals an alias — so the zero-cost half of the
        gate silently stopped working through model_group_alias."""
        assert (
            should_skip_budget_checks_for_model("alias-of-zero-cost", _alias_router())
            is True
        )

    def test_team_public_model_name_skips_for_that_team(self):
        """UI-created team models are addressed by team_public_model_name, which
        only resolves when team_id is supplied to the router."""
        assert (
            should_skip_budget_checks_for_model(
                "team-exempt", _alias_router(), team_id="team-1"
            )
            is True
        )

    def test_team_public_model_name_does_not_skip_for_other_team(self):
        assert (
            should_skip_budget_checks_for_model(
                "team-exempt", _alias_router(), team_id="team-2"
            )
            is False
        )

    def test_litellm_model_alias_map_skips(self, monkeypatch):
        """litellm.model_alias_map is applied after auth, so the gate has to
        resolve it itself."""
        monkeypatch.setitem(litellm.model_alias_map, "legacy-name", "exempt-model")
        assert (
            should_skip_budget_checks_for_model("legacy-name", _alias_router()) is True
        )

    def test_team_model_alias_skips(self):
        assert (
            should_skip_budget_checks_for_model(
                "gpt-4o",
                _alias_router(),
                team_model_aliases={"gpt-4o": "exempt-model"},
            )
            is True
        )

    def test_team_model_alias_onto_paid_model_does_not_skip(self):
        """An exemption must follow the model the request actually routes to,
        not any name in the chain."""
        assert (
            should_skip_budget_checks_for_model(
                "gpt-4o",
                _alias_router(),
                team_model_aliases={"gpt-4o": "paid-model"},
            )
            is False
        )


class TestSkipDeniedWhenFallbackIsNotExempt:
    """Skipping budget checks also skips the budget reservation, so an exemption
    on the requested model would hand a free pass to whatever paid model it falls
    back to when the primary attempt fails. Every reachable model must be exempt."""

    @pytest.mark.parametrize(
        "router_kwargs",
        [
            {"fallbacks": [{"exempt-model": ["paid-model"]}]},
            {"default_fallbacks": ["paid-model"]},
            {"fallbacks": [{"*": ["paid-model"]}]},
            {"context_window_fallbacks": [{"exempt-model": ["paid-model"]}]},
            {"content_policy_fallbacks": [{"exempt-model": ["paid-model"]}]},
        ],
        ids=[
            "model-specific",
            "default_fallbacks",
            "wildcard-key",
            "context_window",
            "content_policy",
        ],
    )
    def test_paid_router_fallback_denies_skip(self, router_kwargs):
        assert (
            should_skip_budget_checks_for_model(
                "exempt-model", _alias_router(**router_kwargs)
            )
            is False
        )

    def test_transitive_paid_fallback_denies_skip(self):
        router = _alias_router(
            fallbacks=[
                {"exempt-model": ["exempt-model-2"]},
                {"exempt-model-2": ["paid-model"]},
            ]
        )
        assert should_skip_budget_checks_for_model("exempt-model", router) is False

    def test_client_supplied_fallback_denies_skip(self):
        """Router.async_function_with_fallbacks reads `fallbacks` straight off the
        request kwargs, so the caller picks the fallback target themselves."""
        assert (
            should_skip_budget_checks_for_model(
                "exempt-model", _alias_router(), request_fallbacks=["paid-model"]
            )
            is False
        )

    def test_fallback_on_alias_target_denies_skip(self):
        router = _alias_router(fallbacks=[{"exempt-model": ["paid-model"]}])
        assert should_skip_budget_checks_for_model("alias-of-exempt", router) is False

    def test_all_exempt_fallbacks_still_skip(self):
        router = _alias_router(fallbacks=[{"exempt-model": ["exempt-model-2"]}])
        assert should_skip_budget_checks_for_model("exempt-model", router) is True

    def test_cyclic_fallbacks_terminate(self):
        router = _alias_router(
            fallbacks=[
                {"exempt-model": ["exempt-model-2"]},
                {"exempt-model-2": ["exempt-model"]},
            ]
        )
        assert should_skip_budget_checks_for_model("exempt-model", router) is True

    def test_fallbacks_of_unrelated_model_do_not_deny_skip(self):
        """Only fallbacks reachable *from the requested model* matter."""
        router = _alias_router(fallbacks=[{"paid-model": ["exempt-model"]}])
        assert should_skip_budget_checks_for_model("exempt-model", router) is True

    def test_garbage_request_fallbacks_are_ignored(self):
        """`fallbacks` is untrusted request-body input."""
        assert (
            should_skip_budget_checks_for_model(
                "exempt-model",
                _alias_router(),
                request_fallbacks=[{"paid": 1}, 7, None],
            )
            is True
        )


class TestFallbackWiring:
    """The gate is only as good as what the callers hand it."""

    def test_auth_layer_passes_request_fallbacks(self):
        assert (
            _should_skip_budget_checks(
                request_data={"model": "exempt-model", "fallbacks": ["paid-model"]},
                route="/v1/chat/completions",
                request=MagicMock(),
                llm_router=_alias_router(),
                valid_token=UserAPIKeyAuth(token="t", user_id="u"),
            )
            is False
        )

    def test_auth_layer_passes_team_context(self):
        assert (
            _should_skip_budget_checks(
                request_data={"model": "team-exempt"},
                route="/v1/chat/completions",
                request=MagicMock(),
                llm_router=_alias_router(),
                valid_token=UserAPIKeyAuth(token="t", user_id="u", team_id="team-1"),
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_max_budget_hook_blocks_exempt_model_with_paid_fallback(
        self, monkeypatch
    ):
        import litellm.proxy.proxy_server as proxy_server

        async def _over_budget_spend(counter_key, fallback_spend):
            return 100.0

        monkeypatch.setattr(proxy_server, "llm_router", _alias_router())
        monkeypatch.setattr(proxy_server, "get_current_spend", _over_budget_spend)

        hook = _PROXY_MaxBudgetLimiter()
        with pytest.raises(HTTPException) as exc_info:
            await hook.async_pre_call_hook(
                user_api_key_dict=UserAPIKeyAuth(
                    token="test-token",
                    user_id="test-user",
                    team_id=None,
                    user_max_budget=10.0,
                    user_spend=100.0,
                ),
                cache=DualCache(),
                data={"model": "exempt-model", "fallbacks": ["paid-model"]},
                call_type="completion",
            )
        assert exc_info.value.status_code == 429
