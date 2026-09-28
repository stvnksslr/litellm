"""Claude Code auto mode's permission classifier sends ``stop_sequences=["</block>"]`` with a
``max_tokens`` computed inline in the binary (2112 on CLI 2.1.259 through 2.1.266). At GLM's default
reasoning effort that budget runs out before the verdict, so the call truncates and fails closed. The
reasoning default lives in model_garden_reasoning; this floors the budget at 4096 as the backstop.
The match on that wire shape is deliberately fail-open: a client change stops matching and requests
pass through. See fork-patches.md
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from litellm.llms.anthropic.experimental_pass_through.adapters.model_garden_reasoning import (
    EMPTY_OVERRIDES,
    match_model_family,
)

CLASSIFIER_STOP_SEQUENCE: Final[str] = "</block>"
GLM_CLASSIFIER_MIN_MAX_TOKENS: Final[int] = 4096


def is_classifier_request(completion_kwargs: Mapping[str, object]) -> bool:
    stop: Final = completion_kwargs.get("stop")
    return isinstance(stop, list) and CLASSIFIER_STOP_SEQUENCE in stop


def classifier_max_tokens_floor(completion_kwargs: Mapping[str, object]) -> int | None:
    max_tokens: Final = completion_kwargs.get("max_tokens")
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
        return None
    if max_tokens >= GLM_CLASSIFIER_MIN_MAX_TOKENS:
        return None
    return GLM_CLASSIFIER_MIN_MAX_TOKENS


def glm_classifier_request_overrides(
    completion_kwargs: Mapping[str, object],
    extra_kwargs: Mapping[str, object],
) -> Mapping[str, object]:
    if match_model_family(completion_kwargs, extra_kwargs) != "glm" or not is_classifier_request(completion_kwargs):
        return EMPTY_OVERRIDES
    floored: Final = classifier_max_tokens_floor(completion_kwargs)
    return EMPTY_OVERRIDES if floored is None else MappingProxyType({"max_tokens": floored})
