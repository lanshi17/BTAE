from __future__ import annotations

from typing import Any
from fnmatch import fnmatch

from epe.core.diagnostics import Diagnostic, Severity
from epe.graph.builder import dependency_cycles


def validate_architecture(snapshot: dict[str, Any], policy: dict[str, Any] | None) -> tuple[dict[str, Any], list[Diagnostic]]:
    policy = policy or {}; ds: list[Diagnostic] = []; violations: list[dict[str, Any]] = []
    blind_spots = [d for d in snapshot.get("diagnostics", []) if d.get("code", "").startswith("EPE-AST-")]
    nodes = snapshot.get("nodes", [])
    coverage = snapshot.get("module_coverage", "unknown")
    if coverage in {"unconfigured", "unknown"} and any(n.get("kind") == "Module" for n in nodes) and any(n.get("kind") == "Source" for n in nodes):
        blind_spots.append({"code": "EPE-ARCH-MODULE-COVERAGE", "message": "模块归属未配置，模块依赖检查不完整"})
    if blind_spots:
        severity = Severity.ERROR if policy.get("unknown_is_blocking", True) else Severity.WARNING
        ds.append(Diagnostic("EPE-ARCH-UNKNOWN", severity, "静态依赖存在未解析盲区，不能证明架构完整"))
    cycles = dependency_cycles(snapshot)
    for cycle in cycles:
        evidence = [[edge for edge in snapshot.get("edges", []) if edge.get("relation") == "depends_on" and edge.get("from") == frm and edge.get("to") == to] for frm, to in zip(cycle, cycle[1:])]
        violations.append({"rule": "ARCH-CYCLE", "path": cycle, "edge_evidence": evidence})
        ds.append(Diagnostic("EPE-ARCH-CYCLE", Severity.ERROR, "发现依赖循环: " + " -> ".join(cycle)))
    forbidden = policy.get("forbidden_dependencies", []) or []
    reported = set()
    for edge in snapshot.get("edges", []):
        if edge.get("relation") != "depends_on": continue
        frm, to = edge.get("from", ""), edge.get("to", "")
        for rule in forbidden:
            if not isinstance(rule, dict): continue
            if fnmatch(frm, str(rule["from"])) and fnmatch(to, str(rule["to"])):
                key = (rule.get("id", "ARCH-FORBIDDEN"), frm, to)
                if key in reported: continue
                reported.add(key)
                violations.append({"rule": rule.get("id", "ARCH-FORBIDDEN"), "from": frm, "to": to})
                ds.append(Diagnostic("EPE-ARCH-FORBIDDEN", Severity.ERROR, f"禁止依赖: {frm} -> {to}"))
    status = "fail" if any(d.is_error for d in ds) else ("unknown" if blind_spots else "pass")
    return {"status": status, "cycles": cycles, "violations": violations, "unknowns": blind_spots,
            "module_coverage": coverage}, ds
