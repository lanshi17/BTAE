from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from .models import InputManifest


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def _excluded(rel: str, excludes: tuple[str, ...]) -> bool:
    parts = Path(rel).parts
    return any(p in parts for p in excludes) or any(p.endswith(".egg-info") for p in parts) or rel.startswith(".engineering/") or rel.startswith("reports/")


def build_manifest(root: Path, include_roots: Iterable[str] | None = None,
                   excludes: tuple[str, ...] = (".git", ".venv", "venv", "__pycache__")) -> InputManifest:
    root = root.resolve()
    roots = [root / x for x in include_roots] if include_roots else [root]
    excludes = tuple(set(excludes) | {".git", ".engineering", "reports", ".venv", "venv", "__pycache__"})
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for base in roots:
        if not base.exists():
            continue
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
        for path in files:
            try:
                rel = path.resolve().relative_to(root).as_posix()
            except ValueError as exc:
                raise ValueError(f"纳管路径解析后逃出仓库根: {path}") from exc
            if rel in seen or _excluded(rel, excludes):
                continue
            seen.add(rel)
            digest = sha256_bytes(path.read_bytes())
            entries.append((rel, digest))
    entries.sort()
    return InputManifest(tuple(entries), sha256_json([{"path": p, "sha256": h} for p, h in entries]))
