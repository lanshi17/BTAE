from __future__ import annotations

import re
from pathlib import PurePosixPath
from dataclasses import dataclass, field
from typing import Iterable

from .diagnostics import Diagnostic, Severity
from .models import Entity, Relation, SourceLocation
from .fingerprint import sha256_json


ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z0-9][A-Z0-9_-]*$")
TYPE_PREFIXES = {
    "Intent": "INTENT-", "Spec": "SPEC-", "Architecture": "ARCH-", "Module": "MOD-",
    "Component": "COMP-", "Class": "CLASS-", "Contract": "CONTRACT-", "ADR": "ADR-",
    "Task": "TASK-", "ChangeSet": "CHANGE-", "Test": "TEST-", "Evidence": "EVIDENCE-",
}
RELATIONS = {
    "contains": ({"Architecture", "Module", "Component"}, {"Module", "Component", "Class"}),
    "realizes": ({"Component", "Class", "Module", "Spec"}, {"Source", "Symbol"}),
    "specifies": ({"Spec"}, {"Module", "Component", "Class", "Contract"}),
    "depends_on": ({"Module", "Component", "Class", "Source", "Symbol"}, {"Module", "Component", "Class", "Source", "Symbol"}),
    "conforms_to": ({"Source", "Symbol", "API", "DataModel"}, {"Contract"}),
    "verified_by": ({"Spec", "Component", "Class", "Contract"}, {"Test", "Evaluation"}),
    "evidenced_by": ({"ChangeSet", "Task", "Test", "Evaluation", "Component", "Class", "Contract"}, {"Evidence"}),
    "constrained_by": ({"Architecture", "Module", "Component", "Class"}, {"ADR", "Contract"}),
    "supersedes": ({"Intent", "Spec", "Architecture", "Module", "Component", "Class", "Contract", "ADR"}, {"Intent", "Spec", "Architecture", "Module", "Component", "Class", "Contract", "ADR"}),
    "affects": ({"ChangeSet"}, set()),
}


@dataclass
class Registry:
    entities: dict[str, Entity] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)

    def get(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "entities": [self.entities[k].to_dict() for k in sorted(self.entities)],
            "relations": [r.to_dict() for r in sorted(self.relations, key=lambda x: (x.from_id, x.to_id, x.relation, sha256_json(x.to_dict())))],
        }


@dataclass
class RegistryBuildResult:
    registry: Registry
    diagnostics: list[Diagnostic]
    complete: bool


