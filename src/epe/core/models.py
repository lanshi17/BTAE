from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Mapping


class ResultStatus(str, Enum):
    PASSED = "passed"
    BLOCKED = "blocked"
    ERROR = "error"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class SourceLocation:
    path: str
    line: int | None = None
    column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Entity:
    schema_version: int
    id: str
    type: str
    name: str
    source: SourceLocation
    design_status: str | None = None
    implementation_status: str | None = None
    verification_status: str | None = None
    implementation: list[dict[str, Any]] = field(default_factory=list)
    verification: list[dict[str, Any]] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)
    lifecycle: str = "active"
    relations: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "schema_version": self.schema_version,
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "source": self.source.to_dict(),
            "design_status": self.design_status,
            "implementation_status": self.implementation_status,
            "verification_status": self.verification_status,
            "implementation": self.implementation,
            "verification": self.verification,
            "contracts": self.contracts,
            "relations": self.relations,
            "lifecycle": self.lifecycle,
        }
        if self.type == "Contract":
            for key in ("version", "schema"):
                if key in self.raw:
                    d[key] = self.raw[key]
        return {k: v for k, v in d.items() if v is not None}


@dataclass(frozen=True)
class Relation:
    from_id: str
    to_id: str
    relation: str
    origin: dict[str, Any]
    confidence: float
    verified: bool
    verification: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "from": self.from_id,
            "to": self.to_id,
            "relation": self.relation,
            "origin": self.origin,
            "confidence": self.confidence,
            "verified": self.verified,
        }
        if self.verification is not None:
            d["verification"] = self.verification
        return d


@dataclass
class Task:
    id: str
    type: str
    objective: str
    acceptance: list[str]
    risk: str
    target_entities: list[str]
    changeset: str | None = None
    status: str = "planned"
    revision: int = 1
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        value = dict(self.raw)
        value.update({
            "schema_version": 1,
            "id": self.id,
            "type": self.type,
            "objective": self.objective,
            "acceptance": self.acceptance,
            "risk": self.risk,
            "target_entities": self.target_entities,
            "changeset": self.changeset,
            "status": self.status,
            "revision": self.revision,
        })
        return value


@dataclass
class ChangeSet:
    id: str
    task_id: str
    owner: str
    affected_entities: list[str]
    write_scope: list[str]
    protected: list[str]
    dependencies: list[dict[str, Any]]
    baseline_manifest: str | None = None
    status: str = "planned"
    revision: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.id,
            "task": self.task_id,
            "owner": self.owner,
            "affected_entities": self.affected_entities,
            "write_scope": self.write_scope,
            "protected": self.protected,
            "dependencies": self.dependencies,
            "baseline_manifest": self.baseline_manifest,
            "status": self.status,
            "revision": self.revision,
        }


@dataclass
class Approval:
    id: str
    entity_id: str
    revision: str
    decision: str
    identity: dict[str, Any]
    authorization_source: str
    timestamp: str
    risk_scope: list[str]
    supersedes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"schema_version": 1, **asdict(self)}
        return d


@dataclass
class Evidence:
    id: str
    run_id: str
    task_id: str | None
    changeset_id: str | None
    target_entities: list[str]
    checker: str
    checker_version: str
    command: list[str]
    cwd: str
    started_at: str
    finished_at: str
    exit_code: int | None
    termination_reason: str | None
    result: str
    validity: str
    input_manifest: dict[str, Any]
    artifacts: list[dict[str, Any]]
    environment: dict[str, Any]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(frozen=True)
class InputManifest:
    entries: tuple[tuple[str, str], ...]
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [{"path": p, "sha256": h} for p, h in self.entries], "digest": self.digest}


@dataclass
class CommandResult:
    command: str
    status: ResultStatus | str
    diagnostics: list[Any] = field(default_factory=list)
    data: Any = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        status = self.status.value if isinstance(self.status, ResultStatus) else self.status
        return {
            "schema_version": self.schema_version,
            "command": self.command,
            "status": status,
            "diagnostics": [d.to_dict() if hasattr(d, "to_dict") else d for d in self.diagnostics],
            "data": self.data,
            "evidence_ids": self.evidence_ids,
        }
