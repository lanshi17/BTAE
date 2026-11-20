from __future__ import annotations

import json
import math
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from epe.core.diagnostics import Diagnostic, Severity


def default_config() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project_id": "PROJ-BTAE",
        "managed": {"design_roots": ["docs"], "code_roots": ["src"], "test_roots": ["tests"], "contract_roots": ["engineering/contracts"]},
        "exclude": [".git", ".engineering", "reports", ".venv", "venv", "__pycache__"],
        "policies": {"architecture": "engineering/policies/architecture.yaml", "verification": "engineering/policies/verification.yaml"},
        "storage": {"derived": ".engineering", "tasks": "engineering/tasks", "changesets": "engineering/changesets", "approvals": "engineering/approvals", "evidence": "engineering/evidence", "audit": "engineering/audit/events.jsonl"},
    }


class Repository:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @property
    def config_path(self) -> Path:
        return self.root / "engineering" / "epe.yaml"

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def safe_path(self, rel: str) -> Path:
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts or "\\" in rel:
            raise ValueError(f"路径必须是仓库相对路径: {rel}")
        candidate = (self.root / rel).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"路径越界: {rel}") from exc
        return candidate

    def read_bytes(self, relative_path: str) -> bytes:
        candidate = self.safe_path(relative_path)
        raw = self.root / relative_path
        if raw.is_symlink():
            raise ValueError(f"不读取符号链接: {relative_path}")
        if not candidate.is_file():
            raise FileNotFoundError(relative_path)
        data = candidate.read_bytes()
        if not candidate.resolve().is_relative_to(self.root):
            raise ValueError(f"读取期间路径越界: {relative_path}")
        return data

    def exists(self, relative_path: str) -> bool:
        try:
            candidate = self.safe_path(relative_path)
            return candidate.exists() and not (self.root / relative_path).is_symlink()
        except ValueError:
            return False

    def load_yaml(self, path: Path) -> tuple[Any | None, list[Diagnostic]]:
        from epe.parsers.documents import parse_yaml_bytes
        return parse_yaml_bytes(path.read_bytes(), self.rel(path))

    def load_json(self, path: Path) -> tuple[Any | None, list[Diagnostic]]:
        try:
            return json.loads(path.read_text(encoding="utf-8")), []
        except (OSError, json.JSONDecodeError) as exc:
            return None, [Diagnostic("EPE-JSON-PARSE", Severity.ERROR, str(exc), path=self.rel(path))]


def load_config(root: Path) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    repo = Repository(root)
    path = repo.config_path
    if not path.exists():
        return None, [Diagnostic("EPE-CONFIG-MISSING", Severity.ERROR, "工程尚未初始化，请运行 epe init", path="engineering/epe.yaml")]
    try:
        path.resolve().relative_to(repo.root)
    except ValueError:
        return None, [Diagnostic("EPE-PATH-SYMLINK", Severity.ERROR, "配置符号链接解析后逃出仓库根", path="engineering/epe.yaml")]
    try:
        value, ds = repo.load_yaml(path)
    except (OSError, ValueError) as exc:
        return None, [Diagnostic("EPE-CONFIG-READ", Severity.ERROR, str(exc), path="engineering/epe.yaml")]
    if value is None:
        return None, ds or [Diagnostic("EPE-CONFIG-TYPE", Severity.ERROR, "配置顶层必须为对象", path="engineering/epe.yaml")]
    if not isinstance(value, dict):
        return None, [Diagnostic("EPE-CONFIG-TYPE", Severity.ERROR, "配置顶层必须为对象", path="engineering/epe.yaml")]
    def json_value(item: Any, active: set[int]) -> bool:
        if item is None or isinstance(item, (str, bool, int)):
            return True
        if isinstance(item, float):
            return math.isfinite(item)
        if isinstance(item, (dict, list)):
            if id(item) in active: return False
            active.add(id(item))
            valid = (all(isinstance(k, str) and json_value(v, active) for k, v in item.items())
                     if isinstance(item, dict) else all(json_value(v, active) for v in item))
            active.remove(id(item))
            return valid
        return False
    if not json_value(value, set()):
        return None, [Diagnostic("EPE-CONFIG-INVALID", Severity.ERROR, "配置必须为无递归、字符串键且有限数值的 JSON 数据", path="engineering/epe.yaml")]
    try:
        import jsonschema
        schema = json.loads(files("epe.data.schemas").joinpath("project-config.schema.json").read_text(encoding="utf-8"))
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(value), key=lambda error: (tuple(str(p) for p in error.absolute_path), error.message))
    except (ImportError, OSError, ValueError) as exc:
        return None, [Diagnostic("EPE-CONFIG-SCHEMA", Severity.ERROR, f"配置 Schema 不可用: {exc}", path="engineering/epe.yaml")]
    if errors:
        return None, [Diagnostic("EPE-CONFIG-INVALID", Severity.ERROR, f"配置字段 {'.'.join(str(p) for p in error.absolute_path) or '<root>'}: {error.message}", path="engineering/epe.yaml") for error in errors]
    managed = value.get("managed", {})
    paths = [p for key in ("design_roots", "code_roots", "test_roots", "contract_roots") for p in managed.get(key, [])]
    paths += [p for group in managed.get("module_roots", {}).values() for p in group]
    paths += list(value.get("policies", {}).values()) + list(value.get("storage", {}).values())
    for relative in paths:
        if relative.startswith("/") or "\\" in relative or any(part in {"", ".", ".."} for part in relative.split("/")):
            return None, [Diagnostic("EPE-CONFIG-PATH", Severity.ERROR, f"配置路径必须是规范仓库相对路径: {relative}", path="engineering/epe.yaml")]
        try:
            (repo.root / relative).resolve().relative_to(repo.root)
        except (OSError, RuntimeError, ValueError):
            return None, [Diagnostic("EPE-CONFIG-PATH", Severity.ERROR, f"配置路径解析后逃出仓库或无法解析: {relative}", path="engineering/epe.yaml")]
    return value, ds
