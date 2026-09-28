"""Reasoning defaults for the self-deployed Vertex Model Garden coding models behind ``/v1/messages``.

Qwen and GLM reason unless told otherwise, while a ``/v1/messages`` client that sends no ``thinking``
expects none. Qwen takes ``chat_template_kwargs.enable_thinking: false`` and its server only accepts
``reasoning_effort`` ``low``, ``medium`` and ``xhigh`` (its default), so a requested tier is mapped onto
those. GLM's template ignores that and only knows ``low`` and ``high`` (anything else means its default,
``max``), so GLM gets ``low`` by default and a requested tier is collapsed onto those two. See fork-patches.md
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final, Literal, TypeAlias

from typing_extensions import assert_never

ModelFamily: TypeAlias = Literal["qwen", "glm"]

EMPTY_OVERRIDES: Final[Mapping[str, object]] = MappingProxyType({})
GLM_DEFAULT_REASONING_EFFORT: Final[str] = "low"
_GLM_REASONING_EFFORTS: Final[Mapping[str, str]] = MappingProxyType(
    {"minimal": "low", "low": "low", "medium": "high", "high": "high", "xhigh": "high"}
)
_QWEN_REASONING_EFFORTS: Final[Mapping[str, str]] = MappingProxyType(
    {"minimal": "low", "low": "low", "medium": "medium", "high": "xhigh", "xhigh": "xhigh", "max": "xhigh"}
)
_MODEL_GARDEN_PROVIDERS: Final[frozenset[str]] = frozenset({"hosted_vllm", "vertex_ai"})
_MODEL_FAMILY_MARKERS: Final[tuple[tuple[ModelFamily, str], ...]] = (("qwen", "qwen"), ("glm", "glm"))
_THINKING_REQUESTED_TYPES: Final[frozenset[str]] = frozenset({"enabled", "adaptive"})


def match_model_family(
    completion_kwargs: Mapping[str, object], extra_kwargs: Mapping[str, object]
) -> ModelFamily | None:
    provider: Final = extra_kwargs.get("custom_llm_provider")
    if isinstance(provider, str) and provider.lower() not in _MODEL_GARDEN_PROVIDERS:
        return None

    model_info: Final = extra_kwargs.get("model_info")
    deployment_params: Final = extra_kwargs.get("litellm_params")
    candidates: Final[tuple[object, ...]] = (
        completion_kwargs.get("model"),
        model_info.get("base_model") if isinstance(model_info, dict) else None,
        deployment_params.get("model") if isinstance(deployment_params, dict) else None,
    )
    names: Final = tuple(candidate.lower() for candidate in candidates if isinstance(candidate, str))
    return next((family for family, marker in _MODEL_FAMILY_MARKERS if any(marker in name for name in names)), None)


def requested_reasoning_effort(completion_kwargs: Mapping[str, object]) -> str | None:
    reasoning_effort: Final = completion_kwargs.get("reasoning_effort")
    effort: Final = reasoning_effort.get("effort") if isinstance(reasoning_effort, dict) else reasoning_effort
    return effort if isinstance(effort, str) and effort != "none" else None


def _qwen_thinking_disabled(completion_kwargs: Mapping[str, object]) -> Mapping[str, object]:
    existing_extra_body: Final = completion_kwargs.get("extra_body")
    extra_body: Final = existing_extra_body if isinstance(existing_extra_body, Mapping) else EMPTY_OVERRIDES
    existing_template_kwargs: Final = extra_body.get("chat_template_kwargs")
    template_kwargs: Final = (
        existing_template_kwargs if isinstance(existing_template_kwargs, Mapping) else EMPTY_OVERRIDES
    )
    template_off: Final = {**template_kwargs, "enable_thinking": False}  # mutable-ok: wire body
    extra_body_off: Final = {**extra_body, "chat_template_kwargs": template_off}  # mutable-ok: wire body
    return MappingProxyType({"extra_body": extra_body_off})


def default_reasoning_overrides(
    completion_kwargs: Mapping[str, object],
    extra_kwargs: Mapping[str, object],
    thinking: Mapping[str, object] | None,
) -> Mapping[str, object]:
    family: Final = match_model_family(completion_kwargs, extra_kwargs)
    if family is None:
        return EMPTY_OVERRIDES
    thinking_requested: Final = isinstance(thinking, Mapping) and thinking.get("type") in _THINKING_REQUESTED_TYPES
    effort: Final = requested_reasoning_effort(completion_kwargs)
    match family:
        case "qwen":
            if effort is not None:
                return MappingProxyType({"reasoning_effort": _QWEN_REASONING_EFFORTS.get(effort, effort)})
            if thinking_requested:
                return EMPTY_OVERRIDES
            return _qwen_thinking_disabled(completion_kwargs)
        case "glm":
            if effort is not None:
                return MappingProxyType({"reasoning_effort": _GLM_REASONING_EFFORTS.get(effort, effort)})
            if thinking_requested:
                return EMPTY_OVERRIDES
            return MappingProxyType({"reasoning_effort": GLM_DEFAULT_REASONING_EFFORT})
        case _:
            assert_never(family)
