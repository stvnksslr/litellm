"""
Unit tests for VertexAIAnthropicConfig structured output (output_format) behaviour.

Validates that:
1. map_openai_params no longer substitutes the model with claude-3-sonnet-20240229 —
   newer Vertex AI Claude models should use native output_format, not the tool-based fallback.
2. transform_request adds the structured-outputs beta header when output_format is set
   (validate_environment skips beta headers for Vertex via is_vertex_request=True, so
   transform_request must add it manually).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("../../../../../.."))

from litellm.llms.vertex_ai.vertex_ai_partner_models.anthropic.transformation import (
    VertexAIAnthropicConfig,
)
from litellm.types.llms.anthropic import ANTHROPIC_BETA_HEADER_VALUES

STRUCTURED_OUTPUT_BETA = ANTHROPIC_BETA_HEADER_VALUES.STRUCTURED_OUTPUT_2025_09_25.value
RESPONSE_FORMAT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "answer",
        "schema": {
            "type": "object",
            "properties": {"result": {"type": "string"}},
            "required": ["result"],
        },
        "strict": True,
    },
}


class TestMapOpenAIParamsNoModelSubstitution:
    """map_openai_params must pass the real model to the parent, not a substituted one."""

    @pytest.mark.parametrize(
        "model",
        [
            "claude-sonnet-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-5",
            "claude-opus-4-6",
            "claude-opus-4-7",
        ],
    )
    def test_newer_models_use_output_format(self, model):
        """Newer Claude models should set output_format, not a tool call."""
        config = VertexAIAnthropicConfig()
        optional_params = config.map_openai_params(
            non_default_params={"response_format": RESPONSE_FORMAT_SCHEMA},
            optional_params={},
            model=model,
            drop_params=False,
        )
        # Native output_format should be set
        assert (
            "output_format" in optional_params
        ), f"{model}: expected output_format to be set but got {optional_params}"
        # Tool-based fallback must NOT be used
        tools = optional_params.get("tools", [])
        assert not any(
            t.get("name") == "json_tool_call" for t in tools
        ), f"{model}: unexpected tool-based fallback detected"

    @pytest.mark.parametrize(
        "model",
        [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-5-sonnet-20241022",
        ],
    )
    def test_older_models_use_tool_based(self, model):
        """Older Claude models that don't support output_format must still use tools."""
        config = VertexAIAnthropicConfig()
        optional_params = config.map_openai_params(
            non_default_params={"response_format": RESPONSE_FORMAT_SCHEMA},
            optional_params={},
            model=model,
            drop_params=False,
        )
        # output_format should NOT be set for older models
        assert (
            "output_format" not in optional_params
        ), f"{model}: output_format should not be set for older models"


class TestTransformRequestStructuredOutputBeta:
    """transform_request must include the structured-outputs beta header when output_format is set."""

    def _make_transform_request_with_output_format(self, model: str):
        """Helper: create request data for a model that supports output_format."""
        config = VertexAIAnthropicConfig()

        # First map params to populate optional_params with output_format
        optional_params = config.map_openai_params(
            non_default_params={
                "response_format": RESPONSE_FORMAT_SCHEMA,
                "max_tokens": 256,
            },
            optional_params={},
            model=model,
            drop_params=False,
        )
        optional_params["is_vertex_request"] = True  # set by caller for Vertex AI

        messages = [{"role": "user", "content": "What is 2+2?"}]
        headers: dict = {}

        data = config.transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params={},
            headers=headers,
        )
        return data, headers

    @pytest.mark.parametrize(
        "model",
        [
            "claude-sonnet-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
        ],
    )
    def test_structured_output_beta_header_in_data(self, model):
        """anthropic_beta field in request body must contain the structured-outputs header."""
        data, _ = self._make_transform_request_with_output_format(model)
        if "output_format" not in data:
            pytest.skip(
                f"{model}: no output_format in data; skipping beta-header check"
            )
        anthropic_beta = data.get("anthropic_beta", [])
        assert (
            STRUCTURED_OUTPUT_BETA in anthropic_beta
        ), f"{model}: expected '{STRUCTURED_OUTPUT_BETA}' in anthropic_beta={anthropic_beta}"

    @pytest.mark.parametrize(
        "model",
        [
            "claude-sonnet-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-7",
        ],
    )
    def test_structured_output_beta_header_in_http_headers(self, model):
        """anthropic-beta HTTP header must also include the structured-outputs value."""
        data, headers = self._make_transform_request_with_output_format(model)
        if "output_format" not in data:
            pytest.skip(
                f"{model}: no output_format in data; skipping beta-header check"
            )
        raw_header = headers.get("anthropic-beta", "")
        betas = [b.strip() for b in raw_header.split(",") if b.strip()]
        assert (
            STRUCTURED_OUTPUT_BETA in betas
        ), f"{model}: expected '{STRUCTURED_OUTPUT_BETA}' in anthropic-beta header={raw_header}"

    def test_no_beta_header_when_no_output_format(self):
        """structured-outputs header must NOT appear when output_format is not set."""
        config = VertexAIAnthropicConfig()
        optional_params = config.map_openai_params(
            non_default_params={"max_tokens": 100},
            optional_params={},
            model="claude-sonnet-4-6",
            drop_params=False,
        )
        optional_params["is_vertex_request"] = True
        headers: dict = {}
        data = config.transform_request(
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "Hello"}],
            optional_params=optional_params,
            litellm_params={},
            headers=headers,
        )
        anthropic_beta = data.get("anthropic_beta", [])
        assert STRUCTURED_OUTPUT_BETA not in anthropic_beta
