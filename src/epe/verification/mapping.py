from __future__ import annotations

from typing import Iterable

from epe.core.diagnostics import Diagnostic, Severity
from epe.core.registry import Registry
from epe.parsers.python import CodeParseResult


def validate_mapping(registry: Registry, code_results: Iterable[CodeParseResult]) -> tuple[dict, list[Diagnostic]]:
    by_path = {r.path: r for r in code_results}
    symbols = {(r.path, s.qualified_name) for r in code_results for s in r.symbols}
    ds: list[Diagnostic] = []; checked = 0
    for entity in registry.entities.values():
        if entity.implementation_status != "implemented": continue
        checked += 1
        for mapping in entity.implementation:
            if not isinstance(mapping, dict) or not mapping.get("path"):
                ds.append(Diagnostic("EPE-MAPPING-FORMAT", Severity.ERROR, "implementation 映射缺少 path", entity_id=entity.id, path=entity.source.path)); continue
            path, symbol = str(mapping["path"]), mapping.get("symbol")
            if path not in by_path:
                ds.append(Diagnostic("EPE-MAPPING-PATH", Severity.ERROR, f"实现文件不存在或未纳管: {path}", entity_id=entity.id, path=path)); continue
            if symbol and (path, str(symbol)) not in symbols:
                ds.append(Diagnostic("EPE-MAPPING-SYMBOL", Severity.ERROR, f"实现符号不存在: {path}:{symbol}", entity_id=entity.id, path=path)); continue
    return {"checked": checked, "symbols": len(symbols), "complete": not any(d.is_error for d in ds)}, ds
