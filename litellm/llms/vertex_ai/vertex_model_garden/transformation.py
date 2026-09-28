from litellm.llms.vertex_ai.vertex_ai_partner_models.llama3.transformation import VertexAILlama3Config


class VertexAIModelGardenOpenAIConfig(VertexAILlama3Config):
    """Params for self-deployed Model Garden endpoints served over the OpenAI-compatible surface.

    Reasoning models on those endpoints (SGLang, vLLM) read ``reasoning_effort`` from the request; the
    generic config never declared it, so ``drop_params`` silently removed it and every request ran at
    the template's default effort. See fork-patches.md
    """

    def get_supported_openai_params(self, model: str) -> list[str]:  # mutable-ok: base class signature
        return [*super().get_supported_openai_params(model=model), "reasoning_effort"]  # mutable-ok: callers mutate it
