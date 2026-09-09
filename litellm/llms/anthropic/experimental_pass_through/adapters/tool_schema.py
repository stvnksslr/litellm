"""Tool parameter schemas rewritten so OpenAI-compatible backends accept them."""

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Final, cast

_NAMED_CHILDREN: Final = frozenset({"properties", "$defs", "definitions"})


def _compiles(pattern: str) -> bool:
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


def _sanitized_children(named: Mapping[str, object], keep: frozenset[str] | None = None) -> dict[str, object]:
    return {name: _sanitize(child) for name, child in named.items() if keep is None or name in keep}


def _sanitized_items(schema: Mapping[str, object]) -> Iterator[tuple[str, object]]:
    for key, value in schema.items():
        if key == "pattern" and isinstance(value, str) and not _compiles(value):
            continue
        if key == "patternProperties" and isinstance(value, Mapping):
            named = cast(Mapping[str, object], value)  # cast-ok: json schema node
            yield key, _sanitized_children(named, frozenset(name for name in named if _compiles(name)))
            continue
        if key in _NAMED_CHILDREN and isinstance(value, Mapping):
            yield key, _sanitized_children(cast(Mapping[str, object], value))  # cast-ok: json schema node
            continue
        yield key, _sanitize(value)


def _sanitize(node: object) -> object:
    if isinstance(node, Mapping):
        return dict(_sanitized_items(cast(Mapping[str, object], node)))  # cast-ok: json schema node
    if isinstance(node, Sequence) and not isinstance(node, str | bytes):
        return [_sanitize(item) for item in cast(Sequence[object], node)]  # cast-ok: json schema list
    return node


def drop_uncompilable_patterns(schema: Mapping[str, object]) -> dict[str, object]:
    """Return a copy of ``schema`` without ``pattern`` regexes Python's ``re`` rejects.

    vLLM validates every tool schema against the JSON Schema 2020-12 metaschema with format checking, and
    ``format: regex`` there is ``re.compile``. Claude Code 2.1.266's Artifact tool ships an ECMAScript-only
    ``\\p{..}`` pattern, so the whole request 400s until it is dropped. See fork-patches.md
    """
    return dict(_sanitized_items(schema))
