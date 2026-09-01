"""
Transformation layer: Anthropic /v1/messages <-> OpenAI Responses API.

This module owns all format conversions for the direct v1/messages -> Responses API
path used for OpenAI and Azure models.
"""

import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from types import MappingProxyType
from typing import Any, Final, cast

from typing_extensions import assert_never

from litellm.litellm_core_utils.prompt_templates.common_utils import (
    TOOL_RESULT_IMAGE_BOUNDARY,
    TOOL_RESULT_IMAGE_PLACEHOLDER,
    with_prompt_cache_breakpoint,
)
from litellm.litellm_core_utils.reasoning_effort_utils import (
    reasoning_effort_from_thinking_budget,
)
from litellm.llms.anthropic.common_utils import (
    AnthropicWebSearchResult,
    build_anthropic_web_search_tool_result_block,
    web_search_result_from_source,
)
from litellm.llms.anthropic.experimental_pass_through.utils import (
    is_reasoning_auto_summary_enabled,
    prompt_cache_key_from_user_id,
)
from litellm.types.llms.anthropic import (
    ANTHROPIC_HOSTED_TOOLS,
    AllAnthropicPassThroughMessageValues,
    AllAnthropicToolsValues,
    AnthropicFinishReason,
    AnthropicMessagesRequest,
    AnthropicMessagesToolChoice,
    AnthropicResponseContentBlockServerToolUse,
    AnthropicResponseContentBlockText,
    AnthropicResponseContentBlockThinking,
    AnthropicResponseContentBlockToolUse,
    AnthropicSystemMessageContent,
    is_anthropic_web_search_tool,
)
from litellm.types.llms.anthropic_messages.anthropic_response import (
    AnthropicMessagesResponse,
    AnthropicUsage,
)
from litellm.types.llms.openai import ResponseAPIUsage, ResponsesAPIResponse

# The Responses API hosted web search tool. ``web_search_preview`` is the
# legacy 4o-era alias; current models (incl. Azure gpt-5.x, which is the only
# way Anthropic's server-side web search can be served on that backend) expect
# the unprefixed name.
RESPONSES_WEB_SEARCH_TOOL_TYPE = "web_search"
_RESPONSES_WEB_SEARCH_TOOL: Mapping[str, object] = MappingProxyType({"type": RESPONSES_WEB_SEARCH_TOOL_TYPE})


@dataclass(frozen=True, slots=True)
class _Thinking:
    text: str


@dataclass(frozen=True, slots=True)
class _Text:
    text: str
    citations: tuple[AnthropicWebSearchResult, ...]


@dataclass(frozen=True, slots=True)
class _ToolUse:
    id: str
    name: str
    arguments: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class _SearchCall:
    id: str
    query: str


_ResponseOutputItem = _Thinking | _Text | _ToolUse | _SearchCall


_EMPTY_MAPPING: Mapping[str, object] = MappingProxyType({})


def as_responses_item_mapping(item: object) -> Mapping[str, object]:
    """Best-effort read-only view of a Responses API output item or event payload.

    The typed ``openai.types.responses`` models for hosted tools vary across SDK
    versions (and some backends return raw dicts), so read them structurally
    rather than importing every concrete class.
    """
    if isinstance(item, dict):
        return cast(Mapping[str, object], item)  # cast-ok: untyped SDK payload, read-only
    dump = getattr(item, "model_dump", None)
    if not callable(dump):
        return _EMPTY_MAPPING
    try:
        return cast(Mapping[str, object], dump())  # cast-ok: model_dump() is untyped; read-only here
    except (TypeError, ValueError):
        return _EMPTY_MAPPING


def web_search_call_query(item: Mapping[str, object]) -> str | None:
    """The search query a ``web_search_call`` item ran, or None when it is not a search.

    Azure/OpenAI report page fetches the model performed while searching as
    ``web_search_call`` items too, with ``action.type == "open_page"`` and no
    query. Anthropic models only the search itself as ``server_tool_use``, so a
    fetch has nothing to translate into and is skipped rather than surfaced as a
    search with an empty query.
    """
    action = as_responses_item_mapping(item.get("action"))
    query = action.get("query")
    if action.get("type") not in (None, "search") or not query:
        return None
    return str(query)


