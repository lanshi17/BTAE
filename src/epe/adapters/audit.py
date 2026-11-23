from __future__ import annotations

import fcntl
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from epe.core.fingerprint import sha256_json
from epe.core.json_codec import strict_json_loads
from epe.core.ports import ClockPort
from epe.adapters.clock import SystemClock


_EVENT_TYPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _json_value(value: Any, active: set[int] | None = None) -> bool:
    active = active if active is not None else set()
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, (dict, list)):
        if id(value) in active:
            return False
        active.add(id(value))
        valid = (all(isinstance(key, str) and _json_value(item, active) for key, item in value.items())
                 if isinstance(value, dict) else all(_json_value(item, active) for item in value))
        active.remove(id(value))
        return valid
    return False


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value or value.endswith(" "):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0
    except (TypeError, ValueError):
        return False


def _now(clock: ClockPort | None = None) -> str:
    return (clock or SystemClock()).now_utc()


def _verify_bytes(data: bytes) -> tuple[bool, str | None, int, str]:
    previous = "0" * 64
    if data and not data.endswith(b"\n"):
        return False, "审计链末行不完整", 0, previous
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return False, "审计链不是 UTF-8", 0, previous
    for index, line in enumerate(lines, 1):
        try:
            event = strict_json_loads(line)
        except (json.JSONDecodeError, ValueError):
            return False, f"第 {index} 行不是 JSON", index - 1, previous
        required = {"schema_version", "sequence", "timestamp", "event_type", "payload", "previous_hash", "hash"}
        if (not isinstance(event, dict) or set(event) != required or event.get("schema_version") != 1
                or isinstance(event.get("sequence"), bool) or not isinstance(event.get("sequence"), int) or event.get("sequence") < 1
                or not _valid_timestamp(event.get("timestamp")) or not isinstance(event.get("event_type"), str) or not _EVENT_TYPE.fullmatch(event.get("event_type", ""))
                or not isinstance(event.get("payload"), dict) or not _json_value(event.get("payload"))
                or not isinstance(event.get("previous_hash"), str) or not _SHA256.fullmatch(event.get("previous_hash", ""))
                or not isinstance(event.get("hash"), str) or not _SHA256.fullmatch(event.get("hash", ""))):
            return False, f"第 {index} 行字段结构无效", index - 1, previous
        if event.get("sequence") != index or event.get("previous_hash") != previous:
            return False, f"第 {index} 行序列或前置摘要断裂", index - 1, previous
        actual = event.get("hash"); content = {k: v for k, v in event.items() if k != "hash"}
        if not isinstance(actual, str) or len(actual) != 64 or actual != sha256_json(content):
            return False, f"第 {index} 行摘要不匹配", index - 1, previous
        previous = actual
    return True, None, len(lines), previous


def _read_fd(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def append_audit(path: Path, event_type: str, payload: dict[str, Any], clock: ClockPort | None = None) -> dict[str, Any]:
    if (not isinstance(event_type, str) or not _EVENT_TYPE.fullmatch(event_type)
            or not isinstance(payload, dict) or not _json_value(payload)):
        raise ValueError("审计事件类型或载荷无效")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        valid, error, count, previous_hash = _verify_bytes(_read_fd(fd))
        if not valid:
            raise ValueError(f"现有审计链无效: {error}")
        event = {"schema_version": 1, "sequence": count + 1, "timestamp": _now(clock), "event_type": event_type, "payload": payload, "previous_hash": previous_hash}
        event["hash"] = sha256_json(event)
        encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        view = memoryview(encoded)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("审计追加未完成")
            view = view[written:]
        os.fsync(fd)
        return event
    finally:
        os.close(fd)


def verify_audit(path: Path) -> tuple[bool, str | None, int]:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return True, None, 0
    except OSError as exc:
        return False, str(exc), 0
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        valid, error, count, _ = _verify_bytes(_read_fd(fd))
        return valid, error, count
    except OSError as exc:
        return False, str(exc), 0
    finally:
        os.close(fd)


def read_audit_events(path: Path) -> list[dict[str, Any]]:
    """Read a single verified audit snapshot under the same shared lock."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return []
    try:
        fcntl.flock(fd, fcntl.LOCK_SH)
        data = _read_fd(fd)
        valid, error, _, _ = _verify_bytes(data)
        if not valid:
            raise ValueError(f"现有审计链无效: {error}")
        return [strict_json_loads(line) for line in data.decode("utf-8").splitlines()]
    finally:
        os.close(fd)
