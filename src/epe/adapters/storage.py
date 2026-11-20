from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass


class WriteConflict(RuntimeError):
    pass


class acquire_write_lock:
    def __init__(self, path: Path): self.path = path; self.fd: int | None = None
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try: self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc: raise WriteConflict(f"写入冲突: {self.path}") from exc
        os.write(self.fd, str(os.getpid()).encode())
        return self
    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None: os.close(self.fd)
        try: self.path.unlink()
        except FileNotFoundError: pass
