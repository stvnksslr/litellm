"""
Tests for AnthropicResponsesStreamWrapper
(litellm/llms/anthropic/experimental_pass_through/responses_adapters/streaming_iterator.py)
"""

import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../..")))

from litellm.llms.anthropic.experimental_pass_through.responses_adapters.streaming_iterator import (
    AnthropicResponsesStreamWrapper,
)


def _process_all(events: list) -> list:
    wrapper = AnthropicResponsesStreamWrapper(responses_stream=None, model="m")
    for event in events:
        wrapper._process_event(event)
    return list(wrapper._chunk_queue)


def _drain_async(events: list) -> list:
    async def _gen():
        for event in events:
            yield event

    async def _run() -> list:
        wrapper = AnthropicResponsesStreamWrapper(responses_stream=_gen(), model="m")
        return [chunk async for chunk in wrapper]

    return asyncio.run(_run())


class TestMessageStartEmittedExactlyOnce:
    """The ``__anext__`` fallback emits ``message_start`` before consuming the
    stream, so ``_process_event`` must not emit a second one when
    ``response.created`` later arrives. Two ``message_start`` events (byte
    identical, same id) break strict Anthropic SDK clients (e.g. Claude Code)
    with 'Content block is not a thinking block' once thinking blocks follow."""

    def test_response_created_does_not_duplicate_message_start(self):
        chunks = _drain_async(
            [
                {"type": "response.created"},
                {"type": "response.output_text.delta", "item_id": "m1", "delta": "hi"},
            ]
        )
        message_starts = [c for c in chunks if c["type"] == "message_start"]
        assert len(message_starts) == 1

    def test_message_start_is_first_event(self):
        chunks = _drain_async([{"type": "response.created"}])
        assert chunks[0]["type"] == "message_start"


class TestProcessEventResponseCreatedGuard:
    """``_process_event`` must emit ``message_start`` exactly once even if
    ``response.created`` arrives more than once. The guard mirrors the
    ``__anext__`` fallback's ``_sent_message_start`` flag, so a direct caller
    and the async fallback can never double-emit. This also exercises the
    guard's emit-branch, which the async path never reaches because the
    fallback sets the flag before the upstream stream is consumed."""

    def test_first_response_created_emits_message_start(self):
        chunks = _process_all([{"type": "response.created"}])
        assert len(chunks) == 1
        assert chunks[0]["type"] == "message_start"
        assert chunks[0]["message"]["model"] == "m"

    def test_second_response_created_is_skipped(self):
        chunks = _process_all([{"type": "response.created"}, {"type": "response.created"}])
        message_starts = [c for c in chunks if c["type"] == "message_start"]
        assert len(message_starts) == 1


