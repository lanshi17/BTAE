from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .diagnostics import Diagnostic, Severity


@dataclass
class TransitionResult:
    accepted: bool
    value: dict[str, Any]
    diagnostics: list[Diagnostic]


DESIGN_EVENTS = {"submit_review": ("draft", "reviewed"), "approve": ("reviewed", "approved"), "reject": ("reviewed", "draft"), "revoke": ("approved", "draft")}
IMPLEMENTATION_EVENTS = {"start": ("not_started", "in_progress"), "complete": ("in_progress", "implemented"), "rework": ("implemented", "in_progress")}


def transition(value: dict[str, Any], dimension: str, event: str, expected_revision: int | None = None) -> TransitionResult:
    """Apply one explicit lifecycle event without mutating the caller's object."""
    current = dict(value)
    if expected_revision is not None and current.get("revision", 1) != expected_revision:
        return TransitionResult(False, current, [Diagnostic("EPE-REVISION-CONFLICT", Severity.ERROR, "状态 revision 已变化")])
    field, events = {"design": ("design_status", DESIGN_EVENTS), "implementation": ("implementation_status", IMPLEMENTATION_EVENTS)}.get(dimension, ("", {}))
    if not field:
        return TransitionResult(False, current, [Diagnostic("EPE-STATE-DIMENSION", Severity.ERROR, f"未知状态维度: {dimension}")])
    pair = events.get(event)
    if pair is None or current.get(field) != pair[0]:
        return TransitionResult(False, current, [Diagnostic("EPE-STATE-TRANSITION", Severity.ERROR, f"非法状态迁移: {current.get(field)} --{event}--> ?")])
    current[field] = pair[1]
    current["revision"] = int(current.get("revision", 1)) + 1
    return TransitionResult(True, current, [])
