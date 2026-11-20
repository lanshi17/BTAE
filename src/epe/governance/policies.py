from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from epe.core.diagnostics import Diagnostic, Severity
from epe.parsers.documents import parse_yaml_bytes
from epe.core.policy import validate_policy_document


def validate_policy_files(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    results: list[dict[str, Any]] = []
    try:
        import jsonschema
    except ImportError:
        return {}, [Diagnostic("EPE-POLICY-UNSUPPORTED", Severity.ERROR, "未安装 jsonschema，不能执行策略 Schema 校验")]
    schema_dir = root / "engineering/schemas"
    if not schema_dir.exists():
        package_schema_dir = Path(__file__).resolve().parents[3] / "engineering/schemas"
        if package_schema_dir.exists(): schema_dir = package_schema_dir
    def load_schema(name: str) -> dict[str, Any] | None:
        schema_path = schema_dir / name
        try: return json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            try: return json.loads(files("epe.data.schemas").joinpath(name).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, ModuleNotFoundError):
                diagnostics.append(Diagnostic("EPE-POLICY-SCHEMA", Severity.ERROR, f"无法读取 Schema: {name}", path=str(schema_path)))
                return None
    mapping = {
        "architecture": (config.get("policies", {}).get("architecture", "engineering/policies/architecture.yaml"), "policy.schema.json"),
        "verification": (config.get("policies", {}).get("verification", "engineering/policies/verification.yaml"), "policy.schema.json"),
    }
    for kind, (relative, schema_name) in mapping.items():
        path = (root / relative).resolve()
        try:
            if path.is_symlink(): raise ValueError("策略文件不能是符号链接")
            path.relative_to(root.resolve()); raw, parse_diagnostics = parse_yaml_bytes(path.read_bytes(), str(relative))
        except (OSError, ValueError) as exc:
            diagnostics.append(Diagnostic("EPE-POLICY-READ", Severity.ERROR, str(exc), path=str(relative))); continue
        diagnostics.extend(parse_diagnostics)
        schema = load_schema(schema_name)
        if schema is None or not isinstance(raw, dict):
            if not isinstance(raw, dict): diagnostics.append(Diagnostic("EPE-POLICY-TYPE", Severity.ERROR, f"{kind} 策略必须为对象", path=str(relative)))
            continue
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(raw), key=lambda error: list(error.path))
        for error in errors:
            location = ".".join(str(item) for item in error.path)
            diagnostics.append(Diagnostic("EPE-POLICY-INVALID", Severity.ERROR, f"{kind} 策略无效{('.' + location) if location else ''}: {error.message}", path=str(relative)))
        if kind == "verification":
            checks = raw.get("checks")
            if checks is not None and not isinstance(checks, list):
                diagnostics.append(Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, "checks 必须为数组", path=str(relative)))
            elif isinstance(checks, list):
                seen: set[str] = set()
                for check in checks:
                    if not isinstance(check, dict): continue
                    check_id = check.get("id")
                    if not isinstance(check_id, str) or not check_id.strip() or check_id in seen:
                        diagnostics.append(Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"检查 ID 缺失或重复: {check_id}", path=str(relative)))
                    else: seen.add(check_id)
                    command = check.get("command")
                    if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
                        diagnostics.append(Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"检查命令必须为非空参数数组: {check_id}", path=str(relative)))
                    try:
                        timeout = float(check.get("timeout", 300))
                        if not 0 < timeout < float("inf"): raise ValueError
                    except (ValueError, TypeError):
                        diagnostics.append(Diagnostic("EPE-VERIFY-CONFIG", Severity.ERROR, f"检查超时无效: {check_id}", path=str(relative)))
        results.append({"kind": kind, "path": str(relative), "valid": not any(d.path == str(relative) and d.is_error for d in diagnostics)})
    workflow_schema = load_schema("workflow.schema.json")
    workflows = root / "engineering/workflows"
    if workflows.exists():
        for path in sorted(workflows.glob("*.yaml")):
            relative = str(path.relative_to(root))
            try:
                if path.is_symlink(): raise ValueError("Workflow 文件不能是符号链接")
                raw, parse_diagnostics = parse_yaml_bytes(path.read_bytes(), relative)
            except (OSError, ValueError) as exc:
                diagnostics.append(Diagnostic("EPE-WORKFLOW-READ", Severity.ERROR, str(exc), path=relative)); continue
            diagnostics.extend(parse_diagnostics)
            errors = [] if workflow_schema is None else sorted(jsonschema.Draft202012Validator(workflow_schema).iter_errors(raw), key=lambda error: list(error.path))
            for error in errors:
                location = ".".join(str(item) for item in error.path)
                diagnostics.append(Diagnostic("EPE-WORKFLOW-INVALID", Severity.ERROR, f"Workflow 无效{('.' + location) if location else ''}: {error.message}", path=relative))
            results.append({"kind": "workflow", "path": relative, "valid": not errors and not parse_diagnostics})
    return {"policies": results, "valid": not any(d.is_error for d in diagnostics)}, diagnostics
