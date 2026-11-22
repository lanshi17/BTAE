from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from epe.core.diagnostics import Diagnostic, Severity
from epe.core.fingerprint import sha256_bytes, sha256_json
from epe.core.models import Approval, Entity
from epe.core.registry import Registry
from epe.parsers.documents import parse_yaml_bytes


def _design_source_path(root: Path, path_text: str) -> Path:
    root = root.resolve()
    raw_path = root / path_text
    current = root
    for component in Path(path_text).parts:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"设计或契约源不能经过符号链接: {path_text}")
    path = raw_path.resolve()
    path.relative_to(root)
    return path


def design_revision(root: Path, entity: Entity, registry: Registry | None = None) -> str:
    def digest(path_text: str) -> str:
        path = _design_source_path(root, path_text)
        return sha256_bytes(path.read_bytes())

    contracts = {}
    if registry:
        for contract_id in entity.contracts:
            contract = registry.get(contract_id)
            if contract is None: raise ValueError(f"契约不存在: {contract_id}")
            contracts[contract_id] = digest(contract.source.path)
    declaration = dict(entity.raw) if isinstance(entity.raw, dict) else entity.to_dict()
    payload = {"algorithm": "epe-design-revision-v3", "entity": entity.to_dict(), "declaration": declaration, "content_sha256": digest(entity.source.path), "contracts": contracts}
    return sha256_json(payload)


def validate_design(registry: Registry, entity_id: str, root: Path) -> tuple[dict[str, Any], list[Diagnostic]]:
    entity = registry.get(entity_id)
    if entity is None: return {}, [Diagnostic("EPE-DESIGN-MISSING", Severity.ERROR, f"实体不存在: {entity_id}", entity_id=entity_id)]
    ds: list[Diagnostic] = []; path = entity.source.path
    if not entity.name: ds.append(Diagnostic("EPE-DESIGN-NAME", Severity.ERROR, "设计缺少 name", entity_id=entity_id, path=path))
    if entity.design_status is None: ds.append(Diagnostic("EPE-DESIGN-STATUS", Severity.ERROR, "设计缺少 design_status", entity_id=entity_id, path=path))
    if entity.type == "Contract":
        _, contract_ds = validate_contract(entity, root)
        ds.extend(contract_ds)
    if entity.type in {"Class", "Component", "Module"} and entity.implementation_status == "implemented" and not entity.implementation:
        ds.append(Diagnostic("EPE-DESIGN-IMPLEMENTATION", Severity.ERROR, "已实现实体缺少 implementation 映射", entity_id=entity_id, path=path))
    for contract in entity.contracts:
        contract_entity = next((e for e in registry.entities.values() if e.id == contract), None)
        if contract_entity is None: ds.append(Diagnostic("EPE-DESIGN-CONTRACT", Severity.ERROR, f"契约引用不存在: {contract}", entity_id=entity_id, path=path)); continue
        _, contract_ds = validate_contract(contract_entity, root)
        ds.extend(contract_ds)
    try:
        revision = design_revision(root, entity, registry)
    except (OSError, ValueError) as exc:
        ds.append(Diagnostic("EPE-DESIGN-REVISION", Severity.ERROR, f"无法计算设计指纹: {exc}", entity_id=entity_id, path=path))
        revision = None
    return {"entity_id": entity_id, "revision": revision, "design_status": entity.design_status, "implementation_status": entity.implementation_status, "contract_ids": entity.contracts}, ds


