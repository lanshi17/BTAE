from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable

from epe.core.diagnostics import Diagnostic, Severity
from epe.core.fingerprint import sha256_bytes, sha256_json
from epe.parsers.documents import DocumentParseResult, parse_markdown, parse_yaml_bytes
from epe.parsers.python import CodeParseResult, parse_python


@dataclass(frozen=True)
class ParseBatch:
    """Deterministic aggregate of parser facts; incomplete batches are never publishable."""

    results: tuple[Any, ...]
    diagnostics: tuple[Diagnostic, ...]
    input_manifest: dict[str, Any]
    counts: dict[str, int]
    complete: bool

    def to_dict(self) -> dict[str, Any]:
        values = []
        for result in self.results:
            values.append(result.to_dict() if hasattr(result, "to_dict") else result)
        return {
            "schema_version": 1,
            "results": values,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "input_manifest": self.input_manifest,
            "counts": dict(self.counts),
            "complete": self.complete,
        }


def _source_parts(source: Any) -> tuple[str, bytes]:
    if isinstance(source, dict):
        path, data = source.get("path"), source.get("data", source.get("bytes"))
    else:
        try:
            path, data = source
        except (TypeError, ValueError) as exc:
            raise ValueError("输入必须是 (relative_path, bytes) 或对象") from exc
    if not isinstance(path, str) or not path or not isinstance(data, bytes):
        raise ValueError("输入路径必须为字符串，内容必须为 bytes")
    normalized = PurePosixPath(path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts or str(normalized) != path.replace("\\", "/"):
        raise ValueError(f"输入路径必须是规范仓库相对路径: {path}")
    return normalized.as_posix(), data


def parse_batch(sources: Iterable[Any], options: dict[str, Any] | None = None) -> ParseBatch:
    options = dict(options or {})
    parse_python_enabled = options.get("python", True)
    results: list[Any] = []
    diagnostics: list[Diagnostic] = []
    entries: list[dict[str, str]] = []
    counts = {"success": 0, "failed": 0, "excluded": 0, "unsupported": 0}
    seen: set[str] = set()
    for source in sources:
        try:
            path, data = _source_parts(source)
        except ValueError as exc:
            diagnostics.append(Diagnostic("EPE-PARSE-SOURCE", Severity.ERROR, str(exc)))
            counts["failed"] += 1
            continue
        if path in seen:
            diagnostics.append(Diagnostic("EPE-PARSE-DUPLICATE", Severity.ERROR, f"输入路径重复: {path}", path=path))
            counts["failed"] += 1
            continue
        seen.add(path)
        digest = sha256_bytes(data)
        entries.append({"path": path, "sha256": digest})
        suffix = PurePosixPath(path).suffix.lower()
        if suffix in {".md", ".markdown"}:
            result = parse_markdown(data, path)
            results.append(result)
            diagnostics.extend(result.diagnostics)
            if result.diagnostics:
                counts["failed"] += 1
            else:
                counts["success"] += 1
        elif suffix in {".yaml", ".yml", ".json"}:
            value, ds = parse_yaml_bytes(data, path)
            results.append({"path": path, "source": path, "digest": digest, "value": value, "diagnostics": [d.to_dict() for d in ds], "kind": "structured"})
            diagnostics.extend(ds)
            if ds:
                counts["failed"] += 1
            else:
                counts["success"] += 1
        elif suffix == ".py" and parse_python_enabled:
            result = parse_python(data, path)
            results.append(result)
            diagnostics.extend(result.diagnostics)
            diagnostics.extend(result.gaps)
            if result.diagnostics:
                counts["failed"] += 1
            else:
                counts["success"] += 1
        elif suffix == ".py":
            counts["excluded"] += 1
        else:
            diagnostics.append(Diagnostic("EPE-PARSE-UNSUPPORTED", Severity.WARNING, f"不支持的输入类型: {suffix or '<none>'}", path=path))
            counts["unsupported"] += 1
    entries.sort(key=lambda item: item["path"])
    manifest = {"entries": entries, "digest": sha256_json(entries)}
    results.sort(key=lambda result: result.path if hasattr(result, "path") else result["path"])
    complete = counts["failed"] == 0 and counts["unsupported"] == 0 and not any(item.is_error for item in diagnostics)
    return ParseBatch(tuple(results), tuple(diagnostics), manifest, counts, complete)
