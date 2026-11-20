from __future__ import annotations

from pathlib import Path
from typing import Any

from epe.core.diagnostics import Diagnostic, Severity
from epe.parsers.python import parse_python_tree


DEFAULT_ALLOWED = {
    "core": set(),
    "parsers": {"core"},
    "graph": {"core"},
    "design": {"core", "parsers"},
    "verification": {"core", "graph", "parsers"},
    "governance": {"core"},
    "context": {"core", "graph"},
    "adapters": {"core"},
    "cli": {"core", "parsers", "graph", "design", "verification", "governance", "context", "adapters"},
}


def validate_import_boundaries(root: Path, config: dict[str, Any], policy: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[Diagnostic]]:
    policy = policy or {}
    allowed = {key: set(value) for key, value in DEFAULT_ALLOWED.items()}
    configured = policy.get("allowed_imports", {})
    if isinstance(configured, dict):
        for module, dependencies in configured.items():
            if isinstance(module, str) and isinstance(dependencies, list) and all(isinstance(item, str) for item in dependencies):
                allowed[module] = set(dependencies)
    results, diagnostics = parse_python_tree(root, config.get("managed", {}).get("code_roots", ["src"]))
    violations: list[dict[str, Any]] = []
    facts = 0
    for result in results:
        parts = result.path.replace("\\", "/").split("/")
        if len(parts) < 3 or parts[0] != "src" or parts[1] != "epe": continue
        owner = parts[2].removesuffix(".py")
        if owner == "__init__" and len(parts) > 3: owner = parts[2]
        facts += len(result.imports)
        for import_fact in result.imports:
            module = import_fact.module.lstrip(".")
            if not module.startswith("epe."): continue
            dependency = module.split(".")[1]
            if dependency == owner or dependency in allowed.get(owner, set()): continue
            violations.append({"from": owner, "to": dependency, "path": result.path, "line": import_fact.line})
            diagnostics.append(Diagnostic("EPE-ARCH-IMPORT", Severity.ERROR, f"模块 {owner} 禁止依赖 {dependency}", path=result.path, line=import_fact.line))
    return {"status": "fail" if diagnostics else "pass", "checked_imports": facts, "violations": violations}, diagnostics
