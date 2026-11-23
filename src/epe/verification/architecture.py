from __future__ import annotations

from typing import Any
from fnmatch import fnmatch

from epe.core.diagnostics import Diagnostic, Severity
from epe.graph.builder import dependency_cycles
from epe.core.fingerprint import sha256_json


def validate_architecture(snapshot: dict[str, Any], policy: dict[str, Any] | None,
                         valid_exceptions: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], list[Diagnostic]]:
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
    exceptions = valid_exceptions or []
    reported = set()
    for edge in snapshot.get("edges", []):
        if edge.get("relation") != "depends_on": continue
        frm, to = edge.get("from", ""), edge.get("to", "")
        for rule in forbidden:
            if not isinstance(rule, dict): continue
            if fnmatch(frm, str(rule["from"])) and fnmatch(to, str(rule["to"])):
                matched_exception = next((exception for exception in exceptions
                                          if exception.get("rule_id") == rule.get("id", "ARCH-FORBIDDEN")
                                          and fnmatch(frm, exception.get("from", ""))
                                          and fnmatch(to, exception.get("to", ""))), None)
                if matched_exception is not None:
                    continue
                key = (rule.get("id", "ARCH-FORBIDDEN"), frm, to)
                if key in reported: continue
                reported.add(key)
                violations.append({"rule": rule.get("id", "ARCH-FORBIDDEN"), "from": frm, "to": to})
                ds.append(Diagnostic("EPE-ARCH-FORBIDDEN", Severity.ERROR, f"禁止依赖: {frm} -> {to}"))
    status = "fail" if any(d.is_error for d in ds) else ("unknown" if blind_spots else "pass")
    return {"status": status, "cycles": cycles, "violations": violations, "unknowns": blind_spots,
            "module_coverage": coverage, "exceptions_applied": exceptions}, ds


def diff_architecture_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Compare two validated graph snapshots without interpreting authorization.

    The result is a discovery delta only. It does not decide whether a design
    or ADR should be changed, and it keeps source/provenance on each edge delta.
    """
    def node_key(node: dict[str, Any]) -> tuple[str, str]:
        return str(node.get("id", "")), str(node.get("kind", ""))

    def edge_key(edge: dict[str, Any]) -> str:
        return sha256_json(edge)

    previous_nodes = {node_key(node): node for node in previous.get("nodes", []) if isinstance(node, dict)}
    current_nodes = {node_key(node): node for node in current.get("nodes", []) if isinstance(node, dict)}
    previous_edges = {edge_key(edge): edge for edge in previous.get("edges", []) if isinstance(edge, dict)}
    current_edges = {edge_key(edge): edge for edge in current.get("edges", []) if isinstance(edge, dict)}
    added_nodes = [current_nodes[key] for key in sorted(current_nodes.keys() - previous_nodes.keys())]
    removed_nodes = [previous_nodes[key] for key in sorted(previous_nodes.keys() - current_nodes.keys())]
    added_edges = [current_edges[key] for key in sorted(current_edges.keys() - previous_edges.keys())]
    removed_edges = [previous_edges[key] for key in sorted(previous_edges.keys() - current_edges.keys())]
    previous_unknowns = [item for item in previous.get("diagnostics", []) if isinstance(item, dict)]
    current_unknowns = [item for item in current.get("diagnostics", []) if isinstance(item, dict)]
    incomplete = bool(previous_unknowns or current_unknowns or previous.get("complete") is not True or current.get("complete") is not True)
    return {
        "status": "changed" if added_nodes or removed_nodes or added_edges or removed_edges else "unchanged",
        "incomplete": incomplete,
        "previous_digest": previous.get("content_digest"),
        "current_digest": current.get("content_digest"),
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "unknowns": {"previous": previous_unknowns, "current": current_unknowns},
        "limitations": [
            "差异是发现架构事实，不自动表示设计违规、批准变化或 ADR 决策。",
            "删除/移动节点需要调用方结合历史实体身份和独立设计评审解释。",
        ],
    }
