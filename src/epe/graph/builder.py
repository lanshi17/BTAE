from __future__ import annotations

import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any, Iterable

from epe.adapters.storage import atomic_write_json, acquire_write_lock, WriteConflict
from epe.core.diagnostics import Diagnostic, Severity
from epe.core.fingerprint import sha256_json, build_manifest
from epe.core.models import Relation
from epe.core.registry import Registry
from epe.parsers.python import CodeParseResult, SymbolRecord, ImportFact, parse_python, parse_python_tree


@dataclass
class GraphBuildResult:
    snapshot: dict[str, Any] | None
    diagnostics: list[Diagnostic]
    published: bool


def _source_node(path: str) -> str:
    return f"SRC-{path}"


def graph_manifest(root: Path, config: dict[str, Any]):
    managed = config.get("managed", {})
    roots = (managed.get("design_roots", []) + managed.get("code_roots", [])
             + managed.get("test_roots", []) + managed.get("contract_roots", [])
             + ["engineering/epe.yaml"])
    return build_manifest(root, roots, tuple(config.get("exclude", [])))


def _module_names(code_results: list[CodeParseResult], roots: list[str]) -> tuple[dict[str, list[str]], set[str]]:
    modules: dict[str, list[str]] = {}
    for result in code_results:
        parts = result.path.replace("\\", "/").split("/")
        for root in roots:
            root_parts = root.strip("/").split("/")
            if parts[:len(root_parts)] != root_parts: continue
            rel = parts[len(root_parts):]
            if not rel: continue
            if rel[-1] == "__init__.py": rel = rel[:-1]
            elif rel[-1].endswith(".py"): rel[-1] = rel[-1][:-3]
            module = ".".join(x for x in rel if x)
            if module: modules.setdefault(module, []).append(result.path)
    return modules, set(modules)


def _resolve_import(result: CodeParseResult, imp, modules: dict[str, list[str]], module_names: set[str], roots: list[str]) -> tuple[str | None, str | None]:
    current = result.path.replace("\\", "/").split("/")
    root = next((r for r in roots if current[:len(r.strip("/").split("/"))] == r.strip("/").split("/")), None)
    if root is None: return None, "代码文件不属于任何纳管包根"
    root_parts = root.strip("/").split("/"); rel = current[len(root_parts):]
    package = rel[:-1] if rel and rel[-1].endswith(".py") else rel
    if package and package[-1] == "__init__.py": package = package[:-1]
    if imp.level:
        if imp.level > len(package) + 1: return None, "相对导入层级超出包根"
        base = package[:len(package) - imp.level + 1]
        base_name = ".".join(base)
        absolute = ".".join(x for x in [base_name, imp.module.lstrip(".")] if x)
    else:
        absolute = imp.module
    candidates: list[str] = []
    if imp.kind == "from" and imp.names:
        for name in imp.names:
            candidate = f"{absolute}.{name}" if absolute else name
            if candidate in module_names: candidates.append(candidate)
    if absolute in module_names: candidates.append(absolute)
    candidates = sorted(set(candidates))
    if len(candidates) == 1 and len(modules[candidates[0]]) == 1: return candidates[0], None
    if len(candidates) > 1 or (candidates and len(modules[candidates[0]]) > 1): return None, "导入目标存在多个静态候选"
    return None, (f"无法解析纳管内部导入: {absolute}" if absolute and any(m == absolute or m.startswith(absolute + ".") for m in module_names) else None)