class TestReasoningItemWithoutSummaryText:
    """Regression: a reasoning item whose summary never produces text must not
    surface as a thinking content block.

    OpenAI emits ``response.output_item.added`` with ``type: "reasoning"`` on
    every reasoning turn, but only emits
    ``response.reasoning_summary_text.delta`` when a summary was requested and
    the model actually produced one. Eagerly opening the block on
    ``output_item.added`` left ``{"type": "thinking", "thinking": ""}`` in the
    assistant turn, which clients persist in their session transcript. Replaying
    that transcript against an Anthropic model (what ``claude --resume`` does
    once the resumed session falls back to the default Anthropic model) fails
    with::

        400 invalid_request_error - messages.2.content.0.thinking:
        each thinking block must contain thinking

    So the thinking block is opened on the first non-empty summary delta.
    """

    @staticmethod
    def _gpt_turn(reasoning_summary_deltas: list) -> list:
        return [
            {"type": "response.created"},
            {"type": "response.output_item.added", "item": {"type": "reasoning", "id": "rs_1"}},
            *(
                {"type": "response.reasoning_summary_text.delta", "item_id": "rs_1", "delta": delta}
                for delta in reasoning_summary_deltas
            ),
            {"type": "response.output_item.done", "item": {"type": "reasoning", "id": "rs_1"}},
            {"type": "response.output_item.added", "item": {"type": "message", "id": "msg_1"}},
            {"type": "response.output_text.delta", "item_id": "msg_1", "delta": "Hello"},
            {"type": "response.output_item.done", "item": {"type": "message", "id": "msg_1"}},
        ]

    def test_reasoning_without_summary_emits_no_thinking_block(self):
        chunks = _drain_async(self._gpt_turn(reasoning_summary_deltas=[]))

        assert not [
            c for c in chunks if c["type"] == "content_block_start" and c["content_block"]["type"] == "thinking"
        ]
        assert [(c["type"], c.get("index")) for c in chunks[1:]] == [
            ("content_block_start", 0),
            ("content_block_delta", 0),
            ("content_block_stop", 0),
        ]
        assert chunks[1]["content_block"] == {"type": "text", "text": ""}

    def test_reasoning_with_only_empty_summary_deltas_emits_no_thinking_block(self):
        chunks = _drain_async(self._gpt_turn(reasoning_summary_deltas=["", ""]))

        assert not [c for c in chunks if c["type"] == "content_block_delta" and c["delta"]["type"] == "thinking_delta"]
        assert not [
            c for c in chunks if c["type"] == "content_block_start" and c["content_block"]["type"] == "thinking"
        ]

    def test_reasoning_with_summary_text_still_emits_a_thinking_block(self):
        chunks = _drain_async(self._gpt_turn(reasoning_summary_deltas=["Weigh", "ing options"]))

        assert [(c["type"], c.get("index")) for c in chunks[1:]] == [
            ("content_block_start", 0),
            ("content_block_delta", 0),
            ("content_block_delta", 0),
            ("content_block_stop", 0),
            ("content_block_start", 1),
            ("content_block_delta", 1),
            ("content_block_stop", 1),
        ]
        assert chunks[1]["content_block"] == {"type": "thinking", "thinking": "", "signature": ""}
        assert "".join(c["delta"]["thinking"] for c in chunks[2:4]) == "Weighing options"

    def test_the_reasoning_item_id_is_never_streamed_as_a_signature(self):
        """A stand-in signature would be replayed as a real one, so none is ever sent."""
        chunks = _drain_async(self._gpt_turn(reasoning_summary_deltas=["Weighing options"]))

        assert not [c for c in chunks if c.get("delta", {}).get("type") == "signature_delta"]


class TestToolUseBlockClosedExactlyOnce:
    """Regression for https://github.com/BerriAI/litellm/issues/37273.

    With ``custom_llm_provider: openai`` + ``use_chat_completions_api: true``,
    ``/v1/messages`` streams through ``LiteLLMCompletionStreamingIterator``,
    which ends a tool-call turn with two ``response.output_item.done`` events:
    one for the function_call item (id = call_id) and one for a synthetic
    message item whose id is the upstream chatcmpl id and was never opened as a
    content block. Resolving that unknown item id to ``_current_block_index``
    closed the tool_use block a second time::

        content_block_start[0](tool_use) -> content_block_stop[0]
        -> content_block_stop[0] -> message_delta(stop_reason=tool_use)

    Anthropic SDK clients (e.g. Claude Code) materialize one tool_use block per
    ``content_block_stop``, so the tool executed twice. An ``output_item.done``
    for an item that never opened a block must emit nothing.
    """

    @staticmethod
    def _chat_completions_bridge_tool_turn() -> list[dict[str, object]]:
        return [
            {"type": "response.created"},
            {
                "type": "response.output_item.added",
                "item": {"type": "function_call", "id": "call_1", "call_id": "call_1", "name": "get_weather"},
            },
            {"type": "response.function_call_arguments.delta", "item_id": "call_1", "delta": '{"city": "'},
            {"type": "response.function_call_arguments.delta", "item_id": "call_1", "delta": 'Tokyo"}'},
            {
                "type": "response.function_call_arguments.done",
                "item_id": "call_1",
                "arguments": '{"city": "Tokyo"}',
            },
            {
                "type": "response.output_item.done",
                "item": {"type": "function_call", "id": "call_1", "call_id": "call_1", "status": "completed"},
            },
            {
                "type": "response.output_item.done",
                "item": {"type": "message", "id": "chatcmpl-123", "status": "completed"},
            },
        ]

    def test_one_content_block_stop_per_content_block_start(self):
        chunks = _drain_async(self._chat_completions_bridge_tool_turn())

        starts = [c["index"] for c in chunks if c["type"] == "content_block_start"]
        stops = [c["index"] for c in chunks if c["type"] == "content_block_stop"]
        assert starts == [0]
        assert stops == [0]

    def test_tool_turn_event_order(self):
        chunks = _drain_async(self._chat_completions_bridge_tool_turn())

        assert [(c["type"], c.get("index")) for c in chunks] == [
            ("message_start", None),
            ("content_block_start", 0),
            ("content_block_delta", 0),
            ("content_block_delta", 0),
            ("content_block_stop", 0),
        ]
        assert chunks[1]["content_block"] == {
            "type": "tool_use",
            "id": "call_1",
            "name": "get_weather",
            "input": {},
        }


