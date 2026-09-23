"""litellm callback that appends one JSONL row per /v1/messages request: which model group Claude Code asked
for, which deployment served it, and the Claude Code hint headers. `python routing_recorder.py LOG` prints a
summary
"""

import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from litellm.integrations.custom_logger import CustomLogger

LOG_PATH: Final = Path(os.environ.get("HARNESS_LOG", "routing.jsonl"))


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def routing_row(request: Mapping[str, object], logged: Mapping[str, object], outcome: str) -> Mapping[str, object]:
    headers: Final = {str(k).lower(): v for k, v in _mapping(request.get("headers")).items()}
    body: Final = _mapping(request.get("body"))
    tools: Final = body.get("tools")
    return {
        "ts": round(time.time(), 3),
        "outcome": outcome,
        "request_class": headers.get("x-claude-code-request-class"),
        "agent_type": headers.get("x-claude-code-agent-type"),
        "requested": body.get("model"),
        "deployment": logged.get("model"),
        "api_base": logged.get("api_base"),
        "stop": body.get("stop_sequences"),
        "max_tokens": body.get("max_tokens"),
        "tools": len(tools) if isinstance(tools, list) else 0,
    }


def _append(row: Mapping[str, object]) -> None:
    with LOG_PATH.open("a") as log:
        log.write(json.dumps(row) + "\n")


class RoutingRecorder(CustomLogger):
    def _record(self, kwargs: Mapping[str, object], outcome: str) -> None:
        litellm_params: Final = _mapping(kwargs.get("litellm_params"))
        _append(
            routing_row(
                _mapping(litellm_params.get("proxy_server_request")),
                _mapping(kwargs.get("standard_logging_object")),
                outcome,
            )
        )

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time) -> None:
        self._record(kwargs, "ok")

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time) -> None:
        self._record(kwargs, "error")

    async def async_post_call_failure_hook(
        self, request_data, original_exception, user_api_key_dict, traceback_str=None
    ):
        if "standard_logging_object" not in request_data:
            _append(
                routing_row(
                    _mapping(request_data.get("proxy_server_request")),
                    {"model": f"rejected: {type(original_exception).__name__}"},
                    "rejected",
                )
            )


proxy_handler_instance: Final = RoutingRecorder()


def report(log_path: Path) -> str:
    rows: Final = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    counts: Final = Counter(
        (row["request_class"], row["requested"], row["deployment"], row["outcome"], json.dumps(row["stop"]))
        for row in rows
    )
    header: Final = f"{'count':>5}  {'class':<10} {'requested':<16} {'deployment':<28} {'outcome':<9} stop"
    lines: Final = (
        f"{count:>5}  {cls!s:<10} {requested!s:<16} {deployment!s:<28} {outcome:<9} {stop}"
        for (cls, requested, deployment, outcome, stop), count in sorted(counts.items(), key=str)
    )
    return "\n".join((header, *lines))


if __name__ == "__main__":
    sys.stdout.write(report(Path(sys.argv[1])) + "\n")
