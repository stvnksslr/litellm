import pytest

from litellm.llms.anthropic.experimental_pass_through.adapters.claude_code_classifier import (
    classifier_max_tokens_floor,
    glm_classifier_request_overrides,
    is_classifier_request,
)

GLM_HOSTED_VLLM = {"custom_llm_provider": "hosted_vllm", "model_info": {"base_model": "hosted_vllm/glm-5_2-fp8"}}


class TestIsClassifierRequest:
    def test_block_stop_in_list_matches(self) -> None:
        assert is_classifier_request({"stop": ["</block>"]}) is True

    def test_block_stop_among_other_stops_matches(self) -> None:
        assert is_classifier_request({"stop": ["STOP", "</block>"]}) is True

    def test_other_stop_does_not_match(self) -> None:
        assert is_classifier_request({"stop": ["STOP"]}) is False

    def test_missing_stop_does_not_match(self) -> None:
        assert is_classifier_request({"max_tokens": 2112}) is False

    def test_str_stop_fails_open(self) -> None:
        assert is_classifier_request({"stop": "</block>"}) is False

    def test_pre_translation_stop_sequences_key_is_ignored(self) -> None:
        assert is_classifier_request({"stop_sequences": ["</block>"]}) is False


class TestClassifierMaxTokensFloor:
    @pytest.mark.parametrize("max_tokens", [2112, 1024, 64, 1, 4095])
    def test_below_floor_is_raised_to_4096(self, max_tokens: int) -> None:
        assert classifier_max_tokens_floor({"max_tokens": max_tokens}) == 4096

    @pytest.mark.parametrize("max_tokens", [4096, 4097, 32000])
    def test_at_or_above_floor_is_left_alone(self, max_tokens: int) -> None:
        assert classifier_max_tokens_floor({"max_tokens": max_tokens}) is None

    @pytest.mark.parametrize("max_tokens", [True, "2112", None])
    def test_non_int_max_tokens_is_left_alone(self, max_tokens: object) -> None:
        assert classifier_max_tokens_floor({"max_tokens": max_tokens}) is None

    def test_missing_max_tokens_is_left_alone(self) -> None:
        assert classifier_max_tokens_floor({}) is None


class TestGlmClassifierRequestOverrides:
    def test_glm_classifier_below_floor_gets_floor(self) -> None:
        kwargs = {"model": "claude-sonnet-unlimited", "stop": ["</block>"], "max_tokens": 2112}
        assert glm_classifier_request_overrides(kwargs, GLM_HOSTED_VLLM) == {"max_tokens": 4096}

    def test_glm_classifier_at_floor_is_left_alone(self) -> None:
        kwargs = {"model": "claude-sonnet-unlimited", "stop": ["</block>"], "max_tokens": 4096}
        assert glm_classifier_request_overrides(kwargs, GLM_HOSTED_VLLM) == {}

    def test_live_router_shape_matches(self) -> None:
        kwargs = {"model": "vertex_ai/openai/glm-5_3-flash", "stop": ["</block>"], "max_tokens": 2112}
        assert glm_classifier_request_overrides(kwargs, {"custom_llm_provider": "vertex_ai"}) == {"max_tokens": 4096}

    def test_glm_without_classifier_stop_is_left_alone(self) -> None:
        kwargs = {"model": "claude-sonnet-unlimited", "stop": ["STOP"], "max_tokens": 2112}
        assert glm_classifier_request_overrides(kwargs, GLM_HOSTED_VLLM) == {}

    def test_qwen_deployment_is_left_alone(self) -> None:
        kwargs = {"model": "claude-haiku-unlimited", "stop": ["</block>"], "max_tokens": 2112}
        extra = {"custom_llm_provider": "vertex_ai", "model_info": {"base_model": "vertex_ai/qwen3-6"}}
        assert glm_classifier_request_overrides(kwargs, extra) == {}

    def test_provider_gate_closed_is_left_alone(self) -> None:
        kwargs = {"model": "glm-5-3-flash", "stop": ["</block>"], "max_tokens": 2112}
        assert glm_classifier_request_overrides(kwargs, {"custom_llm_provider": "azure"}) == {}