class TestProcessEventTextDeltaWithoutOutputItemAdded:
    """Streams that skip response.output_item.added (e.g. LMStudio) must still
    open a text block before any delta and never emit index -1."""

    def test_process_event_synthesizes_content_block_start_before_delta(self):
        chunks = _process_all(
            [
                {"type": "response.output_text.delta", "item_id": "i1", "delta": "Hel"},
                {"type": "response.output_text.delta", "item_id": "i1", "delta": "lo"},
            ]
        )
        assert [c["type"] for c in chunks] == [
            "content_block_start",
            "content_block_delta",
            "content_block_delta",
        ]
        assert chunks[0]["content_block"] == {"type": "text", "text": ""}
        assert [c["index"] for c in chunks] == [0, 0, 0]
        assert chunks[1]["delta"] == {"type": "text_delta", "text": "Hel"}

    def test_process_event_delta_without_item_id_never_yields_negative_index(self):
        chunks = _process_all([{"type": "response.output_text.delta", "delta": "Hi"}])
        assert [(c["type"], c["index"]) for c in chunks] == [
            ("content_block_start", 0),
            ("content_block_delta", 0),
        ]

    def test_process_event_unregistered_item_id_opens_new_text_block(self):
        chunks = _process_all(
            [
                {
                    "type": "response.output_item.added",
                    "item": {"type": "reasoning", "id": "rs_1"},
                },
                {"type": "response.reasoning_summary_text.delta", "item_id": "rs_1", "delta": "hm"},
                {"type": "response.output_text.delta", "item_id": "m1", "delta": "Hi"},
            ]
        )
        assert chunks[2]["type"] == "content_block_start"
        assert chunks[2]["content_block"] == {"type": "text", "text": ""}
        assert [c["index"] for c in chunks[2:]] == [1, 1]

    def test_process_event_registered_item_id_does_not_synthesize_start(self):
        chunks = _process_all(
            [
                {
                    "type": "response.output_item.added",
                    "item": {"type": "message", "id": "m1"},
                },
                {"type": "response.output_text.delta", "item_id": "m1", "delta": "Hi"},
            ]
        )
        assert [(c["type"], c["index"]) for c in chunks] == [
            ("content_block_start", 0),
            ("content_block_delta", 0),
        ]


class TestResponseCompletedUsage:
    """The Anthropic ``message_delta`` usage must report cache reads/writes and
    exclude them from ``input_tokens``, so spend is not billed at the uncached
    input rate."""

    def test_response_completed_usage_carries_cache_tokens(self):
        from litellm.types.llms.openai import ResponseAPIUsage

        response = SimpleNamespace(
            status="completed",
            output=[],
            usage=ResponseAPIUsage(
                input_tokens=4017,
                input_tokens_details={"cached_tokens": 4004, "cache_write_tokens": 10},
                output_tokens=5,
                total_tokens=4022,
            ),
        )
        chunks = _process_all([{"type": "response.completed", "response": response}])
        message_delta = next(c for c in chunks if c["type"] == "message_delta")
        assert message_delta["usage"] == {
            "input_tokens": 3,
            "output_tokens": 5,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 4004,
        }


CITATION = {
    "type": "url_citation",
    "url": "https://github.com/BerriAI/litellm/releases",
    "title": "Releases",
}

