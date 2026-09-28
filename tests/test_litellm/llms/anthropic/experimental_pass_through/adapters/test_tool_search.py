import json
from typing import Final

from litellm.llms.anthropic.experimental_pass_through.adapters.tool_search import (
    expand_tool_references,
    forwards_tool,
    reference_names,
    referenced_tool_names,
    tool_catalog,
    uses_server_side_tool_search,
)

WEATHER: Final = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Weather at a location",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
    },
}
LONG_NAME: Final = "mcp__plugin_atlassian_pb-atlassian__jira_get_issue_development_info"
LONG_TRUNCATED: Final = LONG_NAME[:64]
JIRA: Final = {"type": "function", "function": {"name": LONG_TRUNCATED, "parameters": {"type": "object"}}}


def _reference(name: str) -> dict:
    return {"type": "tool_reference", "tool_name": name}


def _tool_result_turn(*blocks: dict) -> dict:
    return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": list(blocks)}]}


class TestReferenceScan:
    def test_reference_names_keeps_order_and_ignores_other_parts(self) -> None:
        content = [{"type": "text", "text": "loaded"}, _reference("b"), _reference("a"), {"type": "tool_reference"}]

        assert reference_names(content) == ("b", "a")

    def test_reference_names_of_string_content_is_empty(self) -> None:
        assert reference_names("plain text") == ()

    def test_referenced_tool_names_scans_every_tool_result_in_the_conversation(self) -> None:
        messages = [
            {"role": "user", "content": "hi"},
            _tool_result_turn(_reference("get_weather")),
            {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
            _tool_result_turn(_reference("search_files"), {"type": "text", "text": "Tool loaded."}),
            {"role": "user", "content": [{"type": "text", "text": "tool_reference mentioned in prose only"}]},
        ]

        assert referenced_tool_names(messages) == frozenset({"get_weather", "search_files"})


class TestForwarding:
    def test_non_deferred_tools_always_forward(self) -> None:
        assert forwards_tool({"name": "Bash"}, frozenset(), server_side_search=False)
        assert forwards_tool({"name": "Bash", "defer_loading": False}, frozenset(), server_side_search=False)

    def test_deferred_tool_forwards_only_once_referenced(self) -> None:
        tool = {"name": "DeferredToolPlaceholder", "defer_loading": True}

        assert not forwards_tool(tool, frozenset(), server_side_search=False)
        assert forwards_tool(tool, frozenset({"DeferredToolPlaceholder"}), server_side_search=False)

    def test_server_side_search_loads_every_deferred_tool_upfront(self) -> None:
        tools = [{"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"}, {"name": "x"}]

        assert uses_server_side_tool_search(tools)
        assert not uses_server_side_tool_search([{"name": "ToolSearch"}, {"type": "web_search_20250305", "name": "w"}])
        assert forwards_tool({"name": "x", "defer_loading": True}, frozenset(), server_side_search=True)


class TestExpansion:
    def test_catalog_is_keyed_by_the_original_name_but_renders_the_truncated_one(self) -> None:
        catalog = tool_catalog([WEATHER, JIRA, {"type": "web_search_options"}], {LONG_TRUNCATED: LONG_NAME})

        assert set(catalog) == {"get_weather", LONG_NAME}
        assert catalog[LONG_NAME]["function"]["name"] == LONG_TRUNCATED

    def test_expansion_is_one_function_line_per_resolvable_reference(self) -> None:
        catalog = tool_catalog([WEATHER, JIRA], {LONG_TRUNCATED: LONG_NAME})

        text = expand_tool_references(("get_weather", "unknown", LONG_NAME), catalog)

        assert text is not None
        lines = text.split("\n")
        assert lines[0] == "<functions>" and lines[-1] == "</functions>"
        rendered = [json.loads(line.removeprefix("<function>").removesuffix("</function>")) for line in lines[1:-1]]
        assert rendered == [
            {
                "description": "Weather at a location",
                "name": "get_weather",
                "parameters": WEATHER["function"]["parameters"],
            },
            {"description": "", "name": LONG_TRUNCATED, "parameters": {"type": "object"}},
        ]

    def test_nothing_resolvable_expands_to_none(self) -> None:
        assert expand_tool_references(("unknown",), tool_catalog([WEATHER], {})) is None
        assert expand_tool_references((), tool_catalog([WEATHER], {})) is None
