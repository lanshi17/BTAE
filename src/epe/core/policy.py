from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostic, Severity


def validate_policy_document(root: Path, raw: Any, kind: str, path: str) -> list[Diagnostic]:
    """Validate a policy document without depending on governance consumers."""
    try:
        import jsonschema
        schema_path = root / "engineering/schemas/policy.schema.json"
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            schema = json.loads(files("epe.data.schemas").joinpath("policy.schema.json").read_text(encoding="utf-8"))
    except (ImportError, OSError, json.JSONDecodeError) as exc:
        return [Diagnostic("EPE-POLICY-SCHEMA", Severity.ERROR, f"策略 Schema 不可用: {exc}", path=path)]
    if not isinstance(raw, dict):
        return [Diagnostic("EPE-POLICY-TYPE", Severity.ERROR, f"{kind} 策略必须为对象", path=path)]
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(raw), key=lambda error: (tuple(str(p) for p in error.path), error.message))
    diagnostics: list[Diagnostic] = []
    for error in errors:
        location = ".".join(str(item) for item in error.path)
        diagnostics.append(Diagnostic("EPE-POLICY-INVALID", Severity.ERROR, f"{kind} 策略无效{('.' + location) if location else ''}: {error.message}", path=path))
    return diagnostics