def validate_contract(entity: Entity, root: Path) -> tuple[dict[str, Any], list[Diagnostic]]:
    try:
        path = _design_source_path(root, entity.source.path)
        raw, diagnostics = parse_yaml_bytes(path.read_bytes(), entity.source.path)
    except (OSError, ValueError) as exc:
        return {}, [Diagnostic("EPE-CONTRACT-READ", Severity.ERROR, str(exc), entity_id=entity.id, path=entity.source.path)]
    if diagnostics: return {}, diagnostics
    if not isinstance(raw, dict): return {}, [Diagnostic("EPE-CONTRACT-TYPE", Severity.ERROR, "契约必须是对象", entity_id=entity.id, path=entity.source.path)]
    try:
        import jsonschema
        from importlib.resources import files
        contract_schema = json.loads(files("epe.data.schemas").joinpath("contract.schema.json").read_text(encoding="utf-8"))
        errors = sorted(jsonschema.Draft202012Validator(contract_schema).iter_errors(raw), key=lambda error: (tuple(str(part) for part in error.path), error.message))
        if errors:
            return {}, [Diagnostic("EPE-CONTRACT-FIELDS", Severity.ERROR, f"契约字段无效: {errors[0].message}", entity_id=entity.id, path=entity.source.path)]
        if raw.get("id") != entity.id:
            return {}, [Diagnostic("EPE-CONTRACT-FIELDS", Severity.ERROR, "契约 ID 与实体 ID 不一致", entity_id=entity.id, path=entity.source.path)]
        jsonschema.Draft202012Validator.check_schema(raw["schema"])
        reference_error = _first_schema_reference_error(raw["schema"], path, root)
        if reference_error is not None:
            return {}, [Diagnostic("EPE-CONTRACT-REF", Severity.ERROR, reference_error, entity_id=entity.id, path=entity.source.path)]
    except ImportError:
        return {"supported": False, "contract_id": entity.id}, [Diagnostic("EPE-CONTRACT-UNSUPPORTED", Severity.WARNING, "未安装 jsonschema，契约仅完成基础结构检查", entity_id=entity.id, path=entity.source.path)]
    except jsonschema.SchemaError as exc:
        return {}, [Diagnostic("EPE-CONTRACT-SCHEMA", Severity.ERROR, f"JSON Schema 无效: {exc.message}", entity_id=entity.id, path=entity.source.path)]
    return {"supported": True, "contract_id": entity.id, "version": raw["version"]}, []


def _schema_pointer(value: Any, fragment: str) -> Any:
    """Resolve a JSON Pointer fragment without evaluating a schema."""
    if fragment in ("", "#"):
        return value
    if not fragment.startswith("#/"):
        raise ValueError("Schema $ref fragment 必须是 JSON Pointer")
    current = value
    for token in fragment[2:].split("/"):
        token = unquote(token).replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise ValueError(f"Schema $ref 指向不存在的片段: {fragment}")
    return current


