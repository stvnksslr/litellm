#!/usr/bin/env python3
"""Scripted stand-in for the GLM (OpenAI chat) and Claude (Anthropic messages) upstreams.

Every request litellm routes here is appended to a JSONL log with the upstream that received it and the
Claude Code hint headers the proxy forwarded, so a run shows which deployment each request class landed on.
Requests without tools (auto mode classifier stages, titles) get a 529 and never a verdict, so the probe
command is never approved and auto mode fails closed.
"""

import argparse
import json
import os
import sys
import time
import uuid
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

Upstream: TypeAlias = Literal["glm", "claude"]
JsonObject: TypeAlias = Mapping[str, object]

LOG_PATH: Final = Path(os.environ.get("HARNESS_LOG", "routing.jsonl"))
PROBE_COMMAND: Final = os.environ.get("HARNESS_COMMAND", "python3 -c \"print('harness probe')\"")
OVERLOADED: Final = {"type": "error", "error": {"type": "overloaded_error", "message": "harness: no verdicts"}}
HINT_HEADERS: Final = ("x-claude-code-request-class", "x-claude-code-agent-type", "x-claude-code-compaction")


@dataclass(frozen=True, slots=True)
class ToolCall:
    command: str
    kind: Literal["tool_call"] = "tool_call"


@dataclass(frozen=True, slots=True)
class Text:
    text: str
    kind: Literal["text"] = "text"


@dataclass(frozen=True, slots=True)
class Refused:
    kind: Literal["refused"] = "refused"


Answer: TypeAlias = ToolCall | Text
Reply: TypeAlias = Answer | Refused


def _list(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def _is_tool_result_turn(upstream: Upstream, messages: Sequence[object]) -> bool:
    last: Final = messages[-1] if messages else None
    if not isinstance(last, dict):
        return False
    if upstream == "glm":
        return last.get("role") == "tool"
    return any(isinstance(block, dict) and block.get("type") == "tool_result" for block in _list(last.get("content")))


def choose_reply(upstream: Upstream, body: JsonObject) -> Reply:
    if not _list(body.get("tools")):
        return Refused()
    if _is_tool_result_turn(upstream, _list(body.get("messages"))):
        return Text("harness done")
    return ToolCall(PROBE_COMMAND)


def record(upstream: Upstream, body: JsonObject, headers: Mapping[str, str], reply: Reply) -> None:
    entry: Final = {
        "ts": round(time.time(), 3),
        "upstream": upstream,
        "model": body.get("model"),
        "stream": bool(body.get("stream")),
        **{name.removeprefix("x-claude-code-"): headers.get(name) for name in HINT_HEADERS},
        "stop": body.get("stop") or body.get("stop_sequences"),
        "max_tokens": body.get("max_tokens") or body.get("max_completion_tokens"),
        "tools": len(_list(body.get("tools"))),
        "messages": len(_list(body.get("messages"))),
        "reply": reply.kind,
    }
    with LOG_PATH.open("a") as log:
        log.write(json.dumps(entry) + "\n")
    sys.stdout.write(json.dumps(entry) + "\n")
    sys.stdout.flush()


def _tool_input(reply: ToolCall) -> str:
    return json.dumps({"command": reply.command, "description": "harness probe"})


def _sse(event: str | None, payload: object) -> str:
    prefix: Final = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(payload)}\n\n"


def openai_message(model: object, reply: Answer) -> JsonObject:
    match reply:
        case ToolCall():
            message: JsonObject = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"call_{uuid.uuid4().hex[:12]}",
                        "type": "function",
                        "function": {"name": "Bash", "arguments": _tool_input(reply)},
                    }
                ],
            }
            finish = "tool_calls"
        case Text(text=text):
            message = {"role": "assistant", "content": text}
            finish = "stop"
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def openai_stream(model: object, reply: Answer) -> Iterator[str]:
    full: Final = openai_message(model, reply)
    choice: Final = _list(full["choices"])[0]
    assert isinstance(choice, dict)
    base: Final = {k: full[k] for k in ("id", "created", "model")} | {"object": "chat.completion.chunk"}
    yield _sse(None, base | {"choices": [{"index": 0, "delta": choice["message"], "finish_reason": None}]})
    yield _sse(None, base | {"choices": [{"index": 0, "delta": {}, "finish_reason": choice["finish_reason"]}]})
    yield _sse(None, base | {"choices": [], "usage": full["usage"]})
    yield "data: [DONE]\n\n"