def _json_object(arguments: object) -> Mapping[str, object]:
    if not isinstance(arguments, str) or not arguments:
        return _EMPTY_MAPPING
    try:
        parsed = json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return _EMPTY_MAPPING
    return parsed if isinstance(parsed, dict) else _EMPTY_MAPPING


def _url_citations(annotations: object) -> tuple[AnthropicWebSearchResult, ...]:
    if not isinstance(annotations, (list, tuple)):
        return ()
    mapped = (web_search_result_from_source(as_responses_item_mapping(annotation)) for annotation in annotations)
    return tuple(result for result in mapped if result is not None)


def _parse_output_item(item: object) -> tuple[_ResponseOutputItem, ...]:
    from openai.types.responses import (
        ResponseFunctionToolCall,
        ResponseOutputMessage,
        ResponseReasoningItem,
    )

    if isinstance(item, ResponseReasoningItem):
        return tuple(
            _Thinking(text=getattr(summary, "text", "")) for summary in item.summary if getattr(summary, "text", "")
        )

    if isinstance(item, ResponseOutputMessage):
        return tuple(
            _Text(
                text=getattr(part, "text", "") or "",
                citations=_url_citations(getattr(part, "annotations", None)),
            )
            for part in item.content
            if getattr(part, "type", None) == "output_text"
        )

    if isinstance(item, ResponseFunctionToolCall):
        return (
            _ToolUse(
                id=item.call_id or item.id or "",
                name=item.name,
                arguments=_json_object(item.arguments),
            ),
        )

    data = as_responses_item_mapping(item)
    item_type = data.get("type")

    if item_type == "reasoning":
        summaries = data.get("summary")
        if not isinstance(summaries, (list, tuple)):
            return ()
        return tuple(
            _Thinking(text=str(as_responses_item_mapping(summary).get("text")))
            for summary in summaries
            if as_responses_item_mapping(summary).get("text")
        )

    if item_type == "message":
        parts = data.get("content")
        if not isinstance(parts, (list, tuple)):
            return ()
        texts = (as_responses_item_mapping(part) for part in parts)
        return tuple(
            _Text(text=str(part.get("text") or ""), citations=_url_citations(part.get("annotations")))
            for part in texts
            if part.get("type") == "output_text"
        )

    if item_type == "function_call":
        return (
            _ToolUse(
                id=str(data.get("call_id") or data.get("id") or ""),
                name=str(data.get("name") or ""),
                arguments=_json_object(data.get("arguments")),
            ),
        )

    if item_type == "web_search_call":
        query = web_search_call_query(data)
        if query is None:
            return ()
        return (_SearchCall(id=str(data.get("id") or f"srvtoolu_{uuid.uuid4().hex}"), query=query),)

    return ()


def _parse_response_output(output: Iterable[object]) -> tuple[_ResponseOutputItem, ...]:
    return tuple(chain.from_iterable(_parse_output_item(item) for item in output))


def _fold_to_anthropic_blocks(items: tuple[_ResponseOutputItem, ...]) -> tuple[Mapping[str, object], ...]:
    """Fold parsed output items into Anthropic content blocks.

    Emits Anthropic's canonical ordering for a server-side search turn:
    ``server_tool_use`` -> ``web_search_tool_result`` -> ``text``.

    The Responses API reports citations aggregated on the final message rather
    than per search call, so every citation is attached to the last search
    call's result block instead of being split across them on a guess.
    """
    citations = tuple(chain.from_iterable(item.citations for item in items if isinstance(item, _Text)))
    search_ids = tuple(item.id for item in items if isinstance(item, _SearchCall))
    last_search_id = search_ids[-1] if search_ids else None

    def blocks_for(item: _ResponseOutputItem) -> tuple[Mapping[str, object], ...]:
        match item:
            case _Thinking(text=text):
                return (
                    AnthropicResponseContentBlockThinking(type="thinking", thinking=text, signature=None).model_dump(),
                )
            case _Text(text=text):
                return (AnthropicResponseContentBlockText(type="text", text=text).model_dump(),)
            case _ToolUse(id=call_id, name=name, arguments=arguments):
                return (
                    AnthropicResponseContentBlockToolUse(
                        type="tool_use", id=call_id, name=name, input=arguments
                    ).model_dump(),
                )
            case _SearchCall(id=call_id, query=query):
                return (
                    AnthropicResponseContentBlockServerToolUse(
                        id=call_id,
                        name=ANTHROPIC_HOSTED_TOOLS.WEB_SEARCH.value,
                        input={"query": query},
                    ).model_dump(),
                    build_anthropic_web_search_tool_result_block(
                        tool_use_id=call_id,
                        results=citations if call_id == last_search_id else (),
                    ),
                )
        assert_never(item)

    return tuple(chain.from_iterable(blocks_for(item) for item in items))


