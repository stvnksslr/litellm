"""Anthropic tool search (``defer_loading`` + ``tool_reference``) emulated for OpenAI-shaped backends."""

import json
from collections.abc import Iterator, Mapping, Sequence
from typing import Final, cast

from litellm.types.llms.anthropic import ANTHROPIC_HOSTED_TOOLS
from litellm.types.llms.openai import ChatCompletionToolParam

ToolCatalog = Mapping[str, ChatCompletionToolParam]


def _mapping_items(content: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(content, list):
        return ()
    return tuple(
        cast(Mapping[str, object], item)  # cast-ok: untrusted client payload
        for item in cast(Sequence[object], content)  # cast-ok: untrusted client payload
        if isinstance(item, Mapping)
    )


def reference_names(tool_result_content: object) -> tuple[str, ...]:
    return tuple(
        str(item["tool_name"])
        for item in _mapping_items(tool_result_content)
        if item.get("type") == "tool_reference" and isinstance(item.get("tool_name"), str)
    )


def _tool_result_blocks(message: Mapping[str, object]) -> Iterator[Mapping[str, object]]:
    yield from (block for block in _mapping_items(message.get("content")) if block.get("type") == "tool_result")


def referenced_tool_names(messages: Sequence[Mapping[str, object]]) -> frozenset[str]:
    return frozenset(
        name
        for message in messages
        for block in _tool_result_blocks(message)
        for name in reference_names(block.get("content"))
    )


def uses_server_side_tool_search(tools: Sequence[Mapping[str, object]]) -> bool:
    return any(str(tool.get("type") or "").startswith(ANTHROPIC_HOSTED_TOOLS.TOOL_SEARCH_TOOL.value) for tool in tools)


def forwards_tool(tool: Mapping[str, object], referenced: frozenset[str], server_side_search: bool) -> bool:
    """A deferred tool reaches the backend once a tool_reference names it, or when the client relies on the
    server-side search tool, which the bridge cannot run, so every tool must load upfront instead."""
    if not tool.get("defer_loading"):
        return True
    return server_side_search or str(tool.get("name")) in referenced


def tool_catalog(tools: Sequence[ChatCompletionToolParam], truncated_to_original: Mapping[str, str]) -> ToolCatalog:
    functions: Final = tuple(tool for tool in tools if tool.get("type") == "function")
    return {truncated_to_original.get(tool["function"]["name"], tool["function"]["name"]): tool for tool in functions}


def _function_line(tool: ChatCompletionToolParam) -> str:
    function: Final = tool["function"]
    parameters: Final[Mapping[str, object]] = (
        cast(Mapping[str, object], function["parameters"]) if "parameters" in function else {}  # cast-ok: json schema
    )
    definition: Final[dict[str, object]] = {
        "description": function["description"] if "description" in function else "",
        "name": function["name"],
        "parameters": parameters,
    }
    return f"<function>{json.dumps(definition)}</function>"


def expand_tool_references(names: Sequence[str], catalog: ToolCatalog) -> str | None:
    """The ``<functions>`` block Claude Code's ToolSearch description promises, one line per resolvable reference."""
    lines: Final = tuple(_function_line(catalog[name]) for name in names if name in catalog)
    if not lines:
        return None
    return "<functions>\n" + "\n".join(lines) + "\n</functions>"
