from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

from epe.adapters.storage import atomic_write_json
from epe.core.diagnostics import Diagnostic, Severity
from epe.core.models import Task


def validate_task(data: dict[str, Any]) -> tuple[Task | None, list[Diagnostic]]:
    ds: list[Diagnostic] = []
    if not isinstance(data, dict):
        return None, [Diagnostic("EPE-TASK-TYPE", Severity.ERROR, "任务必须为对象")]
    allowed = {"schema_version", "id", "type", "objective", "acceptance", "risk", "target_entities", "changeset", "status", "revision", "baseline_manifest", "reproduction", "hypothesis"}
    unknown = sorted(set(data) - allowed, key=lambda item: (type(item).__name__, repr(item)))
    for key in unknown:
        ds.append(Diagnostic("EPE-TASK-UNKNOWN-FIELD", Severity.ERROR, f"未知任务字段: {key}"))
    required = {"id", "type", "objective", "acceptance", "risk", "target_entities"}
    for key in sorted(required - set(data)):
        ds.append(Diagnostic("EPE-TASK-REQUIRED", Severity.ERROR, f"任务缺少字段: {key}"))
    if data.get("schema_version", 1) != 1:
        ds.append(Diagnostic("EPE-TASK-SCHEMA", Severity.ERROR, "任务 schema_version 必须为 1"))
    revision = data.get("revision", 1)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        ds.append(Diagnostic("EPE-TASK-REVISION", Severity.ERROR, "任务 revision 必须为正整数"))
    if "id" in data and not re.fullmatch(r"TASK-[A-Z0-9][A-Z0-9_-]*", str(data["id"])):
        ds.append(Diagnostic("EPE-TASK-ID", Severity.ERROR, f"任务 ID 非法: {data['id']}"))
    if data.get("changeset") is not None and (not isinstance(data.get("changeset"), str) or not re.fullmatch(r"CHANGE-[A-Z0-9][A-Z0-9_-]*", data["changeset"])):
        ds.append(Diagnostic("EPE-TASK-CHANGESET", Severity.ERROR, "ChangeSet ID 格式非法"))
    if not isinstance(data.get("type"), str) or data.get("type") not in {"feature", "bugfix", "refactor", "exploration"}:
        ds.append(Diagnostic("EPE-TASK-TYPE", Severity.ERROR, f"任务类型非法: {data.get('type')}"))
    if not isinstance(data.get("risk"), str) or data.get("risk") not in {"low", "medium", "high"}:
        ds.append(Diagnostic("EPE-TASK-RISK", Severity.ERROR, f"风险等级非法: {data.get('risk')}"))
    if not isinstance(data.get("status", "planned"), str) or data.get("status", "planned") not in {"planned", "active", "completed", "aborted"}:
        ds.append(Diagnostic("EPE-TASK-STATUS", Severity.ERROR, f"任务状态非法: {data.get('status')}"))
    if not isinstance(data.get("objective"), str) or not data.get("objective", "").strip():
        ds.append(Diagnostic("EPE-TASK-OBJECTIVE", Severity.ERROR, "objective 必须为非空字符串"))
    if not isinstance(data.get("acceptance"), list) or not data.get("acceptance") or not all(isinstance(item, str) and item for item in data.get("acceptance", [])):
        ds.append(Diagnostic("EPE-TASK-ACCEPTANCE", Severity.ERROR, "acceptance 必须为非空字符串数组"))
    if not isinstance(data.get("target_entities"), list) or not data.get("target_entities") or not all(isinstance(item, str) and item for item in data.get("target_entities", [])):
        ds.append(Diagnostic("EPE-TASK-TARGET", Severity.ERROR, "target_entities 必须为非空字符串数组"))
    for field in ("baseline_manifest", "reproduction", "hypothesis"):
        if field in data and (not isinstance(data[field], str) or not data[field].strip()):
            ds.append(Diagnostic("EPE-TASK-WORKFLOW", Severity.ERROR, f"{field} 必须为非空字符串"))
    if ds:
        return None, ds
    return Task(str(data["id"]), str(data["type"]), str(data["objective"]), list(data["acceptance"]), str(data["risk"]), list(data["target_entities"]), data.get("changeset"), data.get("status", "planned"), revision, dict(data)), []


def task_path(root: Path, config: dict[str, Any], task_id: str) -> Path:
    return root / config.get("storage", {}).get("tasks", "engineering/tasks") / f"{task_id}.json"


