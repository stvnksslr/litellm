#!/usr/bin/env python3
"""Scripted stand-in for a self-hosted GLM behind an OpenAI-compatible chat endpoint.

A main turn gets a Bash tool call, the turn carrying its result gets a closing text, and any request without
tools (auto mode classifier stages, titles) gets a 529 and never a verdict, so a mocked model never approves
an action
"""

import argparse
import json
import os
import time
import uuid
from collections.abc import Iterator, Mapping, Sequence
from typing import Final, TypeAlias

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

JsonObject: TypeAlias = Mapping[str, object]

PROBE_COMMAND: Final = os.environ.get("HARNESS_COMMAND", "python3 -c \"print('harness probe')\"")
OVERLOADED: Final = {"error": {"type": "overloaded_error", "message": "fake glm never answers classifier requests"}}


def _list(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def assistant_message(body: JsonObject) -> JsonObject | None:
    messages: Final = _list(body.get("messages"))
    if not _list(body.get("tools")):
        return None
    last: Final = messages[-1] if messages else None
    if isinstance(last, dict) and last.get("role") == "tool":
        return {"role": "assistant", "content": "harness done"}
    arguments: Final = json.dumps({"command": PROBE_COMMAND, "description": "harness probe"})
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {"name": "Bash", "arguments": arguments},
            }
        ],
    }


def completion(model: object, message: JsonObject) -> JsonObject:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "message": message, "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def stream(full: JsonObject) -> Iterator[str]:
    choice: Final = _list(full["choices"])[0]
    assert isinstance(choice, dict)
    base: Final = {k: full[k] for k in ("id", "created", "model")} | {"object": "chat.completion.chunk"}
    chunks: Final = (
        base | {"choices": [{"index": 0, "delta": choice["message"], "finish_reason": None}]},
        base | {"choices": [{"index": 0, "delta": {}, "finish_reason": choice["finish_reason"]}]},
        base | {"choices": [], "usage": full["usage"]},
    )
    yield from (f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
    yield "data: [DONE]\n\n"


app: Final = FastAPI()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    body: Final = await request.json()
    message: Final = assistant_message(body)
    if message is None:
        return JSONResponse(OVERLOADED, status_code=529)
    full: Final = completion(body.get("model"), message)
    if body.get("stream"):
        return StreamingResponse(stream(full), media_type="text/event-stream")
    return JSONResponse(full)


if __name__ == "__main__":
    parser: Final = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    uvicorn.run(app, host="127.0.0.1", port=parser.parse_args().port, log_level="warning")
