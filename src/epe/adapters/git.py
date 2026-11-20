from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _run(root: Path, *args: str) -> tuple[str | None, bool]:
    try:
        process = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None, False
    return (process.stdout, process.returncode == 0)


def git_provenance(root: Path) -> dict[str, Any]:
    commit_output, commit_ok = _run(root, "rev-parse", "HEAD")
    status_output, status_ok = _run(root, "status", "--porcelain=v1", "-z")
    if not commit_ok and not status_ok:
        return {"commit": None, "dirty": False, "git_available": False, "status": [], "untracked": [], "renames": []}
    raw_status = status_output or ""
    records = [record for record in raw_status.split("\0") if record]
    status = []
    untracked = []
    renames = []
    for record in records:
        code, _, path = record[:2], record[2:3], record[3:]
        item = {"code": code, "path": path}
        status.append(item)
        if code == "??":
            untracked.append(path)
        if "R" in code:
            renames.append(path)
    return {"commit": commit_output.strip() if commit_ok and commit_output else None,
            "dirty": bool(records), "git_available": commit_ok or status_ok,
            "status": status, "untracked": sorted(untracked), "renames": sorted(renames)}