def _aggregate_module_dependencies(registry: Registry, code_results: list[CodeParseResult], edges: list[dict[str, Any]], module_roots: Any) -> tuple[list[dict[str, Any]], list[Diagnostic], str]:
    if module_roots is None:
        return [], [], "unconfigured"
    diagnostics: list[Diagnostic] = []
    if not isinstance(module_roots, dict) or not module_roots:
        return [], [Diagnostic("EPE-MODULE-CONFIG", Severity.ERROR, "module_roots 必须为非空模块目录映射")], "invalid"
    roots: list[tuple[str, str]] = []
    for module, paths in module_roots.items():
        if not isinstance(module, str) or not registry.get(module) or registry.get(module).type != "Module" or not isinstance(paths, list) or not paths:
            diagnostics.append(Diagnostic("EPE-MODULE-CONFIG", Severity.ERROR, f"模块归属配置非法: {module}")); continue
        for path in paths:
            if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")) or str(PurePosixPath(path)) != path:
                diagnostics.append(Diagnostic("EPE-MODULE-CONFIG", Severity.ERROR, f"模块目录非法: {path}")); continue
            roots.append((module, path))
    if diagnostics: return [], diagnostics, "invalid"
    owners: dict[str, str] = {}
    for fact in code_results:
        matches = {module for module, path in roots if fact.path == path or fact.path.startswith(path + "/")}
        if len(matches) > 1:
            diagnostics.append(Diagnostic("EPE-MODULE-AMBIGUOUS", Severity.ERROR, f"文件属于多个模块: {fact.path}", path=fact.path))
        elif not matches:
            diagnostics.append(Diagnostic("EPE-AST-MODULE-UNASSIGNED", Severity.WARNING, "文件未指定模块归属", path=fact.path))
        else:
            owners[_source_node(fact.path)] = next(iter(matches))
    if any(d.is_error for d in diagnostics): return [], diagnostics, "invalid"
    aggregated = []
    for edge in edges:
        if edge.get("relation") != "depends_on": continue
        source, target = edge.get("from"), edge.get("to")
        if source not in owners or target not in owners or owners[source] == owners[target]: continue
        origin = edge.get("origin", {})
        if not isinstance(origin, dict) or origin.get("type") != "static": continue
        module_origin = {**origin, "from_source": source, "to_source": target}
        aggregated.append({"from": owners[source], "to": owners[target], "relation": "depends_on",
                           "origin": module_origin, "confidence": edge.get("confidence", 0), "verified": False})
    return aggregated, diagnostics, "partial" if diagnostics else "configured"


