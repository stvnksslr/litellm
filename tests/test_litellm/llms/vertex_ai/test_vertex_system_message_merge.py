"""
Qwen and GLM chat templates reject any request whose system message is not the single first
message ("System message must be at the beginning."), and both Vertex AI routes that serve them
over an OpenAI-compatible endpoint hit that: MaaS partner models and deployed Model Garden
endpoints.

Clients such as Claude Code send mid-turn system entries, so each handler folds them into one
leading system message before the request goes out.
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath("../../../.."))

import litellm
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

MODEL_GARDEN_MODEL = "vertex_ai/openai/qwen_qwen3_8-27b-fp8"
MAAS_MODEL = "vertex_ai/qwen/qwen3-next-80b-a3b-instruct-maas"


def _mock_response() -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.text = ""
    response.json.return_value = {
        "id": "chatcmpl-qwen-test",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "qwen",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Bonjour"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    }
    return response


async def _sent_messages(model: str, messages: list) -> list:
    client = MagicMock(spec=AsyncHTTPHandler)
    client.post = AsyncMock(return_value=_mock_response())
    mock_vertexai = MagicMock()
    mock_vertexai.preview = MagicMock()

    with (
        patch(
            "litellm.llms.vertex_ai.vertex_llm_base.VertexBase._ensure_access_token",
            return_value=("fake-token", "test-project"),
        ),
        patch.dict(
            "sys.modules",
            {"vertexai": mock_vertexai, "vertexai.preview": mock_vertexai.preview},
        ),
    ):
        await litellm.acompletion(
            model=model,
            messages=messages,
            vertex_ai_project="test-project",
            vertex_ai_location="us-west1",
            client=client,
        )

    call_kwargs = client.post.call_args.kwargs
    payload = call_kwargs.get("json") or json.loads(call_kwargs["data"])
    return payload["messages"]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", [MODEL_GARDEN_MODEL, MAAS_MODEL])
async def test_midturn_system_message_is_folded_into_leading_system_message(model):
    sent = await _sent_messages(
        model,
        [
            {"role": "system", "content": "You are terse."},
            {"role": "user", "content": "say hi"},
            {"role": "system", "content": [{"type": "text", "text": "Reply in French only."}]},
            {"role": "assistant", "content": "Bonjour"},
        ],
    )

    assert sent == [
        {"role": "system", "content": "You are terse.\n\nReply in French only."},
        {"role": "user", "content": "say hi"},
        {"role": "assistant", "content": "Bonjour"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", [MODEL_GARDEN_MODEL, MAAS_MODEL])
async def test_system_message_only_at_front_is_left_alone(model):
    sent = await _sent_messages(
        model,
        [
            {"role": "system", "content": [{"type": "text", "text": "You are terse."}]},
            {"role": "user", "content": "say hi"},
        ],
    )

    assert sent == [
        {"role": "system", "content": [{"type": "text", "text": "You are terse."}]},
        {"role": "user", "content": "say hi"},
    ]
