"""Tests for the decider (SystemOne) pass-through route and Vertex AI passthrough config.

The route relays typed-decision requests (`/v1/systemone` and friends) to
a Vertex AI dedicated-endpoint deployment registered by VertexAIModelSet.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException, Request, Response

from litellm.proxy.auth.user_api_key_auth import UserAPIKeyAuth
from litellm.proxy.pass_through_endpoints.llm_passthrough_endpoints import (
    decider_proxy_route,
    handle_decider_passthrough_router_model,
)


def _make_request(body: dict[str, Any] | None = None) -> Request:
    import json

    payload = json.dumps(body or {}).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
        "path": "/decider/v1/systemone",
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request(scope, receive)


EIKOS_RESPONSE_BODY = {
    "model": "/tmp/model_dir/bucket/caiovicentino1/Eikos-27B-FP8",
    "answers": {
        "allowed": {"type": "noul", "noul": 0.212, "value": False, "confidence": 0.788},
    },
    "usage": {"input_tokens": 606, "output_tokens": 0},
    "latency_s": 0.108,
}


class TestVertexAIDeciderPassthroughConfig:
    def test_registered_for_vertex_ai(self) -> None:
        from litellm.types.utils import LlmProviders
        from litellm.utils import ProviderConfigManager

        config = ProviderConfigManager.get_provider_passthrough_config(
            provider=LlmProviders.VERTEX_AI, model="vertex_ai/openai/decider"
        )
        assert type(config).__name__ == "VertexAIDeciderPassthroughConfig"

    def test_get_complete_url_joins_invoke_base(self) -> None:
        from litellm.llms.vertex_ai.passthrough.transformation import (
            VertexAIDeciderPassthroughConfig,
        )

        config = VertexAIDeciderPassthroughConfig()
        url, base = config.get_complete_url(
            api_base=(
                "https://ep.us-south1-78207166843.prediction.vertexai.goog"
                "/v1/projects/78207166843/locations/us-south1/endpoints/ep/invoke/v1"
            ),
            api_key=None,
            model="vertex_ai/openai/decider",
            endpoint="systemone",
            request_query_params=None,
            litellm_params={},
        )
        assert str(url).endswith("/endpoints/ep/invoke/v1/systemone")
        assert base.endswith("/invoke/v1")

    def test_get_complete_url_requires_api_base(self) -> None:
        from litellm.llms.vertex_ai.passthrough.transformation import (
            VertexAIDeciderPassthroughConfig,
        )

        config = VertexAIDeciderPassthroughConfig()
        with pytest.raises(ValueError):
            config.get_complete_url(
                api_base=None,
                api_key=None,
                model="vertex_ai/openai/decider",
                endpoint="systemone",
                request_query_params=None,
                litellm_params={},
            )

    def test_logging_non_streaming_response_maps_usage(self) -> None:
        from litellm.llms.vertex_ai.passthrough.transformation import (
            VertexAIDeciderPassthroughConfig,
        )

        config = VertexAIDeciderPassthroughConfig()
        response = httpx.Response(200, json=EIKOS_RESPONSE_BODY)
        logged = config.logging_non_streaming_response(
            model="vertex_ai/openai/decider",
            custom_llm_provider="vertex_ai",
            httpx_response=response,
            request_data={"model": "eikos-27b"},
            logging_obj=MagicMock(),
            endpoint="systemone",
        )
        assert logged is not None
        assert logged.usage.prompt_tokens == 606
        assert logged.usage.completion_tokens == 0

    def test_logging_non_streaming_response_ignores_errors(self) -> None:
        from litellm.llms.vertex_ai.passthrough.transformation import (
            VertexAIDeciderPassthroughConfig,
        )

        config = VertexAIDeciderPassthroughConfig()
        assert (
            config.logging_non_streaming_response(
                model="vertex_ai/openai/decider",
                custom_llm_provider="vertex_ai",
                httpx_response=httpx.Response(500, json={"error": "boom"}),
                request_data={"model": "eikos-27b"},
                logging_obj=MagicMock(),
                endpoint="systemone",
            )
            is None
        )

    def test_validate_environment_sets_bearer_token(self) -> None:
        from litellm.llms.vertex_ai.passthrough.transformation import (
            VertexAIDeciderPassthroughConfig,
        )

        config = VertexAIDeciderPassthroughConfig()
        with patch.object(
            type(config).__mro__[1],  # VertexBase method is called through the instance
            "_ensure_access_token",
            create=True,
        ) as _:
            # Patch at the source class to avoid network access.
            with patch(
                "litellm.llms.vertex_ai.vertex_llm_base.VertexBase._ensure_access_token",
                return_value=("test-token", "test-project"),
            ):
                headers = config.validate_environment(
                    headers={},
                    model="vertex_ai/openai/decider",
                    messages=[],
                    optional_params={},
                    litellm_params={
                        "vertex_project": "test-project",
                        "vertex_location": "us-central1",
                    },
                    api_key=None,
                    api_base=None,
                )
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


class TestDeciderProxyRoute:
    @pytest.mark.asyncio
    async def test_requires_router_model(self) -> None:
        mock_llm_router = MagicMock(spec=["allm_passthrough_route"])
        with patch(
            "litellm.proxy.proxy_server.llm_router",
            mock_llm_router,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await decider_proxy_route(
                    endpoint="v1/systemone",
                    request=_make_request({"model": "unknown-model"}),
                    fastapi_response=MagicMock(spec=Response),
                    user_api_key_dict=MagicMock(spec=UserAPIKeyAuth),
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_relays_with_stripped_v1_prefix(self) -> None:
        mock_llm_router = MagicMock(spec=["allm_passthrough_route"])
        captured: dict[str, Any] = {}

        class _CapturingProcessor:
            def __init__(self, data: dict[str, Any]) -> None:
                captured["data"] = data

            async def base_passthrough_process_llm_request(self, **kwargs: Any) -> Response:
                captured["kwargs"] = kwargs
                return Response(content=b"{}", status_code=200)

        with (
            patch("litellm.proxy.proxy_server.llm_router", mock_llm_router),
            patch(
                "litellm.proxy.pass_through_endpoints.llm_passthrough_endpoints.is_passthrough_request_using_router_model",
                return_value=True,
            ),
            patch(
                "litellm.proxy.common_request_processing.ProxyBaseLLMRequestProcessing",
                _CapturingProcessor,
            ),
        ):
            await decider_proxy_route(
                endpoint="v1/systemone",
                request=_make_request({"model": "eikos-27b", "state": "s", "questions": {}}),
                fastapi_response=MagicMock(spec=Response),
                user_api_key_dict=MagicMock(spec=UserAPIKeyAuth),
            )

        data = captured["data"]
        assert data["model"] == "eikos-27b"
        assert data["endpoint"] == "systemone"  # v1/ stripped: api_base ends at /invoke/v1
        assert data["custom_llm_provider"] == "vertex_ai"
        assert data["json"]["state"] == "s"
        assert "api_base" not in data  # deployment litellm_params must win

    @pytest.mark.asyncio
    async def test_handler_keeps_request_body_pristine(self) -> None:
        """Auth metadata must not leak into the caller's body dict."""
        request_body = {"model": "eikos-27b", "state": "s", "questions": {}}
        captured: dict[str, Any] = {}

        class _CapturingProcessor:
            def __init__(self, data: dict[str, Any]) -> None:
                captured["data"] = data

            async def base_passthrough_process_llm_request(self, **kwargs: Any) -> Response:
                return Response(content=b"{}", status_code=200)

        with patch(
            "litellm.proxy.common_request_processing.ProxyBaseLLMRequestProcessing",
            _CapturingProcessor,
        ):
            await handle_decider_passthrough_router_model(
                model="eikos-27b",
                endpoint="systemone",
                request=_make_request(request_body),
                request_body=request_body,
                fastapi_response=Response(),
                llm_router=MagicMock(),
                user_api_key_dict=UserAPIKeyAuth(user_id="user-1", team_id="team-1"),
                proxy_logging_obj=MagicMock(),
                general_settings={},
                proxy_config=MagicMock(),
                select_data_generator=MagicMock(),
                user_model=None,
                user_temperature=None,
                user_request_timeout=None,
                user_max_tokens=None,
                user_api_base=None,
                version=None,
            )

        assert request_body == {"model": "eikos-27b", "state": "s", "questions": {}}
        data = captured["data"]
        assert data["metadata"]["user_api_key_user_id"] == "user-1"
        assert data["json"] is request_body