# The shape Claude Code's standalone web-search sub-request produces once
# /v1/messages is routed to the Responses API: a hosted web_search_call, then
# the answer text carrying the sources as url_citation annotations.
#
# Captured verbatim from a live azure/gpt-5.6 deployment. The `added` event
# carries only id/type/status - the `action`, and therefore both the query and
# whether this is a search at all, arrives only on `done`. `action.sources` is
# null, so sources reach the client solely as url_citation annotations on the
# text that follows.
SEARCH_CALL_ADDED = {"id": "ws_1", "type": "web_search_call", "status": "in_progress"}
SEARCH_CALL_DONE = {
    "id": "ws_1",
    "type": "web_search_call",
    "status": "completed",
    "action": {
        "type": "search",
        "query": "latest litellm release",
        "queries": ["latest litellm release"],
        "sources": None,
    },
}
WEB_SEARCH_EVENTS = [
    {"type": "response.created"},
    {"type": "response.output_item.added", "item": SEARCH_CALL_ADDED},
    {"type": "response.web_search_call.in_progress", "item_id": "ws_1"},
    {"type": "response.web_search_call.searching", "item_id": "ws_1"},
    {"type": "response.web_search_call.completed", "item_id": "ws_1"},
    {"type": "response.output_item.done", "item": SEARCH_CALL_DONE},
    {"type": "response.output_item.added", "item": {"id": "msg_1", "type": "message"}},
    {"type": "response.output_text.delta", "item_id": "msg_1", "delta": "The latest release "},
    {"type": "response.output_text.annotation.added", "item_id": "msg_1", "annotation": CITATION},
    {"type": "response.output_text.delta", "item_id": "msg_1", "delta": "is v1.96.0."},
    {"type": "response.output_item.done", "item": {"id": "msg_1", "type": "message"}},
    {"type": "response.completed", "response": {"status": "completed", "output": []}},
]


def _with_annotation(annotation: dict, repeat: int = 1) -> list:
    """WEB_SEARCH_EVENTS with its url_citation swapped for ``annotation``."""
    return [
        event
        for original in WEB_SEARCH_EVENTS
        for event in (
            [{**original, "annotation": annotation}] * repeat
            if original["type"] == "response.output_text.annotation.added"
            else [original]
        )
    ]


