import copy
from typing import Final

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from litellm.llms.anthropic.experimental_pass_through.adapters.tool_schema import drop_uncompilable_patterns

ARTIFACT_FIELD_PATTERN: Final = r'^(?!__.*__$)[^\p{Cc}\p{Cf}\p{Zl}\p{Zp}"\\./[\]]{1,200}$'
ARTIFACT_COLLECTION_PATTERN: Final = (
    r"^(?!\.\.?(?:\/|$))[A-Za-z0-9_\-.~:@+]{1,200}(?:\/(?!\.\.?(?:\/|$))[A-Za-z0-9_\-.~:@+]{1,200}){0,14}$"
)


def _check_schema(schema: dict) -> None:
    Draft202012Validator.check_schema(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _artifact_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field": {"type": "string", "pattern": ARTIFACT_FIELD_PATTERN},
            "asset_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"},
            "collection": {"type": "string", "pattern": ARTIFACT_COLLECTION_PATTERN},
        },
    }


class TestArtifactSchema:
    def test_the_recorded_field_pattern_is_what_vllm_rejects(self) -> None:
        with pytest.raises(SchemaError, match="is not a 'regex'"):
            _check_schema(_artifact_schema())

    def test_only_the_uncompilable_pattern_is_dropped_and_the_schema_then_validates(self) -> None:
        sanitized = drop_uncompilable_patterns(_artifact_schema())

        _check_schema(sanitized)
        assert sanitized["properties"]["field"] == {"type": "string"}
        assert sanitized["properties"]["asset_id"]["pattern"] == "^[0-9a-f]{32}$"
        assert sanitized["properties"]["collection"]["pattern"] == ARTIFACT_COLLECTION_PATTERN
        assert sanitized["additionalProperties"] is False

    def test_input_schema_is_not_mutated(self) -> None:
        schema = _artifact_schema()
        before = copy.deepcopy(schema)

        drop_uncompilable_patterns(schema)

        assert schema == before


class TestWalker:
    def test_patterns_nested_under_combinators_items_and_defs_are_dropped(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"anyOf": [{"type": "string", "pattern": r"\p{L}+"}, {"type": "null"}]},
                },
                "id": {"$ref": "#/$defs/ident"},
            },
            "$defs": {"ident": {"type": "string", "pattern": r"^\p{Lu}", "minLength": 1}},
        }

        sanitized = drop_uncompilable_patterns(schema)

        assert sanitized["properties"]["rows"]["items"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
        assert sanitized["$defs"]["ident"] == {"type": "string", "minLength": 1}
        _check_schema(sanitized)

    def test_pattern_properties_keep_compilable_keys_only(self) -> None:
        schema = {
            "type": "object",
            "patternProperties": {r"^\p{L}": {"type": "string"}, "^x-": {"type": "integer", "pattern": r"\d+"}},
        }

        sanitized = drop_uncompilable_patterns(schema)

        assert sanitized["patternProperties"] == {"^x-": {"type": "integer", "pattern": r"\d+"}}

    def test_a_property_named_pattern_is_a_name_not_a_regex(self) -> None:
        grep_like = {
            "type": "object",
            "properties": {"pattern": {"type": "string", "description": "regex to search for"}},
            "required": ["pattern"],
        }

        assert drop_uncompilable_patterns(grep_like) == grep_like

    def test_a_defs_entry_named_pattern_is_a_name_not_a_regex(self) -> None:
        schema = {"$defs": {"pattern": {"type": "string", "pattern": r"\p{L}"}}}

        assert drop_uncompilable_patterns(schema) == {"$defs": {"pattern": {"type": "string"}}}

    def test_non_string_pattern_values_are_left_alone(self) -> None:
        schema = {"type": "object", "properties": {"x": {"pattern": 42}}}

        assert drop_uncompilable_patterns(schema) == schema
