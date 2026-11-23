"""Short-lived local ChangeSet leases for EPE participants."""

from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from epe.adapters.storage import acquire_write_lock
from epe.core.json_codec import strict_json_loads
from epe.governance.baseline import changeset_paths


_OWNER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}\Z")
_LEASE_ID = re.compile(r"[0-9a-f-]{36}\Z")


class LeaseError(ValueError):
    pass


class LeaseConflict(LeaseError):
    pass


class LeaseNotFound(LeaseError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LeaseError("租约时间必须为 UTC RFC3339")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LeaseError("租约时间格式无效") from exc
    if parsed.tzinfo is None:
        raise LeaseError("租约时间缺少时区")
    return parsed.astimezone(timezone.utc)


def lease_path(root: Path, config: dict[str, Any], changeset_id: str) -> Path:
    change_path, _ = changeset_paths(root.resolve(), config, changeset_id)
    return change_path.with_name(change_path.stem + ".lease.json")


def _write_lock_path(root: Path, config: dict[str, Any]) -> Path:
    path = (root / config.get("storage", {}).get("derived", ".engineering") / ".write.lock").resolve()
    path.relative_to(root.resolve())
    return path


def _validate_owner(owner: Any) -> str:
    if not isinstance(owner, str) or not _OWNER.fullmatch(owner):
        raise LeaseError("租约 owner 格式非法")
    return owner


def _validate_lease_id(value: Any) -> str:
    if not isinstance(value, str) or not _LEASE_ID.fullmatch(value):
        raise LeaseError("lease_id 格式非法")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise LeaseError("lease_id 必须是规范 UUID") from exc
    if str(parsed) != value:
        raise LeaseError("lease_id 必须使用小写规范 UUID")
    return value


def _validate_ttl(ttl: Any) -> float:
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not math.isfinite(ttl) or ttl <= 0 or ttl > 7 * 24 * 3600:
        raise LeaseError("租约 TTL 必须为 0 到 7 天以内的有限正数")
    return float(ttl)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise LeaseError("租约记录不能是符号链接")
    try:
        value = strict_json_loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise LeaseError("租约记录不可读或 JSON 无效") from exc
    try:
        import jsonschema
        schema = strict_json_loads(files("epe.data.schemas").joinpath("lease.schema.json").read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(value))
    except (OSError, ValueError, ImportError) as exc:
        raise LeaseError("租约 Schema 不可用") from exc
    if errors:
        raise LeaseError("租约记录不符合 Schema: " + errors[0].message)
    required = {"schema_version", "changeset_id", "lease_id", "owner", "pid", "revision", "acquired_at", "expires_at"}
    if (not isinstance(value, dict) or set(value) != required or value.get("schema_version") != 1
            or not isinstance(value.get("changeset_id"), str) or not isinstance(value.get("lease_id"), str)
            or not _LEASE_ID.fullmatch(value["lease_id"])
            or not isinstance(value.get("pid"), int) or isinstance(value["pid"], bool) or value["pid"] < 1
            or not isinstance(value.get("revision"), int) or isinstance(value["revision"], bool) or value["revision"] < 1):
        raise LeaseError("租约记录结构无效")
    _validate_owner(value.get("owner"))
    acquired = _parse_timestamp(value.get("acquired_at"))
    expires = _parse_timestamp(value.get("expires_at"))
    if expires <= acquired:
        raise LeaseError("租约过期时间必须晚于获取时间")
    return value


def inspect_lease(root: Path, config: dict[str, Any], changeset_id: str) -> dict[str, Any] | None:
    path = lease_path(root, config, changeset_id)
    if not path.exists():
        return None
    value = _read(path)
    if value["changeset_id"] != changeset_id:
        raise LeaseError("租约记录与路径 ChangeSet ID 不匹配")
    value = dict(value)
    value["expired"] = _parse_timestamp(value["expires_at"]) <= _now()
    return value


def _persist_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def acquire_lease(root: Path, config: dict[str, Any], changeset: dict[str, Any], owner: str, ttl: Any) -> dict[str, Any]:
    owner = _validate_owner(owner)
    seconds = _validate_ttl(ttl)
    if changeset.get("status") != "active":
        raise LeaseError("只有 active ChangeSet 可以获取租约")
    if changeset.get("owner") != owner:
        raise LeaseError("租约 owner 必须匹配 ChangeSet owner")
    root = root.resolve()
    path = lease_path(root, config, changeset["id"])
    lock = _write_lock_path(root, config)
    with acquire_write_lock(lock):
        if path.exists() or path.is_symlink():
            current = _read(path)
            if current["changeset_id"] != changeset["id"]:
                raise LeaseError("租约记录与 ChangeSet ID 不匹配")
            if _parse_timestamp(current["expires_at"]) > _now():
                raise LeaseConflict("ChangeSet 已有未过期租约")
            path.unlink()
        start = _now()
        value = {"schema_version": 1, "changeset_id": changeset["id"], "lease_id": str(uuid.uuid4()),
                 "owner": owner, "pid": os.getpid(), "revision": changeset.get("revision", 1),
                 "acquired_at": _timestamp(start), "expires_at": _timestamp(start + timedelta(seconds=seconds))}
        try:
            _persist_exclusive(path, value)
        except FileExistsError as exc:
            raise LeaseConflict("ChangeSet 租约并发冲突") from exc
    return value


def renew_lease(root: Path, config: dict[str, Any], changeset: dict[str, Any], owner: str, lease_id: str, ttl: Any) -> dict[str, Any]:
    owner = _validate_owner(owner)
    seconds = _validate_ttl(ttl)
    _validate_lease_id(lease_id)
    path = lease_path(root.resolve(), config, changeset["id"])
    with acquire_write_lock(_write_lock_path(root.resolve(), config)):
        if not path.exists():
            raise LeaseNotFound("租约不存在")
        current = _read(path)
        if current["changeset_id"] != changeset["id"]:
            raise LeaseError("租约记录与 ChangeSet ID 不匹配")
        if current["lease_id"] != lease_id or current["owner"] != owner:
            raise LeaseConflict("租约身份不匹配")
        if current["revision"] != changeset.get("revision", 1):
            raise LeaseConflict("ChangeSet revision 已变化")
        if _parse_timestamp(current["expires_at"]) <= _now():
            raise LeaseConflict("租约已过期")
        current["expires_at"] = _timestamp(_now() + timedelta(seconds=seconds))
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("x", encoding="utf-8") as handle:
                json.dump(current, handle, ensure_ascii=False, sort_keys=True, indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            try: temp.unlink()
            except FileNotFoundError: pass
    return current


def release_lease(root: Path, config: dict[str, Any], changeset_id: str, owner: str, lease_id: str) -> bool:
    released, _ = release_lease_with_record(root, config, changeset_id, owner, lease_id)
    return released


def release_lease_with_record(root: Path, config: dict[str, Any], changeset_id: str, owner: str, lease_id: str) -> tuple[bool, dict[str, Any] | None]:
    owner = _validate_owner(owner)
    _validate_lease_id(lease_id)
    path = lease_path(root.resolve(), config, changeset_id)
    with acquire_write_lock(_write_lock_path(root.resolve(), config)):
        if not path.exists():
            return False, None
        current = _read(path)
        if current["changeset_id"] != changeset_id:
            raise LeaseError("租约记录与路径 ChangeSet ID 不匹配")
        if current["lease_id"] != lease_id or current["owner"] != owner:
            raise LeaseConflict("租约身份不匹配")
        path.unlink()
        return True, current