def validate_entity_dict(data: dict, path: str, line: int | None = None) -> tuple[Entity | None, list[Diagnostic]]:
    ds: list[Diagnostic] = []
    if not isinstance(data, dict):
        return None, [Diagnostic("EPE-ENTITY-TYPE", Severity.ERROR, "实体必须为对象", path=path, line=line)]
    allowed_fields = {"schema_version", "id", "type", "name", "version", "source", "design_status", "implementation_status", "verification_status", "implementation", "verification", "contracts", "lifecycle", "relations", "extensions"}
    if data.get("type") == "Contract":
        allowed_fields.add("schema")
    for key in sorted(set(data) - allowed_fields, key=lambda item: (type(item).__name__, repr(item))):
        ds.append(Diagnostic("EPE-ENTITY-UNKNOWN-FIELD", Severity.ERROR, f"未知实体字段: {key}", path=path, line=line))
    for key in ("id", "type", "name"):
        if key not in data:
            ds.append(Diagnostic("EPE-ENTITY-REQUIRED", Severity.ERROR, f"缺少必填字段 {key}", path=path, line=line))
        elif not isinstance(data[key], str) or not data[key].strip():
            ds.append(Diagnostic("EPE-ENTITY-FIELD", Severity.ERROR, f"字段必须为非空字符串: {key}", path=path, line=line))
    if data.get("schema_version", 1) != 1:
        ds.append(Diagnostic("EPE-ENTITY-SCHEMA", Severity.ERROR, "实体 schema_version 必须为 1", path=path, line=line))
    entity_id, typ = data.get("id"), data.get("type")
    diagnostic_id = entity_id if isinstance(entity_id, str) else None
    if isinstance(entity_id, str) and not ID_RE.match(entity_id):
        ds.append(Diagnostic("EPE-ENTITY-ID", Severity.ERROR, f"非法实体 ID: {entity_id}", entity_id=diagnostic_id, path=path, line=line))
    expected = TYPE_PREFIXES.get(typ) if isinstance(typ, str) else None
    if expected and isinstance(entity_id, str) and not entity_id.startswith(expected):
        ds.append(Diagnostic("EPE-ENTITY-PREFIX", Severity.ERROR, f"实体 ID 前缀与类型不匹配: {typ} / {entity_id}", entity_id=diagnostic_id, path=path, line=line))
    if typ == "Contract":
        version = data.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            ds.append(Diagnostic("EPE-CONTRACT-VERSION", Severity.ERROR, "Contract version 必须为正整数", entity_id=diagnostic_id, path=path, line=line))
        if not isinstance(data.get("schema"), dict):
            ds.append(Diagnostic("EPE-CONTRACT-SCHEMA", Severity.ERROR, "Contract schema 必须为对象", entity_id=diagnostic_id, path=path, line=line))
    statuses = {"design_status": {"draft", "reviewed", "approved"}, "implementation_status": {"not_started", "in_progress", "implemented"}, "verification_status": {"pending", "passed", "failed"}, "lifecycle": {"active", "archived"}}
    for key, allowed in statuses.items():
        if key in data and (not isinstance(data[key], str) or data[key] not in allowed):
            ds.append(Diagnostic("EPE-ENTITY-ENUM", Severity.ERROR, f"{key} 值非法: {data[key]}", entity_id=diagnostic_id, path=path, line=line))
    source = data.get("source", path)
    if isinstance(source, str): source = {"path": source}
    if not isinstance(source, dict) or set(source) - {"path", "line", "column"} or not isinstance(source.get("path"), str) or not source["path"].strip() or source["path"].startswith("/") or ".." in PurePosixPath(source["path"]).parts:
        ds.append(Diagnostic("EPE-ENTITY-SOURCE", Severity.ERROR, "source 必须是仓库相对 path 及可选 line/column", entity_id=diagnostic_id, path=path, line=line)); source = {"path": path}
    for key in ("line", "column"):
        if key in source and (isinstance(source[key], bool) or not isinstance(source[key], int) or source[key] < 1):
            ds.append(Diagnostic("EPE-ENTITY-SOURCE", Severity.ERROR, f"source.{key} 必须为正整数", entity_id=diagnostic_id, path=path, line=line))
    def mapping_list(key: str) -> list[dict[str, Any]]:
        value = data.get(key, [])
        if not isinstance(value, list):
            ds.append(Diagnostic("EPE-ENTITY-LIST", Severity.ERROR, f"{key} 必须为数组", entity_id=diagnostic_id, path=path, line=line)); return []
        result = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"].strip() or item["path"].startswith("/") or ".." in PurePosixPath(item["path"]).parts or ("symbol" in item and not isinstance(item["symbol"], str)):
                ds.append(Diagnostic("EPE-ENTITY-MAPPING", Severity.ERROR, f"{key} 包含非法映射", entity_id=diagnostic_id, path=path, line=line)); continue
            result.append(item)
        return result
    impl = mapping_list("implementation"); ver = mapping_list("verification")
    contracts = data.get("contracts", [])
    if not isinstance(contracts, list) or not all(isinstance(item, str) and item for item in contracts):
        ds.append(Diagnostic("EPE-ENTITY-CONTRACTS", Severity.ERROR, "contracts 必须为字符串数组", entity_id=diagnostic_id, path=path, line=line)); contracts = []
    relations = data.get("relations", [])
    if not isinstance(relations, list) or not all(isinstance(item, dict) for item in relations):
        ds.append(Diagnostic("EPE-ENTITY-RELATIONS", Severity.ERROR, "relations 必须为对象数组", entity_id=diagnostic_id, path=path, line=line)); relations = []
    extensions = data.get("extensions", {})
    if not isinstance(extensions, dict):
        ds.append(Diagnostic("EPE-ENTITY-EXTENSIONS", Severity.ERROR, "extensions 必须为对象", entity_id=diagnostic_id, path=path, line=line)); extensions = {}
    if any(d.is_error for d in ds):
        return None, ds
    loc = SourceLocation(str(source["path"]), source.get("line", line), source.get("column"))
    return Entity(1, entity_id, typ, data["name"], loc, data.get("design_status"), data.get("implementation_status"), data.get("verification_status"), impl, ver, contracts, data.get("lifecycle", "active"), relations, dict(data)), ds


