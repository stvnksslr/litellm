from litellm.llms.anthropic.experimental_pass_through.adapters.model_garden_reasoning import (
    default_reasoning_overrides,
    match_model_family,
    requested_reasoning_effort,
)

GLM_HOSTED_VLLM = {"custom_llm_provider": "hosted_vllm", "model_info": {"base_model": "hosted_vllm/glm-5_2-fp8"}}
GLM_VERTEX = {"custom_llm_provider": "vertex_ai"}
GLM_MODEL = "vertex_ai/openai/glm-5_3-flash"
QWEN_VERTEX = {"custom_llm_provider": "vertex_ai", "model_info": {"base_model": "vertex_ai/qwen3-8"}}


class TestMatchModelFamily:
    def test_qwen_wins_over_glm_in_an_earlier_candidate_slot(self) -> None:
        family = match_model_family(
            {"model": "glm-5-3-flash"},
            {"custom_llm_provider": "hosted_vllm", "model_info": {"base_model": "hosted_vllm/qwen3-8"}},
        )
        assert family == "qwen"

    def test_glm_matched_via_model(self) -> None:
        assert match_model_family({"model": "glm-5-3-flash"}, {"custom_llm_provider": "hosted_vllm"}) == "glm"

    def test_glm_matched_via_base_model(self) -> None:
        assert match_model_family({"model": "claude-sonnet-unlimited"}, GLM_HOSTED_VLLM) == "glm"

    def test_glm_matched_via_litellm_params_model(self) -> None:
        family = match_model_family(
            {"model": "claude-sonnet-unlimited"},
            {"custom_llm_provider": "vertex_ai", "litellm_params": {"model": "vertex_ai/openai/glm-5-3-flash"}},
        )
        assert family == "glm"

    def test_match_is_case_insensitive(self) -> None:
        assert match_model_family({"model": "GLM-5-3-Flash"}, {"custom_llm_provider": "Vertex_AI"}) == "glm"

    def test_gate_closes_for_unlisted_provider(self) -> None:
        assert match_model_family({"model": "glm-5-3-flash"}, {"custom_llm_provider": "azure"}) is None

    def test_gate_stays_open_without_provider(self) -> None:
        assert match_model_family({"model": "glm-5-3-flash"}, {}) == "glm"

    def test_no_marker_returns_none(self) -> None:
        family = match_model_family(
            {"model": "claude-sonnet-unlimited"},
            {"custom_llm_provider": "hosted_vllm", "model_info": {"base_model": "hosted_vllm/llama-3"}},
        )
        assert family is None


class TestRequestedReasoningEffort:
    def test_plain_string(self) -> None:
        assert requested_reasoning_effort({"reasoning_effort": "high"}) == "high"

    def test_summary_wrapped_dict(self) -> None:
        assert requested_reasoning_effort({"reasoning_effort": {"effort": "medium", "summary": "auto"}}) == "medium"

    def test_none_is_not_a_request(self) -> None:
        assert requested_reasoning_effort({"reasoning_effort": "none"}) is None
        assert requested_reasoning_effort({"reasoning_effort": {"effort": "none"}}) is None

    def test_absent(self) -> None:
        assert requested_reasoning_effort({}) is None


class TestDefaultReasoningOverridesGlm:
    def test_no_thinking_defaults_to_low(self) -> None:
        assert default_reasoning_overrides({"model": GLM_MODEL}, GLM_VERTEX, None) == {"reasoning_effort": "low"}

    def test_disabled_thinking_translated_to_none_becomes_low(self) -> None:
        kwargs = {"model": GLM_MODEL, "reasoning_effort": "none"}
        assert default_reasoning_overrides(kwargs, GLM_VERTEX, {"type": "disabled"}) == {"reasoning_effort": "low"}

    def test_adaptive_thinking_with_high_effort_stays_high(self) -> None:
        kwargs = {"model": GLM_MODEL, "reasoning_effort": "high"}
        assert default_reasoning_overrides(kwargs, GLM_VERTEX, {"type": "adaptive"}) == {"reasoning_effort": "high"}

    def test_adaptive_thinking_without_effort_is_left_to_the_template(self) -> None:
        assert default_reasoning_overrides({"model": GLM_MODEL}, GLM_VERTEX, {"type": "adaptive"}) == {}

    def test_enabled_thinking_without_effort_is_left_to_the_template(self) -> None:
        thinking = {"type": "enabled", "budget_tokens": 4096}
        assert default_reasoning_overrides({"model": GLM_MODEL}, GLM_VERTEX, thinking) == {}

    def test_medium_collapses_to_high(self) -> None:
        kwargs = {"model": GLM_MODEL, "reasoning_effort": "medium"}
        assert default_reasoning_overrides(kwargs, GLM_VERTEX, {"type": "enabled"}) == {"reasoning_effort": "high"}

    def test_minimal_collapses_to_low(self) -> None:
        kwargs = {"model": GLM_MODEL, "reasoning_effort": {"effort": "minimal", "summary": "auto"}}
        assert default_reasoning_overrides(kwargs, GLM_VERTEX, {"type": "enabled"}) == {"reasoning_effort": "low"}

    def test_unknown_tier_passes_through(self) -> None:
        kwargs = {"model": GLM_MODEL, "reasoning_effort": "default"}
        assert default_reasoning_overrides(kwargs, GLM_VERTEX, None) == {"reasoning_effort": "default"}

    def test_glm_never_receives_a_template_kwarg(self) -> None:
        overrides = default_reasoning_overrides({"model": GLM_MODEL}, GLM_VERTEX, None)
        assert "extra_body" not in overrides


class TestDefaultReasoningOverridesQwen:
    def test_no_thinking_disables_template_thinking_and_preserves_extra_body(self) -> None:
        kwargs = {
            "model": "claude-haiku-unlimited",
            "extra_body": {"chat_template_kwargs": {"some_option": "keep"}, "other_option": "keep"},
        }
        overrides = default_reasoning_overrides(kwargs, QWEN_VERTEX, None)
        assert overrides == {
            "extra_body": {
                "chat_template_kwargs": {"some_option": "keep", "enable_thinking": False},
                "other_option": "keep",
            }
        }
        assert kwargs["extra_body"] == {"chat_template_kwargs": {"some_option": "keep"}, "other_option": "keep"}

    def test_enabled_thinking_is_left_alone(self) -> None:
        thinking = {"type": "enabled", "budget_tokens": 1024}
        assert default_reasoning_overrides({"model": "claude-haiku-unlimited"}, QWEN_VERTEX, thinking) == {}

    def test_requested_effort_is_left_alone(self) -> None:
        kwargs = {"model": "claude-haiku-unlimited", "reasoning_effort": "high"}
        assert default_reasoning_overrides(kwargs, QWEN_VERTEX, None) == {}

    def test_none_effort_still_disables_thinking(self) -> None:
        kwargs = {"model": "claude-haiku-unlimited", "reasoning_effort": "none"}
        assert default_reasoning_overrides(kwargs, QWEN_VERTEX, {"type": "disabled"}) == {
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
        }


class TestDefaultReasoningOverridesOtherTargets:
    def test_azure_is_left_alone(self) -> None:
        kwargs = {"model": "claude-sonnet-unlimited"}
        extra = {"custom_llm_provider": "azure", "model_info": {"base_model": "azure/gpt-5.6-luna"}}
        assert default_reasoning_overrides(kwargs, extra, None) == {}

    def test_unmatched_model_garden_model_is_left_alone(self) -> None:
        assert default_reasoning_overrides({"model": "vertex_ai/openai/gemma-4"}, GLM_VERTEX, None) == {}
