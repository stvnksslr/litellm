"""
`model_info.skip_budget_checks: true` admits over-budget callers on that model without zeroing its price,
so real spend is still recorded. The flag rides on upstream's zero-cost waiver predicate.
"""

import copy
from collections.abc import Iterator
from typing import Final
from unittest.mock import MagicMock

import pytest

import litellm
from litellm.proxy._types import LiteLLM_UserTable, UserAPIKeyAuth
from litellm.proxy.auth.auth_checks import common_checks, is_model_cost_zero, request_skips_budget_checks
from litellm.proxy.utils import ProxyLogging
from litellm.router import Router
from litellm.types.router import Deployment, LiteLLM_Params, ModelInfo

_CHAT: Final = "/v1/chat/completions"
_PRICED: Final = {"model": "openai/gpt-4o-mini", "api_key": "sk-fake"}


@pytest.fixture(autouse=True)
def _isolate_model_cost() -> Iterator[None]:
    saved: Final = copy.deepcopy(litellm.model_cost)
    try:
        yield
    finally:
        litellm.model_cost.clear()
        litellm.model_cost.update(saved)


def _deployment(name: str, deployment_id: str, flag: object = None) -> dict[str, object]:
    model_info: Final = {"id": deployment_id} | ({} if flag is None else {"skip_budget_checks": flag})
    return {"model_name": name, "litellm_params": dict(_PRICED), "model_info": model_info}


def _router() -> Router:
    return Router(
        model_list=[
            _deployment("exempt-model", "exempt-id", True),
            _deployment("paid-model", "paid-id"),
            _deployment("string-flag-model", "string-id", "true"),
            _deployment("mixed-group", "mixed-1", True),
            _deployment("mixed-group", "mixed-2"),
            {
                "model_name": "unmapped-model",
                "litellm_params": {"model": "openai/totally-nonexistent-model-xyz", "api_key": "sk-fake"},
                "model_info": {"id": "unmapped-id"},
            },
        ],
        model_group_alias={"exempt-alias": "exempt-model"},
    )


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("exempt-model", True),
        ("exempt-alias", True),
        ("paid-model", False),
        ("unmapped-model", False),
        ("string-flag-model", False),
        ("mixed-group", False),
        ("not-a-deployment", False),
    ],
)
def test_only_a_fully_flagged_group_counts_as_budget_free(model: str, expected: bool) -> None:
    assert is_model_cost_zero(model=model, llm_router=_router()) is expected


def test_request_on_a_flagged_priced_model_skips_budget_checks() -> None:
    router: Final = _router()

    assert request_skips_budget_checks(route=_CHAT, model="exempt-model", llm_router=router) is True
    assert request_skips_budget_checks(route=_CHAT, model="paid-model", llm_router=router) is False


def test_toggling_the_flag_on_a_stored_model_takes_effect_both_ways() -> None:
    router: Final = Router(model_list=[])

    def upsert(flag: bool) -> None:
        router.upsert_deployment(
            Deployment(
                model_name="db-model",
                litellm_params=LiteLLM_Params(**_PRICED),
                model_info=ModelInfo(id="db-1", skip_budget_checks=flag),
            )
        )

    upsert(True)
    assert is_model_cost_zero(model="db-model", llm_router=router) is True
    upsert(False)
    assert is_model_cost_zero(model="db-model", llm_router=router) is False
    upsert(True)
    assert is_model_cost_zero(model="db-model", llm_router=router) is True


async def _over_budget_user_on(model: str) -> bool:
    proxy_logging: Final = ProxyLogging(user_api_key_cache=None)

    async def _no_alert(*args: object, **kwargs: object) -> None:
        return None

    proxy_logging.budget_alerts = _no_alert
    request: Final = MagicMock()
    request.query_params = {}
    try:
        await common_checks(
            request_body={"model": model},
            team_object=None,
            user_object=LiteLLM_UserTable(user_id="test-user", spend=100.0, max_budget=50.0),
            end_user_object=None,
            global_proxy_spend=None,
            general_settings={},
            route=_CHAT,
            llm_router=_router(),
            proxy_logging_obj=proxy_logging,
            valid_token=UserAPIKeyAuth(token="test-token", user_id="test-user"),
            request=request,
        )
    except litellm.BudgetExceededError:
        return False
    return True


@pytest.mark.asyncio
@pytest.mark.parametrize(("model", "admitted"), [("exempt-model", True), ("paid-model", False)])
async def test_over_budget_user_is_admitted_only_on_the_flagged_model(model: str, admitted: bool) -> None:
    assert await _over_budget_user_on(model) is admitted
