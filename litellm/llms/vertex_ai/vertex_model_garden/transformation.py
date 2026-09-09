from typing import Final

from litellm.llms.vertex_ai.vertex_ai_partner_models.llama3.transformation import VertexAILlama3Config


class VertexAIModelGardenOpenAIConfig(VertexAILlama3Config):
    """Params for self-deployed Model Garden endpoints served over the OpenAI-compatible surface.

    Reasoning models on those endpoints (SGLang, vLLM) read ``reasoning_effort`` from the request; the
    generic config never declared it, so ``drop_params`` silently removed it and every request ran at
    the template's default effort. See fork-patches.md
    """

    def get_supported_openai_params(self, model: str) -> list[str]:  # mutable-ok: base class signature
        return [*super().get_supported_openai_params(model=model), "reasoning_effort"]  # mutable-ok: callers mutate it

    def map_openai_params(
        self,
        non_default_params: dict,  # mutable-ok: base class signature
        optional_params: dict,  # mutable-ok: base class signature
        model: str,
        drop_params: bool,
    ) -> dict:  # mutable-ok: base class signature
        reasoning_effort: Final = non_default_params.get("reasoning_effort")
        if not isinstance(reasoning_effort, dict):
            return super().map_openai_params(
                non_default_params=non_default_params,
                optional_params=optional_params,
                model=model,
                drop_params=drop_params,
            )
        tier: Final = reasoning_effort.get("effort")
        unwrapped: Final = {**non_default_params, "reasoning_effort": tier}  # mutable-ok: super() pops from it
        return super().map_openai_params(
            non_default_params=unwrapped,
            optional_params=optional_params,
            model=model,
            drop_params=drop_params,
        )