class TestHostedWebSearchStreaming:
    """A provider-run web search must reach the client as Anthropic-native blocks.

    Without this the search happens but the client sees only naked text: the
    ``web_search_call`` item matches no branch, so no ``server_tool_use`` block
    is opened and the ``url_citation`` annotations carrying the sources are
    dropped entirely.
    """

    def test_block_is_emitted_from_done_not_added(self):
        """The added event has no action, so nothing can be decided from it.

        Emitting the block on added would produce a server_tool_use with an empty
        query, and could not tell a search from a page fetch at all.
        """
        added_only = _drain_async(
            [
                {"type": "response.created"},
                {"type": "response.output_item.added", "item": SEARCH_CALL_ADDED},
                {"type": "response.completed", "response": {"status": "completed", "output": []}},
            ]
        )
        assert [c for c in added_only if c["type"] == "content_block_start"] == []

    def test_web_search_call_opens_server_tool_use_block(self):
        chunks = _drain_async(WEB_SEARCH_EVENTS)
        starts = [c for c in chunks if c["type"] == "content_block_start"]
        assert starts[0]["content_block"] == {
            "type": "server_tool_use",
            "id": "ws_1",
            "name": "web_search",
            "input": {},
        }

    def test_search_query_is_streamed_as_input_json_delta(self):
        chunks = _drain_async(WEB_SEARCH_EVENTS)
        deltas = [c for c in chunks if c.get("delta", {}).get("type") == "input_json_delta"]
        assert [d["delta"]["partial_json"] for d in deltas] == ['{"query": "latest litellm release"}']

    def test_citations_become_a_paired_web_search_tool_result_block(self):
        chunks = _drain_async(WEB_SEARCH_EVENTS)
        results = [
            c["content_block"]
            for c in chunks
            if c["type"] == "content_block_start" and c["content_block"]["type"] == "web_search_tool_result"
        ]
        assert results == [
            {
                "type": "web_search_tool_result",
                "tool_use_id": "ws_1",
                "content": [
                    {
                        "type": "web_search_result",
                        "url": "https://github.com/BerriAI/litellm/releases",
                        "title": "Releases",
                        "page_age": None,
                        "encrypted_content": "",
                        "snippet": "",
                    }
                ],
            }
        ]

    def test_sources_reported_on_the_search_call_are_used(self):
        """Some api-versions attach sources to the call instead of annotating the text."""
        events = [
            {"type": "response.created"},
            {"type": "response.output_item.added", "item": SEARCH_CALL_ADDED},
            {
                "type": "response.output_item.done",
                "item": {
                    "id": "ws_1",
                    "type": "web_search_call",
                    "action": {
                        "type": "search",
                        "query": "q",
                        "sources": [{"type": "url", "url": "https://example.com", "title": "Example"}],
                    },
                },
            },
            {"type": "response.completed", "response": {"status": "completed", "output": []}},
        ]
        chunks = _drain_async(events)
        results = [
            c["content_block"]
            for c in chunks
            if c["type"] == "content_block_start" and c["content_block"]["type"] == "web_search_tool_result"
        ]
        assert results[0]["content"] == [
            {
                "type": "web_search_result",
                "url": "https://example.com",
                "title": "Example",
                "page_age": None,
                "encrypted_content": "",
                "snippet": "",
            }
        ]

    def test_duplicate_citations_are_reported_once(self):
        events = _with_annotation(CITATION, repeat=2)
        chunks = _drain_async(events)
        result = next(
            c["content_block"]
            for c in chunks
            if c["type"] == "content_block_start" and c["content_block"]["type"] == "web_search_tool_result"
        )
        assert len(result["content"]) == 1

    def test_non_web_annotations_are_ignored(self):
        events = _with_annotation({"type": "file_citation", "file_id": "f_1", "filename": "notes.md"})
        chunks = _drain_async(events)
        result = next(
            c["content_block"]
            for c in chunks
            if c["type"] == "content_block_start" and c["content_block"]["type"] == "web_search_tool_result"
        )
        assert result["content"] == []

    def test_page_fetches_open_no_block_and_do_not_shift_indices(self):
        """Azure interleaves ``open_page`` web_search_call items between the real
        searches. They are not searches, and opening a block for them would both
        emit a query-less server_tool_use and shift every later block index."""
        events = [
            *WEB_SEARCH_EVENTS[:6],
            {
                "type": "response.output_item.added",
                "item": {"id": "ws_fetch", "type": "web_search_call", "status": "in_progress"},
            },
            {
                "type": "response.output_item.done",
                "item": {
                    "id": "ws_fetch",
                    "type": "web_search_call",
                    "status": "completed",
                    "action": {"type": "open_page", "url": "https://github.com/BerriAI/litellm/releases/latest"},
                },
            },
            *WEB_SEARCH_EVENTS[6:],
        ]
        chunks = _drain_async(events)
        server_tool_uses = [
            c["content_block"]
            for c in chunks
            if c["type"] == "content_block_start" and c["content_block"]["type"] == "server_tool_use"
        ]
        assert [b["id"] for b in server_tool_uses] == ["ws_1"]
        assert [(c["type"], c["index"]) for c in chunks if c["type"] == "content_block_start"] == [
            ("content_block_start", 0),
            ("content_block_start", 1),
            ("content_block_start", 2),
        ]
        starts = sorted(c["index"] for c in chunks if c["type"] == "content_block_start")
        assert starts == sorted(c["index"] for c in chunks if c["type"] == "content_block_stop")

    def test_every_opened_block_is_closed_exactly_once(self):
        chunks = _drain_async(WEB_SEARCH_EVENTS)
        starts = sorted(c["index"] for c in chunks if c["type"] == "content_block_start")
        stops = sorted(c["index"] for c in chunks if c["type"] == "content_block_stop")
        assert starts == stops
        assert len(starts) == len(set(starts))


class TestOutputItemDoneDoesNotCloseForeignBlocks:
    """``output_item.done`` used to fall back to ``_current_block_index`` for any
    item it had no block for, so an unsupported hosted-tool item closed whichever
    block happened to be open. The text block then received deltas after its own
    ``content_block_stop``, which strict Anthropic clients reject."""

    def test_unopened_item_does_not_close_the_open_text_block(self):
        chunks = _process_all(
            [
                {"type": "response.output_item.added", "item": {"type": "message", "id": "msg_1"}},
                {"type": "response.output_text.delta", "item_id": "msg_1", "delta": "Hi"},
                {"type": "response.output_item.done", "item": {"id": "ci_1", "type": "code_interpreter_call"}},
                {"type": "response.output_text.delta", "item_id": "msg_1", "delta": " there"},
            ]
        )
        assert [c["type"] for c in chunks] == [
            "content_block_start",
            "content_block_delta",
            "content_block_delta",
        ]
