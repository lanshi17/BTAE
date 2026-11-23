"""Conservative, declaration-only ChangeSet overlap analysis."""

from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath
from typing import Any, Iterable


_WILDCARD = re.compile(r"[*?[]")


def _literal_prefix(pattern: str) -> str:
    match = _WILDCARD.search(pattern)
    prefix = pattern if match is None else pattern[:match.start()]
    return prefix.rstrip("/")


def _may_overlap(left: str, right: str) -> bool:
    """Return a conservative potential-overlap fact for two relative globs."""
    if left == right or left in {"**", "*"} or right in {"**", "*"}:
        return True
    left_prefix, right_prefix = _literal_prefix(left), _literal_prefix(right)
    if left_prefix and right_prefix and not (
        left_prefix == right_prefix
        or left_prefix.startswith(right_prefix + "/")
        or right_prefix.startswith(left_prefix + "/")
    ):
        return False
    candidates = {left_prefix, right_prefix}
    for prefix in (left_prefix, right_prefix):
        if prefix:
            candidates.update({prefix + "/probe", prefix + "/probe.py", prefix + "/nested/probe.txt"})
    for candidate in candidates:
        if candidate and fnmatch.fnmatchcase(candidate, left) and fnmatch.fnmatchcase(candidate, right):
            return True
    # A wildcard suffix after a shared directory can match a deeper path even
    # when no finite probe above represents it (for example `src/**` vs
    # `src/*.py`). Keep the result conservative and label it as potential.
    return bool(left_prefix and right_prefix and (left_prefix == right_prefix))


def _patterns(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("ChangeSet 范围必须为数组")
    patterns = []
    for pattern in value:
        if (not isinstance(pattern, str) or not pattern or pattern.startswith("/")
                or "\\" in pattern or ".." in PurePosixPath(pattern).parts):
            raise ValueError("ChangeSet 范围包含非法路径")
        patterns.append(pattern)
    return sorted(set(patterns))


def detect_changeset_conflicts(changesets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return stable potential conflicts between planned/active declarations."""
    records = []
    for value in changesets:
        if not isinstance(value, dict) or value.get("status") not in {"planned", "active"}:
            continue
        records.append({
            "id": value.get("id", ""), "owner": value.get("owner", ""),
            "write_scope": _patterns(value.get("write_scope", [])),
            "protected": _patterns(value.get("protected", [])),
        })
    records.sort(key=lambda item: (str(item["id"]), str(item["owner"])))
    conflicts: list[dict[str, Any]] = []
    for index, left in enumerate(records):
        for right in records[index + 1:]:
            pairs = (
                ("write_scope", "write_scope", left["write_scope"], right["write_scope"]),
                ("write_scope", "protected", left["write_scope"], right["protected"]),
                ("protected", "write_scope", left["protected"], right["write_scope"]),
            )
            for left_field, right_field, left_patterns, right_patterns in pairs:
                for left_pattern in left_patterns:
                    for right_pattern in right_patterns:
                        if _may_overlap(left_pattern, right_pattern):
                            conflicts.append({
                                "left": {"id": left["id"], "owner": left["owner"], "field": left_field, "pattern": left_pattern},
                                "right": {"id": right["id"], "owner": right["owner"], "field": right_field, "pattern": right_pattern},
                                "conservative": True,
                            })
    return sorted(conflicts, key=lambda item: (
        item["left"]["id"], item["right"]["id"], item["left"]["field"],
        item["right"]["field"], item["left"]["pattern"], item["right"]["pattern"],
    ))
