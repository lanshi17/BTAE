"""ChangeSet baseline snapshots. Files are authority; no Git status inference."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from epe.core.fingerprint import sha256_json
from epe.governance.tasks import check_scope


_IGNORED_NAMES = {".git", ".engineering", ".venv", "venv", "__pycache__", ".pytest_cache"}
_ID = re.compile(r"CHANGE-[A-Z0-9][A-Z0-9_-]*")


def changeset_paths(root: Path, config: dict[str, Any], changeset_id: str) -> tuple[Path, Path]:
    if not _ID.fullmatch(changeset_id):
        raise ValueError("ChangeSet ID 格式非法")
    base = (root / config.get("storage", {}).get("changesets", "engineering/changesets")).resolve()
    base.relative_to(root.resolve())
    return base / f"{changeset_id}.json", base / f"{changeset_id}.baseline.json"


def changeset_declaration(changeset: dict[str, Any]) -> dict[str, Any]:
    """Return immutable declaration fields; lifecycle status/revision are mutable."""
    return {key: value for key, value in changeset.items() if key not in {"baseline_manifest", "status", "revision"}}


def _audit_exclusions(root: Path, config: dict[str, Any], changeset_id: str) -> set[str]:
    change, baseline = changeset_paths(root, config, changeset_id)
    paths = {change.relative_to(root).as_posix(), baseline.relative_to(root).as_posix(), "reports"}
    evidence = (root / config.get("storage", {}).get("evidence", "engineering/evidence")).resolve()
    paths.add(evidence.relative_to(root.resolve()).as_posix())
    return paths


def capture_baseline(root: Path, config: dict[str, Any], changeset_id: str) -> dict[str, Any]:
    root = root.resolve()
    excluded = _audit_exclusions(root, config, changeset_id)
    entries: list[dict[str, str]] = []

    def scan(directory: Path) -> None:
        for path in sorted(directory.iterdir(), key=lambda p: p.name):
            rel = path.relative_to(root).as_posix()
            if path.name in _IGNORED_NAMES or path.name.endswith(".egg-info") or any(rel == item or rel.startswith(item + "/") for item in excluded):
                continue
            if path.is_symlink():
                target = path.resolve(strict=True)
                target.relative_to(root)
                if target.is_dir():
                    raise ValueError(f"不支持目录符号链接: {rel}")
                link_target = os.readlink(path).encode("utf-8")
                digest = hashlib.sha256(b"symlink\0" + link_target + b"\0" + target.read_bytes()).hexdigest()
                entries.append({"path": rel, "sha256": digest, "kind": "symlink"})
            elif path.is_dir():
                scan(path)
            elif path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                entries.append({"path": rel, "sha256": digest, "kind": "file"})
            else:
                raise ValueError(f"不支持的文件类型: {rel}")

    scan(root)
    entries.sort(key=lambda item: item["path"])
    return {"schema_version": 1, "entries": entries, "digest": sha256_json(entries)}


def _validated_baseline(root: Path, config: dict[str, Any], changeset: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    _, baseline_path = changeset_paths(root.resolve(), config, changeset["id"])
    if baseline_path.is_symlink():
        raise ValueError("基线记录不能是符号链接")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    entries = baseline.get("entries") if isinstance(baseline, dict) else None
    if (not isinstance(entries, list) or set(baseline) != {"schema_version", "entries", "digest"} or baseline.get("schema_version") != 1
            or not all(isinstance(e, dict) and set(e) == {"path", "sha256", "kind"}
                       and isinstance(e["path"], str) and e["path"] and not e["path"].startswith("/")
                       and ".." not in PurePosixPath(e["path"]).parts
                       and isinstance(e["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", e["sha256"])
                       and e["kind"] in {"file", "symlink"} for e in entries)):
        raise ValueError("基线结构无效")
    paths = [e["path"] for e in entries]
    expected = sha256_json({"entries": entries, "changeset": changeset_declaration(changeset)})
    legacy_declaration = {k: v for k, v in changeset.items() if k != "baseline_manifest"}
    legacy = sha256_json({"entries": entries, "changeset": legacy_declaration})
    stored = baseline.get("digest")
    if paths != sorted(set(paths)) or stored != changeset.get("baseline_manifest") or stored not in {expected, legacy}:
        raise ValueError("基线摘要不匹配或路径重复")
    return entries, "current" if stored == expected else "legacy"


def baseline_binding_version(root: Path, config: dict[str, Any], changeset: dict[str, Any]) -> str:
    return _validated_baseline(root, config, changeset)[1]


def compare_baseline(root: Path, config: dict[str, Any], changeset: dict[str, Any]) -> list[str]:
    entries, _ = _validated_baseline(root, config, changeset)
    current = capture_baseline(root, config, changeset["id"])
    old = {item["path"]: (item["sha256"], item["kind"]) for item in entries}
    new = {item["path"]: (item["sha256"], item["kind"]) for item in current["entries"]}
    return sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))


def validate_changeset(changeset: dict[str, Any], task_id: str) -> None:
    revision = changeset.get("revision", 1) if isinstance(changeset, dict) else None
    if (not isinstance(changeset, dict) or changeset.get("schema_version", 1) != 1 or not isinstance(changeset.get("id"), str) or not _ID.fullmatch(changeset["id"])
            or isinstance(revision, bool) or not isinstance(revision, int) or revision < 1
            or changeset.get("task") != task_id or not isinstance(changeset.get("owner"), str) or not changeset["owner"].strip()
            or not isinstance(changeset.get("affected_entities"), list) or not changeset["affected_entities"]
            or not all(isinstance(item, str) and item for item in changeset["affected_entities"])
            or not isinstance(changeset.get("dependencies"), list)
            or changeset.get("status") not in {"planned", "active", "completed", "aborted"}):
        raise ValueError("ChangeSet 缺少有效的 ID、任务、负责人、实体、依赖或状态")
    for field in ("write_scope", "protected"):
        patterns = changeset.get(field)
        if not isinstance(patterns, list) or (field == "write_scope" and not patterns):
            raise ValueError(f"{field} 必须是范围数组")
        if any(not isinstance(p, str) or not p or p.startswith("/") or ".." in PurePosixPath(p).parts or "\\" in p for p in patterns):
            raise ValueError(f"{field} 包含非法路径")


def transition_changeset(changeset: dict[str, Any], event: str, expected_revision: int | None = None, scope_ok: bool = True) -> tuple[dict[str, Any] | None, list[str]]:
    """Pure ChangeSet lifecycle transition; caller owns persistence and diagnostics."""
    if not isinstance(changeset, dict):
        return None, ["ChangeSet 必须为对象"]
    revision = changeset.get("revision", 1)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        return None, ["ChangeSet revision 必须为正整数"]
    if expected_revision is not None and revision != expected_revision:
        return None, [f"ChangeSet revision 冲突，当前为 {revision}"]
    current = changeset.get("status")
    transitions = {"activate": {"planned": "active"}, "complete": {"active": "completed"}, "abort": {"planned": "aborted", "active": "aborted"}}
    target = transitions.get(event, {}).get(current)
    if target is None:
        return None, [f"非法 ChangeSet 状态迁移: {current} --{event}--> ?"]
    if event == "complete" and not scope_ok:
        return None, ["ChangeSet 实际改动超出声明范围，不能完成"]
    updated = dict(changeset)
    updated["status"] = target
    updated["revision"] = revision + 1
    return updated, []
