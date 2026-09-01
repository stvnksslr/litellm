import json
import time
from unittest.mock import MagicMock

import pytest

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.llms.openai_like.chat.handler import make_call
from litellm.utils import CustomStreamWrapper


class _FakeStreamingResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeAsyncClient:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def post(self, *args, **kwargs):
        return _FakeStreamingResponse(self._lines)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}"


def _chunk(delta: dict, finish_reason: str | None = None) -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "glm-5_2",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def _logging_obj() -> Logging:
    return Logging(
        model="glm-5_2",
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
        call_type="completion",
        start_time=time.time(),
        litellm_call_id="1234",
        function_id="1234",
    )


async def _stream_chunks(lines: list[str]) -> list:
    completion_stream = await make_call(
        client=_FakeAsyncClient(lines),
        api_base="https://fake-vertex-endpoint/chat/completions",
        headers={},
        data="{}",
        model="glm-5_2",
        messages=[{"role": "user", "content": "hi"}],
        logging_obj=MagicMock(),
    )
    wrapper = CustomStreamWrapper(
        completion_stream=completion_stream,
        model="glm-5_2",
        custom_llm_provider="vertex_ai",
        logging_obj=_logging_obj(),
    )
    return [chunk async for chunk in wrapper]


@pytest.mark.asyncio
async def test_streaming_forwards_reasoning_content():
    """Reasoning-only deltas must reach the client. A reasoning model that spends its
    whole token budget thinking otherwise streams nothing at all."""
    chunks = await _stream_chunks(
        [
            _sse(_chunk({"role": "assistant", "reasoning_content": "let me think"})),
            _sse(_chunk({"reasoning_content": " harder"})),
            _sse(_chunk({"content": "42"})),
            _sse(_chunk({}, finish_reason="stop")),
            "data: [DONE]",
        ]
    )

    reasoning = "".join(getattr(c.choices[0].delta, "reasoning_content", None) or "" for c in chunks)
    content = "".join(c.choices[0].delta.content or "" for c in chunks)

    assert reasoning == "let me think harder"
    assert content == "42"


@pytest.mark.asyncio
async def test_streaming_reasoning_only_response_is_not_silently_empty():
    """finish_reason=length with every token spent on reasoning must still deliver the
    reasoning text instead of an empty stream."""
    chunks = await _stream_chunks(
        [
            _sse(_chunk({"role": "assistant", "reasoning_content": "thinking"})),
            _sse(_chunk({}, finish_reason="length")),
            "data: [DONE]",
        ]
    )

    assert any(getattr(c.choices[0].delta, "reasoning_content", None) for c in chunks)
    assert chunks[-1].choices[0].finish_reason == "length"


@pytest.mark.asyncio
async def test_streaming_surfaces_error_payload_in_200_response():
    """vLLM-backed endpoints can return HTTP 200 whose body carries an error payload.
    Swallowing it hands the client an empty, successful-looking stream."""
    with pytest.raises(litellm.exceptions.MidStreamFallbackError) as excinfo:
        await _stream_chunks(
            [
                _sse({"error": {"message": "model is overloaded", "code": 503}}),
                "data: [DONE]",
            ]
        )

    assert "model is overloaded" in str(excinfo.value)
