from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from epe.core.fingerprint import build_manifest, sha256_bytes
from epe.core.models import InputManifest
from epe.core.registry import Registry
from epe.graph.builder import graph_neighbors
from epe.core.fingerprint import sha256_json
from epe.adapters.storage import atomic_write_json


def context_inputs_manifest(root: Path, config: dict[str, Any]):
    managed = config.get("managed", {})
    roots = (managed.get("design_roots", []) + managed.get("code_roots", [])
             + managed.get("test_roots", []) + managed.get("contract_roots", [])
             + ["AGENTS.md", "archive", "docs/architecture/decisions", "engineering/epe.yaml",
                "engineering/policies", "engineering/approvals", "engineering/audit"])
    manifest = build_manifest(root, roots, tuple(config.get("exclude", [])))
    entries = dict(manifest.entries)
    # Evidence may be located under reports/, which generic source manifests omit.
    evidence_root = root / config.get("storage", {}).get("evidence", "engineering/evidence")
    for path in sorted(evidence_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
            entries[rel] = sha256_bytes(path.read_bytes())
        except (OSError, ValueError):
            raise ValueError(f"无法读取或越界的证据来源: {path}")
    pairs = tuple(sorted(entries.items()))
    return InputManifest(pairs, sha256_json([{"path": p, "sha256": digest} for p, digest in pairs]))


def context_cache_key(task: Any, snapshot: dict[str, Any] | None, config: dict[str, Any], budget: int, required_sources: list[dict[str, Any]] | None = None, source_assessments: dict[str, Any] | None = None) -> str:
    manifest = context_inputs_manifest(Path(config["_root"]), config)
    payload = {"version": 5, "required_sources": required_sources or [], "source_assessments": source_assessments or {}, "task": getattr(task, "to_dict", lambda: {"id": getattr(task, "id", None), "objective": getattr(task, "objective", None), "acceptance": getattr(task, "acceptance", []), "risk": getattr(task, "risk", None), "target_entities": getattr(task, "target_entities", []), "changeset": getattr(task, "changeset", None)})(), "snapshot": snapshot.get("content_digest") if snapshot else None, "manifest": manifest.digest, "budget": budget}
    return sha256_json(payload)


def load_cached_context(root: Path, config: dict[str, Any], task: Any, snapshot: dict[str, Any] | None, budget: int, required_sources: list[dict[str, Any]] | None = None, source_assessments: dict[str, Any] | None = None) -> dict[str, Any] | None:
    local = dict(config); local["_root"] = str(root)
    key = context_cache_key(task, snapshot, local, budget, required_sources, source_assessments)
    path = root / config.get("storage", {}).get("derived", ".engineering") / "context" / f"{key}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("cache_key") != key or data.get("input_manifest", {}).get("digest") != context_inputs_manifest(root, config).digest: return None
        if data.get("content_digest") != sha256_json({k: v for k, v in data.items() if k != "content_digest"}): return None
        for item in data.get("items", []):
            path = (root / item["path"]).resolve()
            path.relative_to(root.resolve())
            if sha256_bytes(path.read_bytes()) != item.get("content_sha256"): return None
        return data
    except (OSError, json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError): return None


def store_cached_context(root: Path, config: dict[str, Any], task: Any, snapshot: dict[str, Any] | None, budget: int, bundle: dict[str, Any], required_sources: list[dict[str, Any]] | None = None, source_assessments: dict[str, Any] | None = None) -> None:
    local = dict(config); local["_root"] = str(root)
    if bundle.get("incomplete") or bundle.get("input_manifest", {}).get("digest") != context_inputs_manifest(root, config).digest:
        return
    key = context_cache_key(task, snapshot, local, budget, required_sources, source_assessments)
    path = root / config.get("storage", {}).get("derived", ".engineering") / "context" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(bundle); data["cache_key"] = key
    data["content_digest"] = sha256_json(data)
    atomic_write_json(path, data)


def _item(path: str, level: str, reason: str, root: Path, source_type: str = "file", entity_id: str | None = None, confidence: float = 1.0, freshness: str = "current") -> dict[str, Any]:
    file_path = (root / path).resolve()
    file_path.relative_to(root.resolve())
    data = file_path.read_bytes()
    text = data.decode("utf-8")
    return {"entity_id": entity_id, "path": path, "level": level, "source": path, "source_type": source_type,
            "freshness": freshness, "confidence": confidence, "reason": reason, "content": text[:4000],
            "content_sha256": sha256_bytes(data), "truncated": len(text) > 4000}


def resolve_context(root: Path, config: dict[str, Any], task: Any, registry: Registry, snapshot: dict[str, Any] | None, budget: int = 32, required_sources: list[dict[str, Any]] | None = None, required_omissions: list[str] | None = None, source_assessments: dict[str, Any] | None = None) -> dict[str, Any]:
    before = context_inputs_manifest(root, config)
    items: list[dict[str, Any]] = []; by_path: dict[str, dict[str, Any]] = {}; omissions: list[str] = []
    def add(path: str, level: str, reason: str, entity_id: str | None = None, source_type: str = "file", confidence: float = 1.0, freshness: str = "current", selection: dict[str, Any] | None = None, entity: Any = None):
        selected = {"reason": reason, "entity_id": entity_id, **(selection or {})}
        if entity is not None:
            selected["declared_design_status"] = entity.design_status
            selected["lifecycle"] = entity.lifecycle
            selected["approval_applicability"] = ((source_assessments or {}).get("entities", {}).get(entity_id, {}).get("approval_applicability", "unknown"))
        if path in by_path:
            if selected not in by_path[path]["selections"]:
                by_path[path]["selections"].append(selected)
            return
        if len(items) >= budget:
            omissions.append(path)
            return
        try:
            item = _item(path, level, reason, root, source_type, entity_id, confidence, freshness)
        except (OSError, UnicodeError, ValueError):
            omissions.append(path); return
        item["selections"] = [selected]
        by_path[path] = item; items.append(item)
    # C0 is mandatory and cannot be silently trimmed.
    add("AGENTS.md", "C0", "全局工程协议", source_type="rule", selection={"selection_type": "required"})
    add("docs/index.md", "C0", "文档入口", selection={"selection_type": "required"})
    for source in required_sources or []:
        add(source["path"], "C0", source["reason"], source.get("entity_id"), source["source_type"],
            freshness="unknown", selection={"selection_type": "required", "assessment": "not_evaluated"})
    omissions.extend(required_omissions or [])
    for eid in getattr(task, "target_entities", []) if task else []:
        entity = registry.get(eid)
        if not entity: omissions.append(eid); continue
        entity_freshness = "historical" if entity.lifecycle == "archived" else "current"
        add(entity.source.path, "C1", "任务目标实体设计", eid, "design", freshness=entity_freshness, selection={"selection_type": "target"}, entity=entity)
        if snapshot:
            for edge in graph_neighbors(snapshot, eid, direction="both"):
                other = edge.get("to") if edge.get("from") == eid else edge.get("from")
                other_entity = registry.get(other)
                if other_entity and other_entity.lifecycle != "archived":
                    origin = edge.get("origin") if isinstance(edge.get("origin"), dict) else {}
                    edge_confidence = edge.get("confidence")
                    add(other_entity.source.path, "C1", f"图邻接关系: {edge.get('relation')}", other, "design", 0.0,
                        selection={"selection_type": "graph_neighbor", "anchor_entity": eid, "relation": edge.get("relation"),
                                   "relation_origin": origin, "relation_confidence": edge_confidence,
                                   "relation_verified": edge.get("verified") is True}, entity=other_entity)
        for mapping in entity.implementation:
            if isinstance(mapping, dict) and mapping.get("path"):
                add(str(mapping["path"]), "C2", "目标实体实现映射", eid, "implementation", freshness=entity_freshness, selection={"selection_type": "implementation_mapping"})
        for test in entity.verification:
            if isinstance(test, dict) and test.get("path"):
                add(str(test["path"]), "C2", "目标实体验证映射", eid, "test", freshness=entity_freshness, selection={"selection_type": "verification_mapping"})
    objective = getattr(task, "objective", "") if task else ""
    if objective:
        keywords = {word.lower() for word in str(objective).split() if len(word) > 2}
        for entity in registry.entities.values():
            if entity.lifecycle == "archived": continue
            if keywords and any(word in (entity.name + " " + entity.source.path).lower() for word in keywords):
                add(entity.source.path, "C2", "目标文本关键词匹配", entity.id, "design", 0.5, selection={"selection_type": "keyword"}, entity=entity)
    # C3 is deliberately last and never replaces C0/C1. Historical ADRs and
    # execution evidence remain labelled; they are context, not authorization.
    decisions = root / "docs/architecture/decisions"
    if decisions.exists():
        for path in sorted(decisions.rglob("*.md")):
            add(path.relative_to(root).as_posix(), "C3", "历史 ADR 背景", source_type="historical", confidence=0.4, freshness="historical")
    archive = root / "archive"
    if archive.exists():
        for path in sorted(archive.rglob("*.md")):
            add(path.relative_to(root).as_posix(), "C3", "归档背景", source_type="historical", confidence=0.3, freshness="historical")
    evidence_root = root / config.get("storage", {}).get("evidence", "engineering/evidence")
    if evidence_root.exists():
        for path in sorted(evidence_root.glob("*/evidence.json")):
            try: evidence = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): continue
            if getattr(task, "id", None) and evidence.get("task_id") == task.id:
                evidence_path = path.relative_to(root).as_posix()
                validity = (source_assessments or {}).get("evidence", {}).get(evidence_path, {}).get("validity", "unknown")
                freshness = {"valid": "current", "stale": "stale", "invalid": "unknown", "unknown": "unknown"}.get(validity, "unknown")
                add(evidence_path, "C3", "任务验证证据摘要", source_type="evidence", confidence=0.8, freshness=freshness, selection={"selection_type": "evidence", "validity": validity})
    manifest = context_inputs_manifest(root, config)
    changed = before.digest != manifest.digest
    for item in items:
        try:
            path = (root / item["path"]).resolve()
            path.relative_to(root.resolve())
            if sha256_bytes(path.read_bytes()) != item["content_sha256"]:
                changed = True
        except (OSError, ValueError):
            changed = True
    truncated = [item["path"] for item in items if item["truncated"]]
    unknowns = ["动态运行依赖未由静态上下文解析"]
    if changed: unknowns.append("上下文装配期间输入发生变化")
    return {"task_id": getattr(task, "id", None), "snapshot_digest": snapshot.get("content_digest") if snapshot else None, "input_manifest": manifest.to_dict(), "budget": budget, "items": items, "omissions": omissions, "truncated_paths": truncated, "incomplete": bool(omissions or truncated or changed), "unknowns": unknowns, "source_assessments": source_assessments or {}}
