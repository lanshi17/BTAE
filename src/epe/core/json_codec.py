"""Strict JSON decoding for authority-bearing project records."""

from __future__ import annotations

import json
from typing import Any


class DuplicateJSONKeyError(ValueError):
    """Raised when an object contains the same key more than once."""


class NonStandardJSONConstantError(ValueError):
    """Raised for JavaScript-style NaN and Infinity tokens outside JSON."""


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise NonStandardJSONConstantError(f"non-standard JSON numeric constant: {value}")


def strict_json_loads(text: str) -> Any:
    """Decode JSON while rejecting duplicate keys and non-standard numbers."""
    if not isinstance(text, str):
        raise TypeError("JSON input must be text")
    return json.loads(text, object_pairs_hook=_object_from_pairs, parse_constant=_reject_constant)