def build_registry(candidates: Iterable[tuple[dict, str, int | None]], relation_candidates: Iterable[tuple[dict, str]] = ()) -> RegistryBuildResult:
    reg = Registry()
    diagnostics: list[Diagnostic] = []
    for data, path, line in candidates:
        entity, ds = validate_entity_dict(data, path, line)
        diagnostics.extend(ds)
        if entity is None:
            continue
        if entity.id in reg.entities:
            diagnostics.append(Diagnostic("EPE-ENTITY-DUPLICATE", Severity.ERROR, f"重复实体 ID: {entity.id}", entity.id, path))
            continue
        reg.entities[entity.id] = entity
    raw_rels: list[tuple[dict, str]] = []
    for item in relation_candidates:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], dict):
            raw_rels.append((item[0], str(item[1])))
        else:
            diagnostics.append(Diagnostic("EPE-RELATION-INPUT", Severity.ERROR, "关系候选必须是 (object, path) 元组"))
    for entity in reg.entities.values():
        for rel in entity.relations:
            if isinstance(rel, dict):
                raw_rels.append((dict(rel, **({"from": entity.id} if "from" not in rel else {})), entity.source.path))
    seen: set[tuple] = set()
    for raw, path in raw_rels:
        frm, to, relation = raw.get("from"), raw.get("to"), raw.get("relation")
        if not all(isinstance(x, str) and x for x in (frm, to, relation)):
            diagnostics.append(Diagnostic("EPE-RELATION-FIELDS", Severity.ERROR, "关系缺少 from/to/relation", path=path)); continue
        if frm not in reg.entities or to not in reg.entities:
            diagnostics.append(Diagnostic("EPE-RELATION-DANGLING", Severity.ERROR, f"关系端点不存在: {frm} -> {to}", path=path)); continue
        if frm == to:
            diagnostics.append(Diagnostic("EPE-RELATION-SELF", Severity.ERROR, "关系禁止自环", entity_id=frm, path=path)); continue
        conf = raw.get("confidence", 1.0)
        if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= float(conf) <= 1:
            diagnostics.append(Diagnostic("EPE-RELATION-CONFIDENCE", Severity.ERROR, "confidence 必须在 [0,1]", path=path)); continue
        origin = raw.get("origin", {"type": "explicit", "source": path})
        if relation not in RELATIONS:
            diagnostics.append(Diagnostic("EPE-RELATION-TYPE", Severity.ERROR, f"未知关系类型: {relation}", path=path)); continue
        allowed_fields = {"from", "to", "relation", "origin", "confidence", "verified", "verification"}
        if set(raw) - allowed_fields:
            diagnostics.append(Diagnostic("EPE-RELATION-FIELDS", Severity.ERROR, "关系包含未知字段", path=path)); continue
        if not isinstance(origin, dict) or not isinstance(origin.get("type"), str) or origin.get("type") not in {"explicit", "static", "inferred"} or not isinstance(origin.get("source"), str) or not origin["source"].strip():
            diagnostics.append(Diagnostic("EPE-RELATION-ORIGIN", Severity.ERROR, "origin 必须包含合法 type 和非空 source", path=path)); continue
        verified = raw.get("verified", False)
        if not isinstance(verified, bool):
            diagnostics.append(Diagnostic("EPE-RELATION-VERIFIED", Severity.ERROR, "verified 必须为布尔值", path=path)); continue
        verification = raw.get("verification")
        if verification is not None:
            required = {"verifier", "method", "timestamp", "version"}
            if not isinstance(verification, dict) or set(verification) != required or any(not isinstance(verification.get(key), str) or not verification[key].strip() for key in required):
                diagnostics.append(Diagnostic("EPE-RELATION-VERIFICATION", Severity.ERROR, "verification 必须包含且仅包含 verifier/method/timestamp/version", path=path)); continue
        if verified and verification is None:
            diagnostics.append(Diagnostic("EPE-RELATION-VERIFICATION", Severity.ERROR, "verified=true 必须提供验证元数据", entity_id=frm, path=path)); continue
        if not verified and verification is not None:
            diagnostics.append(Diagnostic("EPE-RELATION-VERIFICATION", Severity.ERROR, "未验证关系不能携带 verification", entity_id=frm, path=path)); continue
        record = Relation(frm, to, relation, origin, float(conf), verified, verification)
        try:
            key = sha256_json(record.to_dict())
        except (TypeError, ValueError):
            diagnostics.append(Diagnostic("EPE-RELATION-ORIGIN", Severity.ERROR, "origin 必须可序列化为 JSON 对象", path=path)); continue
        if key in seen:
            diagnostics.append(Diagnostic("EPE-RELATION-DUPLICATE", Severity.ERROR, f"重复关系: {frm} -[{relation}]-> {to}", path=path)); continue
        seen.add(key)
        reg.relations.append(record)
    # Relation endpoint checks are deliberately performed after registration.
    for rel in reg.relations:
        a, b = reg.entities[rel.from_id].type, reg.entities[rel.to_id].type
        allowed = RELATIONS.get(rel.relation)
        if allowed and rel.relation != "affects" and (a not in allowed[0] or b not in allowed[1]):
            diagnostics.append(Diagnostic("EPE-RELATION-ENDPOINT", Severity.ERROR, f"关系端点类型非法: {a} -[{rel.relation}]-> {b}"))
    return RegistryBuildResult(reg, diagnostics, not any(d.is_error for d in diagnostics))
