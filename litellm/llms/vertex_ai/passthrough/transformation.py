"""Vertex AI pass-through support for typed-decision ("decider") models.

Decider models expose the SystemOne typed-decision API (TypeSafe-compatible:
`/v1/systemone`, `/v1/evaluate`, `/v1/sessions`) and are deployed on Vertex AI
dedicated endpoints (invoke mode) by `VertexAIModelSet`. The current instance
is Eikos; the serving model may be replaced or upgraded over time without
changes to this config — routing is keyed on the LiteLLM model group, not on
any specific model implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Final

from litellm.llms.base_llm.passthrough.transformation import BasePassthroughConfig
from litellm.llms.vertex_ai.vertex_llm_base import VertexBase
from litellm.types.utils import ModelResponse, Usage

if TYPE_CHECKING:
    from httpx import URL, Response

    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
    from litellm.types.llms.openai import AllMessageValues
    from litellm.types.utils import CostResponseTypes


class VertexAIDeciderPassthroughConfig(BasePassthroughConfig):
    """Pass-through for Vertex AI dedicated-endpoint decider models (SystemOne API).

    Deployments look like::

        model_name: eikos-27b
        litellm_params:
          model: vertex_ai/openai/decider
          api_base: https://<endpoint-id>.<region>-<project>.prediction.vertexai.goog/\
v1/projects/<n>/locations/<region>/endpoints/<id>/invoke/v1

    `api_base` already ends at the `/invoke/v1` container-prefix boundary, so any
    container route is reachable by appending it verbatim (e.g. `systemone`).
    """

    def is_streaming_request(self, endpoint: str, request_data: Mapping[str, object]) -> bool:
        # SystemOne typed-decision responses are single JSON documents; honor the
        # flag anyway so a future streaming backend works unchanged.
        return bool(request_data.get("stream", False))

    def get_complete_url(
        self,
        api_base: str | None,
        api_key: str | None,
        model: str,
        endpoint: str,
        request_query_params: dict | None,
        litellm_params: dict,
    ) -> tuple[URL, str]:
        if not api_base:
            raise ValueError(
                "Vertex AI dedicated-endpoint deployment is missing 'api_base'. "
                "Register the VertexAIModelSet region deployment with api_base="
                "'<dedicated-dns>/v1/projects/<n>/locations/<r>/endpoints/<id>/invoke/v1'."
            )
        base_target_url: Final = api_base.rstrip("/")
        return self.format_url(endpoint, base_target_url, request_query_params), base_target_url

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: Sequence[AllMessageValues],
        optional_params: Mapping[str, object],
        litellm_params: Mapping[str, object],
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> dict:
        vertex_base = VertexBase()
        vertex_credentials = vertex_base.safe_get_vertex_ai_credentials(dict(litellm_params))
        vertex_project = vertex_base.safe_get_vertex_ai_project(dict(litellm_params))
        token, _ = vertex_base._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai",
        )
        headers["Authorization"] = f"Bearer {token}"  # mutable-ok: auth header setup
        headers["Content-Type"] = "application/json"  # mutable-ok: auth header setup
        return headers

    def logging_non_streaming_response(
        self,
        model: str,
        custom_llm_provider: str,
        httpx_response: Response,
        request_data: Mapping[str, object],
        logging_obj: LiteLLMLoggingObj,
        endpoint: str,
    ) -> CostResponseTypes | None:
        """Map a SystemOne decision response onto standard token usage.

        SystemOne servers respond with::

            {"model": <local weight path>, "answers": {...},
             "usage": {"input_tokens": N, "output_tokens": 0}, ...}

        The response's own `model` field is a server-side filesystem path, so it
        is not useful for pricing/attribution; usage is returned under the
        deployment model LiteLLM already knows.
        """
        if httpx_response.status_code != 200:
            return None
        try:
            body: Final = httpx_response.json()
        except ValueError:
            return None
        if not isinstance(body, dict):
            return None
        usage = body.get("usage") or {}
        input_tokens = usage.get("input_tokens", 0) if isinstance(usage, dict) else 0
        output_tokens = usage.get("output_tokens", 0) if isinstance(usage, dict) else 0
        try:
            return ModelResponse(
                model=model,
                usage=Usage(prompt_tokens=int(input_tokens or 0), completion_tokens=int(output_tokens or 0)),
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def get_api_base(api_base: str | None = None) -> str | None:
        # Decider deployments always carry a dedicated-endpoint api_base; there is
        # no meaningful static fallback.
        return api_base

    @staticmethod
    def get_api_key(api_key: str | None = None) -> str | None:
        # Auth is Google OAuth via validate_environment; no static API key.
        return api_key

    @staticmethod
    def get_base_model(model: str) -> str | None:
        return model

    def get_models(self, api_key: str | None = None, api_base: str | None = None) -> list[str]:
        # Decider models are provisioned by VertexAIModelSet, not discoverable
        # from a public models endpoint.
        return []
