"""Regression tests over the exact request shapes Claude Code sends to ``/v1/messages``.

The fixtures under ``fixtures/claude_code_2_1_266`` were recorded off the wire from CLI 2.1.266 in one
``claude -p --permission-mode auto`` session on 2026-09-09 (long text elided, identifiers scrubbed,
structure untouched). Each test drives the real bridge translation with a fixture and pins what the
bridge sends to a GLM or Qwen Model Garden deployment.
"""

import json
from pathlib import Path
from typing import Final

import pytest

from litellm.llms.anthropic.experimental_pass_through.adapters.handler import (
    LiteLLMMessagesToCompletionTransformationHandler,
)

FIXTURES: Final = Path(__file__).parent / "fixtures" / "claude_code_2_1_266"
GLM_DEPLOYMENT: Final = "vertex_ai/openai/glm-5_3-flash"
QWEN_DEPLOYMENT: Final = "vertex_ai/openai/qwen_qwen3_8-27b-fp8"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


def _bridge(fixture: dict, deployment: str) -> dict:
    completion_kwargs, _ = LiteLLMMessagesToCompletionTransformationHandler._prepare_completion_kwargs(
        max_tokens=fixture["max_tokens"],
        messages=fixture["messages"],
        model=deployment,
        metadata=fixture.get("metadata"),
        stop_sequences=fixture.get("stop_sequences"),
        stream=fixture.get("stream", False),
        system=fixture.get("system"),
        thinking=fixture.get("thinking"),
        tools=fixture.get("tools"),
        extra_kwargs={
            "custom_llm_provider": "vertex_ai",
            **({"output_config": fixture["output_config"]} if "output_config" in fixture else {}),
        },
    )
    return completion_kwargs


class TestCapturedShapes:
    def test_stage1_wire_shape_is_what_the_detector_keys_on(self) -> None:
        fixture = _load("stage1")
        assert fixture["max_tokens"] == 2112
        assert fixture["stop_sequences"] == ["</block>"]
        assert "thinking" not in fixture
        assert "stream" not in fixture
        assert "tools" not in fixture
        assert "temperature" not in fixture

    def test_stage2_wire_shape_has_no_stop_and_a_bigger_budget(self) -> None:
        fixture = _load("stage2")
        assert fixture["max_tokens"] == 10240
        assert "stop_sequences" not in fixture
        assert "thinking" not in fixture

    def test_sonnet_probe_wire_shape_disables_thinking_with_a_64_token_budget(self) -> None:
        fixture = _load("probe_stage1_sonnet5")
        assert fixture["model"] == "claude-sonnet-5"
        assert fixture["max_tokens"] == 64
        assert fixture["stop_sequences"] == ["</block>"]
        assert fixture["thinking"] == {"type": "disabled"}

    def test_main_loop_wire_shape_requests_adaptive_thinking_with_high_effort(self) -> None:
        fixture = _load("main_loop")
        assert fixture["max_tokens"] == 32000
        assert fixture["thinking"] == {"type": "adaptive", "display": "omitted"}
        assert fixture["output_config"] == {"effort": "high"}
        assert fixture["stream"] is True
        assert "stop_sequences" not in fixture


class TestGlmDeployment:
    def test_stage1_gets_low_effort_and_the_4096_floor(self) -> None:
        kwargs = _bridge(_load("stage1"), GLM_DEPLOYMENT)
        assert kwargs["max_tokens"] == 4096
        assert kwargs["stop"] == ["</block>"]
        assert kwargs["reasoning_effort"] == "low"
        assert "stop_sequences" not in kwargs
        assert "thinking" not in kwargs
        assert "extra_body" not in kwargs

    def test_stage2_gets_low_effort_and_keeps_its_budget(self) -> None:
        kwargs = _bridge(_load("stage2"), GLM_DEPLOYMENT)
        assert kwargs["max_tokens"] == 10240
        assert kwargs["reasoning_effort"] == "low"
        assert "stop" not in kwargs

    def test_sonnet_probe_on_a_glm_backed_slot_gets_low_not_none(self) -> None:
        kwargs = _bridge(_load("probe_stage1_sonnet5"), GLM_DEPLOYMENT)
        assert kwargs["reasoning_effort"] == "low"
        assert kwargs["max_tokens"] == 4096
        assert kwargs["stop"] == ["</block>"]

    def test_main_loop_keeps_the_requested_high_effort_and_budget(self) -> None:
        kwargs = _bridge(_load("main_loop"), GLM_DEPLOYMENT)
        assert kwargs["reasoning_effort"] == "high"
        assert kwargs["max_tokens"] == 32000
        assert kwargs["stream"] is True
        assert "stop" not in kwargs
        assert "extra_body" not in kwargs
        assert [tool["function"]["name"] for tool in kwargs["tools"]] == [
            tool["name"] for tool in _load("main_loop")["tools"]
        ]

    def test_title_call_without_thinking_gets_low_effort_and_keeps_its_schema(self) -> None:
        kwargs = _bridge(_load("main_loop_title_no_thinking"), GLM_DEPLOYMENT)
        assert kwargs["reasoning_effort"] == "low"
        assert kwargs["response_format"]["type"] == "json_schema"
        assert kwargs["max_tokens"] == 32000


class TestQwenDeployment:
    def test_stage1_disables_template_thinking_and_keeps_its_budget(self) -> None:
        kwargs = _bridge(_load("stage1"), QWEN_DEPLOYMENT)
        assert kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
        assert "reasoning_effort" not in kwargs
        assert kwargs["max_tokens"] == 2112
        assert kwargs["stop"] == ["</block>"]

    def test_main_loop_keeps_thinking_on(self) -> None:
        kwargs = _bridge(_load("main_loop"), QWEN_DEPLOYMENT)
        assert "extra_body" not in kwargs
        assert kwargs["reasoning_effort"] == "high"


@pytest.mark.parametrize(
    "name", ["stage1", "stage2", "probe_stage1_sonnet5", "main_loop", "main_loop_title_no_thinking"]
)
def test_fixture_metadata_is_scrubbed(name: str) -> None:
    user_id = json.loads(_load(name)["metadata"]["user_id"])
    assert user_id == {"device_id": "<device_id>", "account_uuid": "", "session_id": "<session_id>"}