def anthropic_block(reply: Answer) -> JsonObject:
    match reply:
        case ToolCall():
            return {
                "type": "tool_use",
                "id": f"toolu_{uuid.uuid4().hex[:20]}",
                "name": "Bash",
                "input": json.loads(_tool_input(reply)),
            }
        case Text(text=text):
            return {"type": "text", "text": text}


def anthropic_message(model: object, reply: Answer) -> JsonObject:
    return {
        "id": f"msg_{uuid.uuid4().hex[:20]}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [anthropic_block(reply)],
        "stop_reason": "tool_use" if isinstance(reply, ToolCall) else "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def anthropic_stream(model: object, reply: Answer) -> Iterator[str]:
    full: Final = anthropic_message(model, reply)
    block: Final = anthropic_block(reply)
    start_block: Final = {**block, "input": {}} if isinstance(reply, ToolCall) else {**block, "text": ""}
    delta: Final = (
        {"type": "input_json_delta", "partial_json": _tool_input(reply)}
        if isinstance(reply, ToolCall)
        else {"type": "text_delta", "text": reply.text}
    )
    yield _sse("message_start", {"type": "message_start", "message": {**full, "content": [], "stop_reason": None}})
    yield _sse("content_block_start", {"type": "content_block_start", "index": 0, "content_block": start_block})
    yield _sse("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta})
    yield _sse("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield _sse(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": full["stop_reason"], "stop_sequence": None},
            "usage": {"output_tokens": 1},
        },
    )
    yield _sse("message_stop", {"type": "message_stop"})


app: Final = FastAPI()


async def _read(request: Request, upstream: Upstream) -> tuple[JsonObject, Reply]:
    body: Final = await request.json()
    reply: Final = choose_reply(upstream, body)
    record(upstream, body, request.headers, reply)
    return body, reply


@app.post("/glm/v1/chat/completions")
async def glm_chat(request: Request) -> Response:
    body, reply = await _read(request, "glm")
    if isinstance(reply, Refused):
        return JSONResponse(OVERLOADED, status_code=529)
    if body.get("stream"):
        return StreamingResponse(openai_stream(body.get("model"), reply), media_type="text/event-stream")
    return JSONResponse(openai_message(body.get("model"), reply))


@app.post("/claude/v1/messages")
async def claude_messages(request: Request) -> Response:
    body, reply = await _read(request, "claude")
    if isinstance(reply, Refused):
        return JSONResponse(OVERLOADED, status_code=529)
    if body.get("stream"):
        return StreamingResponse(anthropic_stream(body.get("model"), reply), media_type="text/event-stream")
    return JSONResponse(anthropic_message(body.get("model"), reply))


def report(log_path: Path) -> None:
    rows: Final = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    counts: Final = Counter(
        (row["request-class"], row["upstream"], row["model"], json.dumps(row["stop"]), row["max_tokens"])
        for row in rows
    )
    header: Final = f"{'count':>5}  {'request-class':<14} {'upstream':<8} {'model':<22} {'stop':<16} max_tokens"
    lines: Final = (
        f"{count:>5}  {request_class!s:<14} {upstream:<8} {model!s:<22} {stop:<16} {max_tokens}"
        for (request_class, upstream, model, stop, max_tokens), count in sorted(counts.items(), key=str)
    )
    sys.stdout.write("\n".join((header, *lines)) + "\n")


def main() -> None:
    parser: Final = argparse.ArgumentParser()
    commands: Final = parser.add_subparsers(dest="command", required=True)
    serve: Final = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    commands.add_parser("report").add_argument("log", type=Path)
    args: Final = parser.parse_args()
    if args.command == "report":
        report(args.log)
        return
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
