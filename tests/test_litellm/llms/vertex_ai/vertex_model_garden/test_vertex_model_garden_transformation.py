import litellm
from litellm.llms.vertex_ai.vertex_ai_partner_models.llama3.transformation import VertexAILlama3Config
from litellm.llms.vertex_ai.vertex_model_garden.transformation import VertexAIModelGardenOpenAIConfig
from litellm.types.utils import LlmProviders
from litellm.utils import ProviderConfigManager, get_optional_params

GLM = "openai/glm-5-3-flash"


class TestConfigResolution:
    def test_openai_prefixed_model_garden_model_resolves_to_the_openai_config(self) -> None:
        config = ProviderConfigManager.get_provider_chat_config(model=GLM, provider=LlmProviders.VERTEX_AI)
        assert isinstance(config, VertexAIModelGardenOpenAIConfig)

    def test_llama_partner_model_keeps_the_llama_config(self) -> None:
        config = ProviderConfigManager.get_provider_chat_config(
            model="meta/llama-3.1-405b-instruct-maas", provider=LlmProviders.VERTEX_AI
        )
        assert type(config) is VertexAILlama3Config

    def test_supported_params_lookup_declares_reasoning_effort(self) -> None:
        assert "reasoning_effort" in litellm.get_supported_openai_params(model=GLM, custom_llm_provider="vertex_ai")

    def test_llama_supported_params_do_not_declare_reasoning_effort(self) -> None:
        supported = litellm.get_supported_openai_params(
            model="meta/llama-3.1-405b-instruct-maas", custom_llm_provider="vertex_ai"
        )
        assert "reasoning_effort" not in supported


class TestReasoningEffortForwarding:
    def test_reasoning_effort_survives_drop_params(self) -> None:
        optional = get_optional_params(
            model=GLM, custom_llm_provider="vertex_ai", reasoning_effort="low", max_tokens=64, drop_params=True
        )
        assert optional["reasoning_effort"] == "low"
        assert optional["max_tokens"] == 64

    def test_summary_wrapped_effort_is_unwrapped_to_its_tier(self) -> None:
        optional = get_optional_params(
            model=GLM,
            custom_llm_provider="vertex_ai",
            reasoning_effort={"effort": "high", "summary": "auto"},
            drop_params=True,
        )
        assert optional["reasoning_effort"] == "high"

    def test_llama_still_drops_reasoning_effort(self) -> None:
        optional = get_optional_params(
            model="meta/llama-3.1-405b-instruct-maas",
            custom_llm_provider="vertex_ai",
            reasoning_effort="low",
            drop_params=True,
        )
        assert "reasoning_effort" not in optional
