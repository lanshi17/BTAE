from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from epe.core.diagnostics import Diagnostic, Severity


def finalize_gate(task: Any, design_ok: bool, mapping_ok: bool, architecture_ok: bool, evidences: list[dict], scope_ok: bool = True, required_checks: list[dict] | None = None) -> tuple[str, list[Diagnostic]]:
    ds: list[Diagnostic] = []
    if not design_ok: ds.append(Diagnostic("EPE-GATE-DESIGN", Severity.ERROR, "设计门禁未通过"))
    if not mapping_ok: ds.append(Diagnostic("EPE-GATE-MAPPING", Severity.ERROR, "映射门禁未通过"))
    if not architecture_ok: ds.append(Diagnostic("EPE-GATE-ARCH", Severity.ERROR, "架构门禁未通过"))
    if not scope_ok: ds.append(Diagnostic("EPE-GATE-SCOPE", Severity.ERROR, "实际修改超出 ChangeSet 范围"))
    if not required_checks:
        ds.append(Diagnostic("EPE-GATE-REQUIRED-CHECKS", Severity.ERROR, "未提供有效的必需检查策略"))
    for check in required_checks or []:
        check_id = check["id"]
        matching = [e for e in evidences if e.get("checker") == check_id
                    and e.get("command") == check["command"]
                    and e.get("checker_version") == str(check.get("version", "1"))
                    and e.get("task_id") == getattr(task, "id", None)
                    and e.get("changeset_id") == getattr(task, "changeset", None)]
        if not matching:
            ds.append(Diagnostic("EPE-GATE-EVIDENCE", Severity.ERROR, f"必需检查缺少当前有效证据: {check_id}"))
            continue
        try:
            ordered = []
            for record in matching:
                timestamp = record.get("finished_at")
                if not isinstance(timestamp, str):
                    raise ValueError("missing timestamp")
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError("timezone required")
                ordered.append((parsed.astimezone(timezone.utc), record))
            latest_time = max(time for time, _ in ordered)
            latest = [record for time, record in ordered if time == latest_time]
        except (ValueError, OverflowError):
            ds.append(Diagnostic("EPE-GATE-EVIDENCE-ORDER", Severity.ERROR, f"必需检查证据时间无效或不明确: {check_id}"))
            continue
        if any(e.get("validity") != "valid" or e.get("result") != "passed" or (check.get("kind") == "test" and
               (check.get("result_parser") != "pytest" or not isinstance(e.get("provenance"), dict)
                or e["provenance"].get("test_protocol") != "pytest-junit-v1")) for e in latest):
            ds.append(Diagnostic("EPE-GATE-TEST", Severity.ERROR, f"必需检查最新证据未通过或顺序不明确: {check_id}"))
    return ("passed" if not ds else "blocked"), ds
