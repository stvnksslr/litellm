"""
Unit tests for Gemma 4 MaaS routing on Vertex AI.

Covers:
- PartnerModelPrefixes.GOOGLE_PREFIX recognition
- is_vertex_partner_model() returning True for google/ models
- should_use_openai_handler() returning True for google/ models
- get_vertex_ai_model_route() routing google/ models to PARTNER_MODELS
- model_prices_and_context_window.json entry for gemma-4-26b-a4b-it-maas
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("../../../../../.."))

from litellm.llms.vertex_ai.common_utils import (
    VertexAIModelRoute,
    get_vertex_ai_model_route,
)
from litellm.llms.vertex_ai.vertex_ai_partner_models.main import (
    PartnerModelPrefixes,
    VertexAIPartnerModels,
)


GEMMA4_MAAS_MODEL = "google/gemma-4-26b-a4b-it-maas"


class TestGooglePrefixRecognition:
    """GOOGLE_PREFIX must be present and correctly valued."""

    def test_google_prefix_value(self):
        assert PartnerModelPrefixes.GOOGLE_PREFIX == "google/"

    def test_is_vertex_partner_model_google(self):
        assert VertexAIPartnerModels.is_vertex_partner_model(GEMMA4_MAAS_MODEL) is True

    def test_is_vertex_partner_model_other_google_model(self):
        assert (
            VertexAIPartnerModels.is_vertex_partner_model(
                "google/some-future-model-maas"
            )
            is True
        )

    def test_should_use_openai_handler_google(self):
        """Google MaaS models must go through the OpenAI-compatible endpoint."""
        assert (
            VertexAIPartnerModels.should_use_openai_handler(GEMMA4_MAAS_MODEL) is True
        )

    def test_should_use_openai_handler_non_google(self):
        """Sanity check: non-google partner models should not be affected."""
        assert (
            VertexAIPartnerModels.should_use_openai_handler("claude-sonnet-4-6")
            is False
        )


class TestVertexGemma4Routing:
    """get_vertex_ai_model_route must route google/ models to PARTNER_MODELS."""

    def test_gemma4_maas_routes_to_partner_models(self):
        route = get_vertex_ai_model_route(GEMMA4_MAAS_MODEL)
        assert route == VertexAIModelRoute.PARTNER_MODELS

    def test_gemma4_maas_does_not_route_to_non_gemini(self):
        route = get_vertex_ai_model_route(GEMMA4_MAAS_MODEL)
        assert route != VertexAIModelRoute.NON_GEMINI

    def test_gemma4_maas_does_not_route_to_gemma(self):
        """google/ prefix should NOT match the old 'gemma/' custom-endpoint route."""
        route = get_vertex_ai_model_route(GEMMA4_MAAS_MODEL)
        assert route != VertexAIModelRoute.GEMMA

    @pytest.mark.parametrize(
        "model, expected_route",
        [
            # Old-style custom endpoint Gemma (unchanged)
            ("gemma/gemma-3-12b-it-endpoint123", VertexAIModelRoute.GEMMA),
            # New Google MaaS prefix
            ("google/gemma-4-26b-a4b-it-maas", VertexAIModelRoute.PARTNER_MODELS),
            # Ensure existing partner models are unaffected
            ("claude-sonnet-4-6", VertexAIModelRoute.PARTNER_MODELS),
            (
                "meta/llama-4-scout-17b-16e-instruct-maas",
                VertexAIModelRoute.PARTNER_MODELS,
            ),
        ],
    )
    def test_routing_table(self, model, expected_route):
        assert get_vertex_ai_model_route(model) == expected_route


class TestGemma4ModelPrices:
    """The model_prices_and_context_window.json entry must contain expected fields."""

    def test_gemma4_maas_entry_exists(self):
        import json

        path = os.path.join(
            os.path.dirname(__file__),
            "../../../../../model_prices_and_context_window.json",
        )
        with open(path) as f:
            data = json.load(f)
        assert "vertex_ai/google/gemma-4-26b-a4b-it-maas" in data

    def test_gemma4_maas_entry_fields(self):
        import json

        path = os.path.join(
            os.path.dirname(__file__),
            "../../../../../model_prices_and_context_window.json",
        )
        with open(path) as f:
            data = json.load(f)
        entry = data["vertex_ai/google/gemma-4-26b-a4b-it-maas"]
        assert entry["litellm_provider"] == "vertex_ai-google_models"
        assert entry["mode"] == "chat"
        assert entry["max_input_tokens"] == 262144
        assert entry["max_output_tokens"] == 131072
        assert entry["supports_function_calling"] is True
        assert entry["supports_vision"] is True