class TestDeciderModelFromQueryParam:
    @pytest.mark.asyncio
    async def test_health_via_query_param_model(self) -> None:
        """GET /decider/v1/health?model=<group> has no body; model comes from the query."""
        captured: dict[str, Any] = {}

        class _CapturingProcessor:
            def __init__(self, data: dict[str, Any]) -> None:
                captured["data"] = data

            async def base_passthrough_process_llm_request(self, **kwargs: Any) -> Response:
                return Response(content=b"{}", status_code=200)

        import json

        payload = json.dumps({}).encode()
        scope = {
            "type": "http",
            "method": "GET",
            "headers": [],
            "query_string": b"model=eikos-27b",
            "path": "/decider/v1/health",
        }

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": payload, "more_body": False}

        request = Request(scope, receive)
        with (
            patch("litellm.proxy.proxy_server.llm_router", MagicMock(spec=["allm_passthrough_route"])),
            patch(
                "litellm.proxy.pass_through_endpoints.llm_passthrough_endpoints.is_passthrough_request_using_router_model",
                return_value=True,
            ),
            patch(
                "litellm.proxy.common_request_processing.ProxyBaseLLMRequestProcessing",
                _CapturingProcessor,
            ),
        ):
            await decider_proxy_route(
                endpoint="v1/health",
                request=request,
                fastapi_response=MagicMock(spec=Response),
                user_api_key_dict=MagicMock(spec=UserAPIKeyAuth),
            )
        assert captured["data"]["model"] == "eikos-27b"
        assert captured["data"]["endpoint"] == "health"