def save_task(root: Path, config: dict[str, Any], task: Task) -> None:
    atomic_write_json(task_path(root, config, task.id), task.to_dict())


def create_task(root: Path, config: dict[str, Any], task: Task) -> None:
    """Create a task with exclusive file creation; never replace authority."""
    path = task_path(root, config, task.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(task.to_dict(), handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        import os
        os.fsync(handle.fileno())


def load_task(root: Path, config: dict[str, Any], task_id: str) -> tuple[Task | None, list[Diagnostic]]:
    if not re.fullmatch(r"TASK-[A-Z0-9][A-Z0-9_-]*", task_id):
        return None, [Diagnostic("EPE-TASK-ID", Severity.ERROR, "任务 ID 格式非法", entity_id=task_id)]
    path = task_path(root, config, task_id)
    if not path.exists(): return None, [Diagnostic("EPE-TASK-MISSING", Severity.ERROR, f"任务不存在: {task_id}", entity_id=task_id, path=str(path.relative_to(root)))]
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: return None, [Diagnostic("EPE-TASK-READ", Severity.ERROR, str(exc), path=str(path.relative_to(root)))]
    return validate_task(data)


def check_scope(actual: list[str], write_scope: list[str], protected: list[str]) -> tuple[bool, list[str]]:
    def matches(path: str, pattern: str) -> bool:
        from fnmatch import fnmatch
        return fnmatch(path, pattern) or path == pattern or path.startswith(pattern.rstrip("/") + "/")
    violations = [p for p in actual if any(matches(p, q) for q in protected) or not any(matches(p, q) for q in write_scope)]
    return not violations, violations


def transition_task(task: Task, event: str, gate_status: str | None = None, expected_revision: int | None = None,
                    required_fields: Sequence[str] | None = None) -> tuple[Task | None, list[Diagnostic]]:
    """Validate task workflow transitions without changing the stored object."""
    diagnostics: list[Diagnostic] = []
    if expected_revision is not None and task.revision != expected_revision:
        return None, [Diagnostic("EPE-TASK-REVISION", Severity.ERROR, f"任务 revision 冲突，当前为 {task.revision}")]
    required_by_type = {
        "feature": ("objective", "acceptance", "target_entities"),
        "bugfix": ("objective", "acceptance", "target_entities", "reproduction"),
        "refactor": ("objective", "acceptance", "target_entities", "baseline_manifest"),
        "exploration": ("objective", "acceptance", "target_entities", "hypothesis"),
    }
    if event == "activate":
        if task.status != "planned": diagnostics.append(Diagnostic("EPE-TASK-TRANSITION", Severity.ERROR, f"只能从 planned 激活任务: {task.status}"))
        fields = tuple(required_fields) if required_fields is not None else required_by_type.get(task.type, ())
        special_codes = {
            "baseline_manifest": ("EPE-TASK-BASELINE", "refactor 激活需要 baseline_manifest"),
            "reproduction": ("EPE-TASK-REPRODUCTION", "bugfix 激活需要 reproduction"),
            "hypothesis": ("EPE-TASK-HYPOTHESIS", "exploration 激活需要 hypothesis"),
        }
        for field in fields:
            if task.raw.get(field):
                continue
            code, message = special_codes.get(field, ("EPE-TASK-WORKFLOW", f"{task.type} 激活需要 {field}"))
            diagnostics.append(Diagnostic(code, Severity.ERROR, message))
        new_status = "active"
    elif event == "complete":
        if task.status != "active": diagnostics.append(Diagnostic("EPE-TASK-TRANSITION", Severity.ERROR, f"只能从 active 完成任务: {task.status}"))
        if gate_status != "passed": diagnostics.append(Diagnostic("EPE-TASK-GATE", Severity.ERROR, "完成任务需要明确的 passed 门禁事实"))
        new_status = "completed"
    elif event == "abort":
        if task.status not in {"planned", "active"}: diagnostics.append(Diagnostic("EPE-TASK-TRANSITION", Severity.ERROR, f"不能从当前状态中止任务: {task.status}"))
        new_status = "aborted"
    else:
        return None, [Diagnostic("EPE-TASK-EVENT", Severity.ERROR, f"未知任务事件: {event}")]
    if diagnostics: return None, diagnostics
    raw = dict(task.raw); raw["status"] = new_status; raw["revision"] = task.revision + 1
    return Task(task.id, task.type, task.objective, list(task.acceptance), task.risk, list(task.target_entities), task.changeset, new_status, task.revision + 1, raw), []
