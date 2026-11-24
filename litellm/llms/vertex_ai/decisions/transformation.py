from collections.abc import Callable, Mapping
from typing import Final

from litellm.llms.typesafe.decisions.transformation import TypeSafeDecisionsConfig
from litellm.llms.vertex_ai.vertex_llm_base import VertexBase


def _vertex_access_token(litellm_params: Mapping[str, object]) -> str:
    params: Final = dict(litellm_params)
    token, _ = VertexBase().ensure_access_token(
        credentials=VertexBase.safe_get_vertex_ai_credentials(params),  # pyright: ignore[reportUnknownMemberType]  # VertexBase takes an untyped dict
        project_id=VertexBase.safe_get_vertex_ai_project(params),  # pyright: ignore[reportUnknownMemberType]  # VertexBase takes an untyped dict
        custom_llm_provider="vertex_ai",
    )
    return token


class VertexAIDecisionsConfig(TypeSafeDecisionsConfig):
    api_key_env = ()
    api_base_env = ()

    def __init__(self, access_token: Callable[[Mapping[str, object]], str] = _vertex_access_token) -> None:
        self._access_token: Final = access_token

    def get_default_api_base(self) -> str | None:
        return None

    def missing_api_base_message(self, custom_llm_provider: str) -> str:
        return (
            f"api_base is required for Decisions provider '{custom_llm_provider}': set it to the dedicated "
            "endpoint's '<dedicated-dns>/v1/projects/<n>/locations/<region>/endpoints/<id>/invoke/v1' URL"
        )

    def resolve_credential(
        self, api_key: str | None, api_base: str, litellm_params: Mapping[str, object]
    ) -> str | None:
        return api_key or self._access_token(litellm_params)