def build_graph(root: Path, registry: Registry, code_results: Iterable[CodeParseResult], config: dict[str, Any]) -> GraphBuildResult:
    diagnostics: list[Diagnostic] = []
    if registry is None:
        return GraphBuildResult(None, [Diagnostic("EPE-GRAPH-REGISTRY", Severity.ERROR, "注册快照不可用")], False)
    nodes: list[dict[str, Any]] = []
    edges = [r.to_dict() for r in registry.relations]
    for entity in registry.entities.values():
        nodes.append({"id": entity.id, "kind": entity.type, "source": entity.source.to_dict()})
        for impl in entity.implementation:
            if isinstance(impl, dict) and impl.get("path"):
                path = str(impl["path"])
                sid = str(impl.get("symbol") or _source_node(path))
                if impl.get("symbol"):
                    sid = f"SYM-{path}:{sid}"
                nodes.append({"id": sid, "kind": "Symbol" if impl.get("symbol") else "Source", "source": {"path": path, "symbol": impl.get("symbol")}})
                edges.append({"from": entity.id, "to": sid, "relation": "realizes", "origin": {"type": "explicit", "source": entity.source.path}, "confidence": 1.0, "verified": False})
    symbol_by_path: dict[str, list[dict[str, Any]]] = {}
    code_results = sorted(code_results, key=lambda item: item.path)
    import_targets: dict[str, str] = {}
    managed_roots = list(config.get("managed", {}).get("code_roots", ["src"]))
    module_paths, module_names = _module_names(code_results, managed_roots)
    for result in code_results:
        rel = result.path.replace("\\", "/")
        parts = rel.split("/")
        if parts and parts[0] in set(config.get("managed", {}).get("code_roots", ["src"])):
            module_parts = parts[1:]
            if module_parts and module_parts[-1] == "__init__.py": module_parts = module_parts[:-1]
            elif module_parts and module_parts[-1].endswith(".py"): module_parts[-1] = module_parts[-1][:-3]
            if module_parts: import_targets[".".join(module_parts)] = _source_node(result.path)
    for result in code_results:
        source_id = _source_node(result.path)
        if not any(n["id"] == source_id for n in nodes):
            nodes.append({"id": source_id, "kind": "Source", "source": {"path": result.path}})
        for sym in result.symbols:
            sid = f"SYM-{result.path}:{sym.qualified_name}"
            symbol_by_path.setdefault(result.path, []).append({"id": sid, "kind": "Symbol", "source": {"path": result.path, "symbol": sym.qualified_name}})
            if not any(n["id"] == sid for n in nodes): nodes.append(symbol_by_path[result.path][-1])
        diagnostics.extend(result.diagnostics)
        diagnostics.extend(result.gaps)
        for imp in result.imports:
            if imp.dynamic:
                continue
            module, unknown = _resolve_import(result, imp, module_paths, module_names, managed_roots)
            if module:
                target_paths = module_paths[module]
                target = _source_node(target_paths[0])
                edges.append({"from": source_id, "to": target, "relation": "depends_on", "origin": {"type": "static", "source": result.path, "line": imp.line}, "confidence": 1.0, "verified": False})
            elif unknown:
                diagnostics.append(Diagnostic("EPE-AST-IMPORT-UNKNOWN", Severity.WARNING, unknown, path=result.path, line=imp.line))
                edges.append({"from": source_id, "to": f"UNKNOWN-{imp.module or 'relative'}", "relation": "depends_on", "origin": {"type": "static", "source": result.path, "line": imp.line}, "confidence": 0.0, "verified": False})
            else:
                target = f"EXT-{imp.module or '.'}"
                edges.append({"from": source_id, "to": target, "relation": "depends_on", "origin": {"type": "static", "source": result.path, "line": imp.line}, "confidence": 0.5, "verified": False})
    module_edges, module_diagnostics, module_coverage = _aggregate_module_dependencies(registry, code_results, edges, config.get("managed", {}).get("module_roots"))
    edges.extend(module_edges); diagnostics.extend(module_diagnostics)
    # Preserve distinct provenance and verification facts; remove exact duplicates only.
    dedup: dict[str, dict] = {}
    for edge in edges:
        dedup[sha256_json(edge)] = edge
    nodes = sorted({n["id"]: n for n in nodes}.values(), key=lambda n: n["id"])
    edges = sorted(dedup.values(), key=lambda e: (e["from"], e["to"], e["relation"], sha256_json(e)))
    manifest = graph_manifest(root, config)
    expected = {p: h for p, h in manifest.entries if _is_code_path(p, managed_roots)}
    actual = {r.path: r.digest for r in code_results}
    if len(actual) != len(code_results) or actual != expected or any(not r.complete for r in code_results):
        diagnostics.append(Diagnostic("EPE-GRAPH-FACTS", Severity.ERROR, "解析事实不完整或与输入清单不一致"))
    if graph_manifest(root, config).digest != manifest.digest:
        diagnostics.append(Diagnostic("EPE-GRAPH-INPUT-CHANGED", Severity.ERROR, "构图期间输入发生变化"))
    complete = not any(d.is_error for d in diagnostics)
    content = {"parser_config": _parser_config(config), "module_coverage": module_coverage, "schema_version": 1, "input_manifest": manifest.to_dict(), "complete": complete, "nodes": nodes, "edges": edges, "code_facts": [result.to_dict() for result in sorted(code_results, key=lambda item: item.path)], "diagnostics": [d.to_dict() for d in diagnostics]}
    content["content_digest"] = sha256_json({k: v for k, v in content.items() if k != "content_digest"})
    derived = root / config.get("storage", {}).get("derived", ".engineering")
    if not complete:
        return GraphBuildResult(content, diagnostics, False)
    try:
        with acquire_write_lock(derived / ".write.lock"):
            generation = content["content_digest"]
            generations = derived / "generations"
            generations.mkdir(parents=True, exist_ok=True)
            temporary = generations / f".tmp-{generation}"
            final = generations / generation
            if temporary.exists():
                import shutil
                shutil.rmtree(temporary)
            temporary.mkdir(parents=True)
            atomic_write_json(temporary / "entities.json", registry.to_dict())
            atomic_write_json(temporary / "graph.json", content)
            if final.exists():
                try:
                    existing_graph = json.loads((final / "graph.json").read_text(encoding="utf-8"))
                    existing_entities = json.loads((final / "entities.json").read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise ValueError("已有 generation 无法读取") from exc
                if existing_graph != content or existing_entities != registry.to_dict():
                    raise ValueError("已有 generation 内容与待发布载荷不一致")
                import shutil
                shutil.rmtree(temporary)
            else:
                os.replace(temporary, final)
            # Compatibility views are non-authoritative; the pointer is the commit point.
            atomic_write_json(derived / "entities.json", registry.to_dict())
            atomic_write_json(derived / "graph.json", content)
            atomic_write_json(derived / "current.json", {"schema_version": 1, "generation": generation, "content_digest": content["content_digest"]})
    except WriteConflict as exc:
        diagnostics.append(Diagnostic("EPE-WRITE-CONFLICT", Severity.ERROR, str(exc), path=str(derived)))
        return GraphBuildResult(content, diagnostics, False)
    except (OSError, ValueError) as exc:
        diagnostics.append(Diagnostic("EPE-GRAPH-PUBLISH", Severity.ERROR, str(exc), path=str(derived)))
        return GraphBuildResult(content, diagnostics, False)
    return GraphBuildResult(content, diagnostics, True)


def _parser_config(config: dict[str, Any]) -> dict[str, Any]:
    return {"version": "1", "builder_version": "3", "python": list(sys.version_info[:2]),
            "code_roots": list(config.get("managed", {}).get("code_roots", ["src"])),
            "module_roots": config.get("managed", {}).get("module_roots")}


def _is_code_path(path: str, roots: list[str]) -> bool:
    return path.endswith(".py") and any(path.startswith(r.rstrip("/") + "/") or path == r for r in roots)


def _restore_code_fact(value: dict[str, Any]) -> CodeParseResult:
    symbols = [SymbolRecord(item["qualified_name"], item["kind"], item["name"], item["path"], item["line"], item["end_line"], item["signature"], item["async"]) for item in value["symbols"]]
    imports = [ImportFact(item["module"], tuple(item["names"]), item["path"], item["line"], item["level"], item["dynamic"], item["kind"]) for item in value["imports"]]
    def restore_diagnostics(items):
        return [Diagnostic(**item) for item in items]
    result = CodeParseResult(value["path"], value["digest"], symbols, imports,
                             restore_diagnostics(value["diagnostics"]), restore_diagnostics(value["gaps"]), value["complete"])
    if result.to_dict() != value or result.complete is not True:
        raise ValueError("invalid code fact")
    if not isinstance(result.path, str) or not isinstance(result.digest, str):
        raise ValueError("invalid code fact identity")
    if any(item.path != result.path for item in symbols + imports):
        raise ValueError("invalid fact path")
    if any(d.severity not in {s.value for s in Severity} for d in result.diagnostics + result.gaps):
        raise ValueError("invalid diagnostic severity")
    return result


def _validated_previous(previous: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, str], list[CodeParseResult]]:
    if previous.get("complete") is not True or previous.get("schema_version") != 1 or previous.get("parser_config") != _parser_config(config):
        raise ValueError("incompatible snapshot")
    if previous.get("content_digest") != sha256_json({k: v for k, v in previous.items() if k != "content_digest"}):
        raise ValueError("snapshot digest mismatch")
    manifest = previous["input_manifest"]
    entries = manifest["entries"]
    if not isinstance(entries, list) or any(not isinstance(e, dict) or set(e) != {"path", "sha256"} or not isinstance(e["path"], str) or not isinstance(e["sha256"], str) or len(e["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in e["sha256"]) for e in entries):
        raise ValueError("invalid manifest")
    old = {e["path"]: e["sha256"] for e in entries}
    if len(old) != len(entries) or manifest.get("digest") != sha256_json(entries):
        raise ValueError("invalid manifest digest")
    raw_facts = previous["code_facts"]
    if not isinstance(raw_facts, list):
        raise ValueError("invalid facts")
    facts = [_restore_code_fact(fact) for fact in raw_facts]
    actual = {f.path: f.digest for f in facts}
    expected = {p: h for p, h in old.items() if _is_code_path(p, _parser_config(config)["code_roots"])}
    if len(actual) != len(facts) or actual != expected:
        raise ValueError("incomplete facts")
    return old, facts


def build_graph_incremental(root: Path, registry: Registry, previous: dict[str, Any] | None, config: dict[str, Any], parser_version: str = "1") -> GraphBuildResult:
    """Reuse only compatible, internally consistent cached facts; otherwise rebuild."""
    roots = config.get("managed", {}).get("code_roots", ["src"])
    try:
        if not isinstance(previous, dict) or parser_version != _parser_config(config)["version"]:
            raise ValueError("missing or incompatible snapshot")
        old, facts = _validated_previous(previous, config)
        current = dict(graph_manifest(root, config).entries)
        changed = {path for path in old.keys() | current.keys() if old.get(path) != current.get(path)}
        reused = [fact for fact in facts if fact.path not in changed]
        reparsed: list[CodeParseResult] = []
        for path in sorted(changed):
            if path not in current or not _is_code_path(path, roots):
                continue
            try:
                data = (root / path).read_bytes()
            except OSError as exc:
                diagnostic = Diagnostic("EPE-AST-READ", Severity.ERROR,
                                        f"无法读取 Python 文件: {exc}", path=path)
                return GraphBuildResult(None, [diagnostic], False)
            reparsed.append(parse_python(data, path))
        return build_graph(root, registry, reused + reparsed, config)
    except (KeyError, TypeError, ValueError, AttributeError):
        results, diagnostics = parse_python_tree(root, roots)
        if any(d.is_error for d in diagnostics):
            return GraphBuildResult(None, diagnostics, False)
        return build_graph(root, registry, results, config)


def _validate_graph_shape(snapshot: dict[str, Any]) -> None:
    """Validate the minimum node/edge shape before query consumers use a snapshot."""
    nodes = snapshot.get("nodes")
    edges = snapshot.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("图快照 nodes/edges 必须为数组")
    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"]:
            raise ValueError("图快照包含非法节点")
        if node["id"] in node_ids:
            raise ValueError(f"图快照包含重复节点: {node['id']}")
        node_ids.add(node["id"])
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("图快照包含非对象边")
        if any(not isinstance(edge.get(key), str) or not edge[key] for key in ("from", "to", "relation")):
            raise ValueError("图快照边缺少有效 from/to/relation")
        origin = edge.get("origin")
        if (not isinstance(origin, dict) or not isinstance(origin.get("type"), str)
                or not origin["type"] or not isinstance(origin.get("source"), str)
                or not origin["source"]):
            raise ValueError("图快照边 origin 结构无效")
        confidence = edge.get("confidence")
        if (type(confidence) not in {int, float} or isinstance(confidence, bool)
                or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1):
            raise ValueError("图快照边 confidence 超出合法范围")
        if not isinstance(edge.get("verified"), bool):
            raise ValueError("图快照边 verified 必须为布尔值")


def load_graph(root: Path, config: dict[str, Any]) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    derived = root / config.get("storage", {}).get("derived", ".engineering")
    path = derived / "graph.json"
    pointer = derived / "current.json"
    generation = None
    if pointer.exists():
        try:
            marker = json.loads(pointer.read_text(encoding="utf-8"))
            generation = marker.get("generation")
            if marker.get("schema_version") != 1 or not isinstance(generation, str) or re.fullmatch(r"[0-9a-f]{64}", generation) is None or generation != marker.get("content_digest"):
                return None, [Diagnostic("EPE-GRAPH-POINTER", Severity.ERROR, "当前图指针无效", path=str(pointer.relative_to(root)))]
            path = derived / "generations" / generation / "graph.json"
        except (OSError, ValueError, AttributeError, json.JSONDecodeError) as exc:
            return None, [Diagnostic("EPE-GRAPH-POINTER", Severity.ERROR, str(exc), path=str(pointer.relative_to(root)))]
    if not path.exists(): return None, [Diagnostic("EPE-GRAPH-MISSING", Severity.ERROR, "图快照不存在，请运行 epe graph build", path=str(path.relative_to(root)))]
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict) or snapshot.get("complete") is not True:
            return None, [Diagnostic("EPE-GRAPH-INCOMPLETE", Severity.ERROR, "图快照不完整", path=str(path.relative_to(root)))]
        content = {k: v for k, v in snapshot.items() if k != "content_digest"}
        if snapshot.get("content_digest") != sha256_json(content) or (generation is not None and snapshot.get("content_digest") != generation):
            return None, [Diagnostic("EPE-GRAPH-INTEGRITY", Severity.ERROR, "图快照摘要不匹配", path=str(path.relative_to(root)))]
        try:
            _validate_graph_shape(snapshot)
        except ValueError as exc:
            return None, [Diagnostic("EPE-GRAPH-SHAPE", Severity.ERROR, str(exc), path=str(path.relative_to(root)))]
        if snapshot.get("parser_config") != _parser_config(config):
            return None, [Diagnostic("EPE-GRAPH-STALE", Severity.ERROR, "图构建版本或解析配置已变更，请重新构建", path=str(path.relative_to(root)))]
        if snapshot.get("input_manifest", {}).get("digest") != graph_manifest(root, config).digest:
            return None, [Diagnostic("EPE-GRAPH-STALE", Severity.ERROR, "图快照与当前输入不匹配，请重新构建", path=str(path.relative_to(root)))]
        return snapshot, []
    except (OSError, ValueError, AttributeError) as exc: return None, [Diagnostic("EPE-GRAPH-READ", Severity.ERROR, str(exc), path=str(path.relative_to(root)))]


def load_historical_graph(root: Path, config: dict[str, Any], generation: str) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Load an explicitly selected historical generation without claiming freshness."""
    if not isinstance(generation, str) or re.fullmatch(r"[0-9a-f]{64}", generation) is None:
        return None, [Diagnostic("EPE-GRAPH-HISTORY", Severity.ERROR, "历史 generation 必须是完整 SHA-256")]
    base = (root / config.get("storage", {}).get("derived", ".engineering") / "generations").resolve()
    path = base / generation / "graph.json"
    try:
        path.resolve().relative_to(base)
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1
                or snapshot.get("complete") is not True or not isinstance(snapshot.get("nodes"), list)
                or not isinstance(snapshot.get("edges"), list) or not isinstance(snapshot.get("diagnostics"), list)
                or not isinstance(snapshot.get("input_manifest"), dict)
                or snapshot.get("content_digest") != generation
                or sha256_json({k: v for k, v in snapshot.items() if k != "content_digest"}) != generation):
            raise ValueError("历史图不完整或摘要不匹配")
        _validate_graph_shape(snapshot)
        return snapshot, []
    except (OSError, ValueError, TypeError) as exc:
        return None, [Diagnostic("EPE-GRAPH-HISTORY", Severity.ERROR, str(exc), path=str(path))]


def graph_neighbors(snapshot: dict[str, Any], entity_id: str, relation_types: set[str] | None = None, direction: str = "both") -> list[dict[str, Any]]:
    result = []
    for edge in snapshot.get("edges", []):
        if not isinstance(edge, dict):
            continue
        if relation_types and edge.get("relation") not in relation_types: continue
        if (direction in {"out", "both"} and edge.get("from") == entity_id) or (direction in {"in", "both"} and edge.get("to") == entity_id): result.append(edge)
    return sorted(result, key=lambda e: (e.get("from", ""), e.get("to", ""), e.get("relation", ""), sha256_json(e)))


def trace_path(snapshot: dict[str, Any], source: str, target: str, *, direction: str = "out", relation_types: set[str] | None = None, budget: int = 1000) -> dict[str, Any]:
    """Find one deterministic shortest path; the search does not prove graph completeness."""
    from collections import deque
    import json

    if direction not in {"out", "in", "both"} or isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ValueError("invalid direction or budget")
    nodes = {n["id"] for n in snapshot.get("nodes", []) if isinstance(n, dict) and isinstance(n.get("id"), str)}
    if source not in nodes or target not in nodes:
        raise ValueError("path endpoint not in graph")
    adjacency: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    for edge in snapshot.get("edges", []):
        if not isinstance(edge, dict):
            continue
        if relation_types is not None and edge.get("relation") not in relation_types:
            continue
        frm, to = edge.get("from"), edge.get("to")
        if frm not in nodes or to not in nodes:
            continue
        if direction in {"out", "both"}: adjacency.setdefault(frm, []).append((to, "out", edge))
        if direction in {"in", "both"}: adjacency.setdefault(to, []).append((frm, "in", edge))
    for items in adjacency.values():
        items.sort(key=lambda x: (x[0], x[1], json.dumps(x[2], sort_keys=True, ensure_ascii=True)))
    parents: dict[str, tuple[str, str, dict[str, Any]] | None] = {source: None}
    queue = deque([source]); expanded = 0
    while queue and target not in parents and expanded < budget:
        current = queue.popleft(); expanded += 1
        for nxt, step_direction, edge in adjacency.get(current, []):
            if nxt in parents: continue
            parents[nxt] = (current, step_direction, edge)
            queue.append(nxt)
            if nxt == target: break
    found = target in parents
    path: list[dict[str, Any]] = []
    if found:
        node = target
        while node != source:
            previous, step_direction, edge = parents[node]
            path.append({"edge": edge, "direction": step_direction})
            node = previous
        path.reverse()
    def uncertain(edge: dict[str, Any]) -> bool:
        origin = edge.get("origin")
        origin_type = origin.get("type") if isinstance(origin, dict) else None
        confidence = edge.get("confidence")
        determined = (
            origin_type in {"explicit", "static"}
            and type(confidence) in {int, float}
            and not isinstance(confidence, bool)
            and math.isfinite(float(confidence))
            and float(confidence) == 1.0
        )
        return not determined

    candidate = any(uncertain(step["edge"]) for step in path)
    return {"source": source, "target": target, "snapshot_digest": snapshot.get("content_digest"),
            "found": found, "path": path, "classification": ("candidate" if candidate else "determined") if found else None,
            "expanded": expanded, "budget": budget, "truncated": bool(queue and not found),
            "analysis_diagnostics": snapshot.get("diagnostics", [])}


def dependency_cycles(snapshot: dict[str, Any]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = {}
    for e in snapshot.get("edges", []):
        if e.get("relation") == "depends_on": adjacency.setdefault(e["from"], []).append(e["to"])
    cycles: list[list[str]] = []; stack: list[str] = []; active: set[str] = set(); done: set[str] = set()
    def visit(node: str):
        if node in active:
            try: cycles.append(stack[stack.index(node):] + [node])
            except ValueError: pass
            return
        if node in done: return
        active.add(node); stack.append(node)
        for nxt in sorted(adjacency.get(node, [])): visit(nxt)
        stack.pop(); active.remove(node); done.add(node)
    for node in sorted(adjacency): visit(node)
    return cycles


def analyze_impact(snapshot: dict[str, Any], changed_entities: list[str], budget: int = 100) -> dict[str, Any]:
    """Traverse explicitly supported relation directions, retaining path uncertainty."""
    from collections import deque

    nodes = {n.get("id"): n for n in snapshot.get("nodes", []) if isinstance(n, dict) and isinstance(n.get("id"), str)}
    roots = list(dict.fromkeys(changed_entities))
    missing = [eid for eid in roots if eid not in nodes]
    gaps = [d for d in snapshot.get("diagnostics", []) if isinstance(d, dict) and d.get("code") in {"EPE-AST-DYNAMIC", "EPE-AST-STAR-IMPORT", "EPE-AST-IMPORT-UNKNOWN", "EPE-AST-MODULE-UNASSIGNED"}]
    adjacency: dict[str, list[tuple[str, dict[str, Any], str]]] = {}

    def add(source: str, target: str, edge: dict[str, Any], direction: str) -> None:
        adjacency.setdefault(source, []).append((target, edge, direction))

    forward = {"realizes", "verified_by", "evidenced_by", "conforms_to", "specifies", "affects"}
    reverse = {"realizes", "depends_on"}
    for edge in snapshot.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src, dst, relation = edge.get("from"), edge.get("to"), edge.get("relation")
        if not isinstance(src, str) or not isinstance(dst, str):
            continue
        if relation in forward:
            add(src, dst, edge, "forward")
        if relation in reverse:
            add(dst, src, edge, "reverse")
    for node_id, node in nodes.items():
        if node.get("kind") != "Symbol":
            continue
        path = node.get("source", {}).get("path")
        source_id = _source_node(path) if isinstance(path, str) else None
        if source_id in nodes:
            edge = {"from": source_id, "to": node_id, "relation": "defines", "origin": {"type": "static", "source": path}, "confidence": 1.0, "verified": True}
            add(source_id, node_id, edge, "forward")
            add(node_id, source_id, edge, "reverse")
    for outgoing in adjacency.values():
        outgoing.sort(key=lambda item: (item[0], str(item[1].get("relation")), item[2], sha256_json(item[1])))

    result: dict[str, dict[str, Any]] = {}
    # Best known certainty per node; revisiting on an upgrade propagates it downstream.
    best = {eid: True for eid in roots if eid in nodes}
    queue = deque((eid, [], True, eid) for eid in roots if eid in nodes)
    truncated = budget <= 0
    while queue and budget > 0:
        current, path, certain, origin = queue.popleft()
        if not certain and best.get(current) is True:
            continue
        for target, edge, direction in adjacency.get(current, []):
            origin_type = edge.get("origin", {}).get("type") if isinstance(edge.get("origin"), dict) else None
            confidence = edge.get("confidence")
            next_certain = (certain and origin_type in {"explicit", "static"}
                            and type(confidence) in (int, float) and confidence == 1)
            prior = best.get(target)
            if prior is True or (prior is False and not next_certain):
                continue
            if target not in best and len(result) >= budget:
                truncated = True
                continue
            next_path = path + [{**edge, "direction": direction}]
            best[target] = next_certain
            result[target] = {"entity_id": target, "classification": "determined" if next_certain else "candidate", "reason": edge.get("relation"), "origin_entity": origin, "path": next_path}
            queue.append((target, next_path, next_certain, origin))
    return {"changed_entities": changed_entities, "impacts": [result[k] for k in sorted(result)],
            "truncated": truncated, "incomplete": truncated or bool(missing) or bool(gaps),
            "missing_entities": missing, "analysis_gaps": gaps, "budget": budget,
            "snapshot_digest": snapshot.get("content_digest")}


def plan_incremental(previous: dict[str, Any] | None, current: dict[str, Any] | None, parser_version: str = "1", previous_parser_version: str = "1") -> dict[str, Any]:
    """Plan a manifest delta only from compatible, internally consistent snapshots."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return {"full_rebuild": True, "reason": "snapshot_missing_or_incomplete", "paths": []}
    try:
        current_config = current["parser_config"]
        previous_config = previous["parser_config"]
        if (not isinstance(current_config, dict) or not isinstance(previous_config, dict)
                or current_config != previous_config
                or parser_version != current_config.get("version")
                or previous_parser_version != previous_config.get("version")):
            return {"full_rebuild": True, "reason": "parser_or_schema_changed", "paths": []}
        roots = current_config["code_roots"]
        if not isinstance(roots, list) or any(not isinstance(root, str) for root in roots):
            raise ValueError("invalid code roots")
        config = {"managed": {"code_roots": roots, "module_roots": current_config.get("module_roots")}}
        old, _ = _validated_previous(previous, config)
        new, _ = _validated_previous(current, config)
    except (KeyError, TypeError, ValueError, AttributeError):
        return {"full_rebuild": True, "reason": "snapshot_invalid_or_incompatible", "paths": []}
    changed = sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))
    return {"full_rebuild": False, "reason": "manifest_delta", "paths": changed,
            "previous_digest": previous["content_digest"], "current_digest": current["content_digest"]}
