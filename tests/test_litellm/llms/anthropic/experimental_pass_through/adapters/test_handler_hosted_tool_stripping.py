"""
Regression tests for Anthropic server-side tools leaking through the
``/v1/messages`` -> ``/chat/completions`` adapter.

Background: ``translate_anthropic_tools_to_openai`` deliberately forwards
Anthropic hosted tools (``tool_search_tool_*``, ``bash_*``, ``text_editor_*``,
``memory_*``, ...) in their native shape, because the guardrail translation
path round-trips them back to Anthropic format.

That pass-through is wrong once the request leaves for a non-Anthropic
backend. Claude Code with tool search enabled sends
``{"type": "tool_search_tool_regex_20251119", "name": "tool_search"}`` as
``tools[0]``; forwarding it verbatim makes OpenAI-compatible backends reject
the whole request on ``tools[0].type``.

``_prepare_completion_kwargs`` is the single boundary where the translated
request leaves for ``litellm.completion``, so the strip belongs there.
"""

import asyncio
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../..")))

import litellm
from litellm.llms.anthropic.experimental_pass_through.adapters.handler import (
    LiteLLMMessagesToCompletionTransformationHandler,
)

MESSAGES = [{"role": "user", "content": "hello"}]

BASH_TOOL = {
    "name": "Bash",
    "description": "run a command",
    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}},
}


def _call_prepare(tools, model="hosted_vllm/glm-5_2-fp8"):
    completion_kwargs, _ = LiteLLMMessagesToCompletionTransformationHandler._prepare_completion_kwargs(
        max_tokens=1024,
        messages=MESSAGES,
        model=model,
        metadata=None,
        stop_sequences=None,
        stream=False,
        system=None,
        temperature=None,
        thinking=None,
        tool_choice=None,
        tools=tools,
        top_k=None,
        top_p=None,
        output_format=None,
        extra_kwargs={},
    )
    return completion_kwargs


@pytest.mark.parametrize(
    "hosted_tool",
    [
        {"type": "tool_search_tool_regex_20251119", "name": "tool_search"},
        {"type": "tool_search_tool_bm25_20251119", "name": "tool_search"},
        {"type": "bash_20250124", "name": "bash"},
        {"type": "text_editor_20250124", "name": "str_replace_editor"},
        {"type": "memory_20250818", "name": "memory"},
        {"type": "code_execution_20250522", "name": "code_execution"},
    ],
)
def test_hosted_tools_are_not_forwarded_to_chat_completions(hosted_tool):
    completion_kwargs = _call_prepare([hosted_tool, BASH_TOOL])

    forwarded = completion_kwargs["tools"]
    assert [tool["type"] for tool in forwarded] == ["function"]
    assert forwarded[0]["function"]["name"] == "Bash"


def test_user_function_tools_survive_untouched():
    completion_kwargs = _call_prepare([BASH_TOOL])

    forwarded = completion_kwargs["tools"]
    assert len(forwarded) == 1
    assert forwarded[0]["function"]["name"] == "Bash"
    assert forwarded[0]["function"]["parameters"]["properties"] == {"command": {"type": "string"}}


def test_tools_key_removed_when_only_hosted_tools_present():
    """An empty ``tools: []`` is rejected by several OpenAI-compatible backends."""
    completion_kwargs = _call_prepare([{"type": "tool_search_tool_regex_20251119", "name": "tool_search"}])

    assert "tools" not in completion_kwargs


def test_claude_code_tool_search_request_reaches_glm_backend_without_hosted_tools():
    """End-to-end: the body actually POSTed to an OpenAI-compatible backend."""
    captured = {}

    async def fake_post(*args, **kwargs):
        captured["body"] = kwargs.get("json") or json.loads(kwargs.get("data") or "{}")
        raise RuntimeError("stop before network")

    async def drive():
        with patch("litellm.llms.custom_httpx.http_handler.AsyncHTTPHandler.post", side_effect=fake_post):
            with pytest.raises(Exception):
                await litellm.anthropic.messages.acreate(
                    model="hosted_vllm/glm-5_2-fp8",
                    api_base="http://localhost:8000/v1",
                    api_key="fake-key",
                    max_tokens=256,
                    messages=MESSAGES,
                    tools=[
                        {"type": "tool_search_tool_regex_20251119", "name": "tool_search"},
                        BASH_TOOL,
                    ],
                )

    asyncio.run(drive())

    wire_tools = captured["body"]["tools"]
    assert [tool["type"] for tool in wire_tools] == ["function"]
    assert wire_tools[0]["function"]["name"] == "Bash"