class LiteLLMAnthropicToResponsesAPIAdapter:
    """
    Converts Anthropic /v1/messages requests to OpenAI Responses API format and
    converts Responses API responses back to Anthropic format.
    """

    @staticmethod
    def translate_responses_api_usage_to_anthropic_usage(
        raw_usage: ResponseAPIUsage | None,
    ) -> AnthropicUsage:
        """Map Responses API usage onto Anthropic usage, where ``input_tokens``
        excludes the cache-read and cache-write tokens reported alongside it.
        """
        if raw_usage is None:
            return AnthropicUsage(input_tokens=0, output_tokens=0)

        from litellm.llms.anthropic.experimental_pass_through.adapters.transformation import (
            LiteLLMAnthropicMessagesAdapter,
        )
        from litellm.responses.utils import ResponseAPILoggingUtils

        chat_usage = ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(raw_usage)
        return LiteLLMAnthropicMessagesAdapter._translate_openai_usage_to_anthropic_usage(chat_usage)

    # ------------------------------------------------------------------ #
    # Request translation: Anthropic -> Responses API                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _translate_anthropic_image_source_to_url(source: object) -> str | None:
        """Convert Anthropic image source to a URL string."""
        if not isinstance(source, dict):
            return None
        source_type: Final = source.get("type")
        if source_type == "base64":
            media_type: Final = source.get("media_type", "image/jpeg")
            data: Final = source.get("data", "")
            return f"data:{media_type};base64,{data}" if data else None
        elif source_type == "url":
            return source.get("url")
        return None

    @staticmethod
    def _translate_midturn_system_content_to_responses(
        content: str | Iterable[AnthropicSystemMessageContent],
    ) -> list[dict[str, object]]:  # mutable-ok: API message payload
        """Convert in-sequence system content to Responses input-text parts."""
        if isinstance(content, str):
            return (
                [{"type": "input_text", "text": content}] if content else []  # mutable-ok: API message payload
            )  # mutable-ok: API message payload
        if not isinstance(content, list):
            return []  # mutable-ok: API message payload
        return [  # mutable-ok: API message payload
            with_prompt_cache_breakpoint(
                {"type": "input_text", "text": text}, block.get("prompt_cache_breakpoint")
            )  # mutable-ok: API message payload
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and (text := block.get("text"))  # pyright: ignore[reportUnnecessaryIsInstance]  # untrusted client payload
        ]

    def translate_messages_to_responses_input(
        self,
        messages: list[AllAnthropicPassThroughMessageValues],
    ) -> list[dict[str, Any]]:
        """
        Convert Anthropic messages list to Responses API `input` items.

        Mapping:
          system text        -> message(role=system, input_text)
          user text          -> message(role=user, input_text)
          user image         -> message(role=user, input_image)
          user tool_result   -> function_call_output
          assistant text     -> message(role=assistant, output_text)
          assistant tool_use -> function_call
        """
        input_items: Final[list[dict[str, Any]]] = []

        for m in messages:
            if m["role"] == "system":
                system_parts = self._translate_midturn_system_content_to_responses(m.get("content"))
                if system_parts:
                    input_items.append(
                        {  # mutable-ok: API message payload
                            "type": "message",
                            "role": "system",
                            "content": system_parts,
                        }
                    )
                continue

            role = m["role"]
            content = m.get("content")

            if role == "user":
                if isinstance(content, str):
                    input_items.append(
                        {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": content}],
                        }
                    )
                elif isinstance(content, list):
                    user_parts: list[dict[str, Any]] = []
                    tool_image_parts: list[dict[str, Any]] = []  # mutable-ok: json content parts
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            user_parts.append(
                                with_prompt_cache_breakpoint(
                                    {"type": "input_text", "text": block.get("text", "")},
                                    block.get("prompt_cache_breakpoint"),
                                )
                            )
                        elif btype == "image":
                            url = self._translate_anthropic_image_source_to_url(cast(dict, block.get("source", {})))
                            if url:
                                user_parts.append(
                                    with_prompt_cache_breakpoint(
                                        {"type": "input_image", "image_url": url}, block.get("prompt_cache_breakpoint")
                                    )
                                )
                        elif btype == "tool_result":
                            tool_use_id = block.get("tool_use_id", "")
                            inner = block.get("content")
                            if inner is None:
                                output_text = ""
                            elif isinstance(inner, str):
                                output_text = inner
                            elif isinstance(inner, list):
                                parts = [
                                    c.get("text", "") for c in inner if isinstance(c, dict) and c.get("type") == "text"
                                ]
                                output_text = "\n".join(parts)
                                image_candidates = tuple(
                                    self._translate_anthropic_image_source_to_url(c.get("source"))
                                    for c in inner
                                    if isinstance(c, dict) and c.get("type") == "image"
                                )
                                image_urls = tuple(url for url in image_candidates if url)
                                if image_urls:
                                    output_text = (
                                        f"{output_text}\n{TOOL_RESULT_IMAGE_PLACEHOLDER}"
                                        if output_text
                                        else TOOL_RESULT_IMAGE_PLACEHOLDER
                                    )
                                    tool_image_parts.extend(
                                        {"type": "input_image", "image_url": url}  # mutable-ok: json content part
                                        for url in image_urls
                                    )
                            else:
                                output_text = str(inner)
                            # tool_result is a top-level item, not inside the message
                            input_items.append(
                                {
                                    "type": "function_call_output",
                                    "call_id": tool_use_id,
                                    "output": output_text,
                                }
                            )
                    if tool_image_parts:
                        boundary_part = {  # mutable-ok: json content part
                            "type": "input_text",
                            "text": TOOL_RESULT_IMAGE_BOUNDARY,
                        }
                        input_items.append(
                            {  # mutable-ok: json input item
                                "type": "message",
                                "role": "user",
                                "content": [boundary_part, *tool_image_parts],  # mutable-ok: json content list
                            }
                        )
                    if user_parts:
                        input_items.append(
                            {
                                "type": "message",
                                "role": "user",
                                "content": user_parts,
                            }
                        )

            elif role == "assistant":
                if isinstance(content, str):
                    input_items.append(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": content}],
                        }
                    )
                elif isinstance(content, list):
                    asst_parts: list[dict[str, Any]] = []
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            asst_parts.append({"type": "output_text", "text": block.get("text", "")})
                        elif btype == "tool_use":
                            # tool_use becomes a top-level function_call item
                            input_items.append(
                                {
                                    "type": "function_call",
                                    "call_id": block.get("id", ""),
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {})),
                                }
                            )
                        elif btype == "thinking":
                            thinking_text = block.get("thinking", "")
                            if thinking_text:
                                asst_parts.append({"type": "output_text", "text": thinking_text})
                    if asst_parts:
                        input_items.append(
                            {
                                "type": "message",
                                "role": "assistant",
                                "content": asst_parts,
                            }
                        )

        return input_items

    def translate_tools_to_responses_api(
        self,
        tools: list[AllAnthropicToolsValues],
    ) -> list[dict[str, Any]]:
        """Convert Anthropic tool definitions to Responses API function tools."""
        result: Final[list[dict[str, Any]]] = []
        for tool in tools:
            tool_dict = cast(dict[str, Any], tool)
            tool_name = tool_dict.get("name", "")
            if is_anthropic_web_search_tool(tool_dict):
                result.append(dict(_RESPONSES_WEB_SEARCH_TOOL))
                continue
            # Responses turns strict mode on when `strict` is omitted, silently rewriting
            # `required` to every property. Anthropic tools are non-strict unless asked.
            func_tool: dict[str, Any] = {
                "type": "function",
                "name": tool_name,
                "strict": bool(tool_dict.get("strict")),
            }
            if "description" in tool_dict:
                func_tool["description"] = tool_dict["description"]
            if "input_schema" in tool_dict:
                func_tool["parameters"] = tool_dict["input_schema"]
            result.append(func_tool)
        return result

    @staticmethod
    def translate_tool_choice_to_responses_api(
        tool_choice: AnthropicMessagesToolChoice,
        translated_tools: Sequence[Mapping[str, object]] | None = None,
    ) -> str | dict[str, Any]:
        """Convert Anthropic tool_choice to Responses API tool_choice.

        ``translated_tools`` is the already-converted tool list. A forced choice
        naming Anthropic's hosted web search must resolve to the hosted
        Responses tool, because ``translate_tools_to_responses_api`` replaced
        that tool definition - emitting a function choice for it would name a
        tool that is no longer in the request.
        """
        tc_type: Final = tool_choice.get("type")
        if tc_type == "any":
            return "required"
        elif tc_type == "tool":
            name = tool_choice.get("name", "")
            if name == ANTHROPIC_HOSTED_TOOLS.WEB_SEARCH.value and any(
                tool.get("type") == RESPONSES_WEB_SEARCH_TOOL_TYPE for tool in translated_tools or ()
            ):
                return dict(_RESPONSES_WEB_SEARCH_TOOL)
            return {"type": "function", "name": name}
        elif tc_type == "none":
            return "none"
        return "auto"

    @staticmethod
    def translate_context_management_to_responses_api(
        context_management: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """
        Convert Anthropic context_management dict to OpenAI Responses API array format.

        Anthropic format: {"edits": [{"type": "compact_20260112", "trigger": {"type": "input_tokens", "value": 150000}}]}
        OpenAI format:    [{"type": "compaction", "compact_threshold": 150000}]
        """
        if not isinstance(context_management, dict):
            return None

        edits: Final = context_management.get("edits", [])
        if not isinstance(edits, list):
            return None

        result: Final[list[dict[str, Any]]] = []
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            edit_type = edit.get("type", "")
            if edit_type == "compact_20260112":
                entry: dict[str, Any] = {"type": "compaction"}
                trigger = edit.get("trigger")
                if isinstance(trigger, dict) and trigger.get("value") is not None:
                    entry["compact_threshold"] = int(trigger["value"])
                result.append(entry)

        return result if result else None

    @staticmethod
    def translate_thinking_to_reasoning(
        thinking: dict[str, Any],
        output_config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Convert Anthropic thinking param to Responses API reasoning param.

        ``thinking.budget_tokens`` is bucketed via the shared
        ``reasoning_effort_from_thinking_budget`` thresholds. For adaptive
        thinking, uses ``output_config.effort`` if available, otherwise defaults
        to medium.
        """
        if not isinstance(thinking, dict):
            return None

        thinking_type: Final = thinking.get("type")

        if thinking_type == "adaptive":
            # Use output_config.effort if available
            effort = "medium"
            if isinstance(output_config, dict) and output_config.get("effort"):
                effort = output_config["effort"]
        elif thinking_type == "enabled":
            effort = reasoning_effort_from_thinking_budget(thinking.get("budget_tokens", 0))
        else:
            return None

        auto_summary: Final = is_reasoning_auto_summary_enabled()
        result: Final[dict[str, Any]] = {"effort": effort}
        summary: Final = thinking.get("summary")
        if summary:
            result["summary"] = summary
        elif auto_summary:
            result["summary"] = "detailed"
        return result

    def translate_request(
        self,
        anthropic_request: AnthropicMessagesRequest,
    ) -> dict[str, Any]:
        """
        Translate a full Anthropic /v1/messages request dict to
        litellm.responses() / litellm.aresponses() kwargs.
        """
        model: Final[str] = anthropic_request["model"]
        messages_list: Final = cast(
            list[AllAnthropicPassThroughMessageValues],
            anthropic_request["messages"],
        )

        input_items: Final = self.translate_messages_to_responses_input(messages_list)
        system: Final = anthropic_request.get("system")
        developer_parts: Final = (
            self._translate_midturn_system_content_to_responses(system)
            if isinstance(system, list)
            and any(isinstance(block, dict) and block.get("prompt_cache_breakpoint") is not None for block in system)
            else ()
        )
        if developer_parts:
            input_items.insert(
                0,
                {  # mutable-ok: API message payload
                    "type": "message",
                    "role": "developer",
                    "content": developer_parts,
                },
            )

        responses_kwargs: Final[dict[str, Any]] = {
            "model": model,
            "input": input_items,
        }

        if system and not developer_parts:
            if isinstance(system, str):
                responses_kwargs["instructions"] = system
            elif isinstance(system, list):
                responses_kwargs["instructions"] = "\n".join(
                    filter(None, (b.get("text", "") for b in system if isinstance(b, dict) and b.get("type") == "text"))
                )

        # max_tokens -> max_output_tokens
        max_tokens: Final = anthropic_request.get("max_tokens")
        if max_tokens:
            responses_kwargs["max_output_tokens"] = max_tokens

        # temperature / top_p passed through
        if "temperature" in anthropic_request:
            responses_kwargs["temperature"] = anthropic_request["temperature"]
        if "top_p" in anthropic_request:
            responses_kwargs["top_p"] = anthropic_request["top_p"]

        # tools
        tools: Final = anthropic_request.get("tools")
        translated_tools: Final[Sequence[Mapping[str, object]]] = (
            self.translate_tools_to_responses_api(cast(list[AllAnthropicToolsValues], tools)) if tools else ()
        )
        if translated_tools:
            responses_kwargs["tools"] = translated_tools

        # tool_choice
        tool_choice: Final = anthropic_request.get("tool_choice")
        if tool_choice and translated_tools:
            responses_kwargs["tool_choice"] = self.translate_tool_choice_to_responses_api(
                cast(AnthropicMessagesToolChoice, tool_choice),
                translated_tools=translated_tools,
            )

        # thinking -> reasoning
        thinking: Final = anthropic_request.get("thinking")
        if isinstance(thinking, dict):
            output_config = anthropic_request.get("output_config")
            reasoning: Final = self.translate_thinking_to_reasoning(
                thinking,
                output_config=cast(dict[str, Any] | None, output_config),
            )
            if reasoning:
                responses_kwargs["reasoning"] = reasoning

        # output_format / output_config.format -> text format
        # output_format: {"type": "json_schema", "schema": {...}}
        # output_config: {"format": {"type": "json_schema", "schema": {...}}}
        output_format: Any = anthropic_request.get("output_format")
        output_config = anthropic_request.get("output_config")
        if not isinstance(output_format, dict) and isinstance(output_config, dict):
            output_format = output_config.get("format")
        if isinstance(output_format, dict) and output_format.get("type") == "json_schema":
            schema: Final = output_format.get("schema")
            if schema:
                responses_kwargs["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": "structured_output",
                        "schema": schema,
                        "strict": True,
                    }
                }

        # context_management: Anthropic dict -> OpenAI array
        context_management: Final = anthropic_request.get("context_management")
        if isinstance(context_management, dict):
            openai_cm: Final = self.translate_context_management_to_responses_api(context_management)
            if openai_cm is not None:
                responses_kwargs["context_management"] = openai_cm

        # metadata user_id -> user and prompt_cache_key
        metadata: Final = anthropic_request.get("metadata")
        if isinstance(metadata, dict) and "user_id" in metadata:
            responses_kwargs["user"] = str(metadata["user_id"])[:64]
            prompt_cache_key: Final = prompt_cache_key_from_user_id(metadata["user_id"])
            if prompt_cache_key is not None:
                responses_kwargs["prompt_cache_key"] = prompt_cache_key

        return responses_kwargs

    # ------------------------------------------------------------------ #
    # Response translation: Responses API -> Anthropic                    #
    # ------------------------------------------------------------------ #

    def translate_response(
        self,
        response: ResponsesAPIResponse,
    ) -> AnthropicMessagesResponse:
        """
        Translate an OpenAI ResponsesAPIResponse to AnthropicMessagesResponse.
        """
        parsed = _parse_response_output(response.output)
        content = list(_fold_to_anthropic_blocks(parsed))
        stop_reason: AnthropicFinishReason = (
            "tool_use" if any(isinstance(item, _ToolUse) for item in parsed) else "end_turn"
        )

        # status -> stop_reason override
        if response.status == "incomplete":
            stop_reason = "max_tokens"

        anthropic_usage: Final = self.translate_responses_api_usage_to_anthropic_usage(response.usage)

        return AnthropicMessagesResponse(
            id=response.id,
            type="message",
            role="assistant",
            model=response.model or "unknown-model",
            stop_sequence=None,
            usage=anthropic_usage,
            content=content,
            stop_reason=stop_reason,
        )