def _first_schema_reference_error(schema: Any, source_path: Path, root: Path) -> str | None:
    """Check local, repository-relative JSON Schema references fail closed.

    ``jsonschema.Draft202012Validator.check_schema`` validates the shape of a
    schema but deliberately does not load external ``$ref`` targets. Contracts
    are repository authority, so unresolved or remote references must be
    rejected before a design can be considered valid.
    """
    visited: set[tuple[str, str]] = set()

    def visit(value: Any, document: Any, document_path: Path) -> str | None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref is not None:
                if not isinstance(ref, str) or not ref:
                    return "$ref 必须是非空字符串"
                parts = urlsplit(ref)
                if parts.scheme or parts.netloc or parts.query:
                    return f"Schema $ref 只能引用仓库内文件，拒绝: {ref}"
                target_text, _, fragment = ref.partition("#")
                target_path = document_path
                if target_text:
                    candidate = (document_path.parent / unquote(target_text)).resolve()
                    try:
                        relative = candidate.relative_to(root.resolve()).as_posix()
                        target_path = _design_source_path(root, relative)
                    except (OSError, ValueError) as exc:
                        return f"Schema $ref 路径无效: {ref} ({exc})"
                    if not target_path.is_file():
                        return f"Schema $ref 目标不存在: {ref}"
                    try:
                        document = json.loads(target_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                        return f"Schema $ref 目标不是有效 JSON: {ref} ({exc})"
                key = (str(target_path), "#" + fragment if fragment else "#")
                if key not in visited:
                    visited.add(key)
                    try:
                        target = _schema_pointer(document, "#" + fragment if fragment else "#")
                    except ValueError as exc:
                        return str(exc)
                    error = visit(target, document, target_path)
                    if error is not None:
                        return error
            for child in value.values():
                error = visit(child, document, document_path)
                if error is not None:
                    return error
        elif isinstance(value, list):
            for child in value:
                error = visit(child, document, document_path)
                if error is not None:
                    return error
        return None

    return visit(schema, schema, source_path.resolve())


def validate_approval_record(record: dict[str, Any]) -> list[Diagnostic]:
    required = {"schema_version", "id", "entity_id", "revision", "decision", "identity", "authorization_source", "timestamp", "risk_scope", "signature"}
    allowed = required | {"supersedes"}
    if not isinstance(record, dict) or required - record.keys() or record.keys() - allowed:
        return [Diagnostic("EPE-APPROVAL-FIELDS", Severity.ERROR, "审批记录缺少必填字段或包含未知字段")]
    identity = record.get("identity")
    risks = record.get("risk_scope")
    try:
        timestamp = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        timestamp_valid = timestamp.tzinfo is not None and timestamp.utcoffset().total_seconds() == 0
    except (AttributeError, ValueError, TypeError):
        timestamp_valid = False
    if (record.get("schema_version") != 1 or not isinstance(record.get("id"), str) or not re.fullmatch(r"APPROVAL-[A-Z0-9][A-Z0-9_-]*", record["id"])
            or not isinstance(record.get("entity_id"), str) or not record["entity_id"]
            or not isinstance(record.get("revision"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["revision"])
            or not isinstance(record.get("decision"), str) or record.get("decision") not in {"approved", "rejected", "revoked"}
            or not isinstance(identity, dict) or set(identity) != {"id"} or not isinstance(identity.get("id"), str) or not identity["id"]
            or not isinstance(record.get("authorization_source"), str) or not record["authorization_source"].strip()
            or not timestamp_valid or not isinstance(risks, list) or not risks or any(not isinstance(x, str) or x not in {"low", "medium", "high"} for x in risks)
            or not isinstance(record.get("signature"), str) or not record["signature"]):
        return [Diagnostic("EPE-APPROVAL-FIELDS", Severity.ERROR, "审批记录字段或格式非法")]
    if record["decision"] == "revoked" and (not isinstance(record.get("supersedes"), str) or not re.fullmatch(r"APPROVAL-[A-Z0-9][A-Z0-9_-]*", record["supersedes"])):
        return [Diagnostic("EPE-APPROVAL-REVOKES", Severity.ERROR, "撤销记录必须引用既有批准 ID")]
    if record["decision"] != "revoked" and record.get("supersedes") is not None:
        return [Diagnostic("EPE-APPROVAL-REVOKES", Severity.ERROR, "仅撤销记录可引用批准 ID")]
    return []


def assess_approval(revision: str, record: dict[str, Any], trusted_identity: dict[str, Any] | None = None, risk: str | None = None) -> tuple[str, list[Diagnostic]]:
    ds: list[Diagnostic] = []
    ds = validate_approval_record(record)
    if ds: return "invalid", ds
    if record.get("decision") not in {"approved", "rejected", "revoked"}: ds.append(Diagnostic("EPE-APPROVAL-DECISION", Severity.ERROR, "审批 decision 非法")); return "invalid", ds
    identity_value = record.get("identity")
    if not isinstance(identity_value, dict) or not record.get("authorization_source") or not identity_value.get("id"):
        return "invalid", [Diagnostic("EPE-APPROVAL-SOURCE", Severity.ERROR, "审批缺少 identity 或 authorization_source")]
    if record.get("revision") != revision: return "stale", [Diagnostic("EPE-APPROVAL-STALE", Severity.ERROR, "审批记录与当前设计指纹不匹配")]
    if record.get("decision") != "approved": return "not_approved", [Diagnostic("EPE-APPROVAL-NOT-APPROVED", Severity.ERROR, "审批记录不是 approved")]
    identity = trusted_identity or {}
    if not identity.get("trusted") or identity.get("id") != identity_value.get("id") or identity.get("source") != "ssh-signature":
        return "unknown", [Diagnostic("EPE-APPROVAL-IDENTITY", Severity.ERROR, "未提供可信审批身份来源")]
    if risk and (risk not in record["risk_scope"] or risk not in identity.get("risk_scope", [])):
        return "not_applicable", [Diagnostic("EPE-APPROVAL-RISK", Severity.ERROR, "审批不覆盖当前风险")]
    if risk == "high" and identity.get("kind") != "human":
        return "not_applicable", [Diagnostic("EPE-APPROVAL-HUMAN", Severity.ERROR, "高风险批准需要受信人类身份")]
    return "valid", ds
