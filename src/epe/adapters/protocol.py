from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import re
from pathlib import PurePosixPath

from epe.core.diagnostics import Diagnostic, Severity


@dataclass(frozen=True)
class AgentRequest:
    request_id: str
    operation: str
    task_id: str
    changeset_id: str | None
    target_entities: tuple[str, ...]
    expected_design_revision: str | None
    write_scope: tuple[str, ...]
    parameters: dict[str, Any] = field(default_factory=dict)
    trusted_identity: dict[str, Any] | None = None


@dataclass
class AgentResponse:
    decision: str
    reasons: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"decision": self.decision, "reasons": self.reasons, "diagnostics": [d.to_dict() for d in self.diagnostics], "evidence_ids": self.evidence_ids, "next_steps": self.next_steps}


def validate_request(request: AgentRequest) -> AgentResponse:
    diagnostics: list[Diagnostic] = []
    if not isinstance(request, AgentRequest):
        return AgentResponse("blocked", ["请求对象类型无效"], [Diagnostic("EPE-AGENT-REQUEST", Severity.ERROR, "请求对象类型无效")])
    if not isinstance(request.request_id, str) or not request.request_id.strip():
        diagnostics.append(Diagnostic("EPE-AGENT-REQUEST-ID", Severity.ERROR, "request_id 不能为空"))
    protocol_version = getattr(request, "protocol_version", "1")
    if protocol_version != "1":
        diagnostics.append(Diagnostic("EPE-AGENT-PROTOCOL", Severity.ERROR, "不支持的宿主协议版本"))
    if request.operation not in {"start_implementation", "verify", "finalize"}:
        diagnostics.append(Diagnostic("EPE-AGENT-OPERATION", Severity.ERROR, f"不支持的宿主操作: {request.operation}"))
    if not isinstance(request.task_id, str) or not re.fullmatch(r"TASK-[A-Z0-9][A-Z0-9_-]*", request.task_id):
        diagnostics.append(Diagnostic("EPE-AGENT-TASK", Severity.ERROR, "task_id 格式非法"))
    if request.changeset_id is not None and (not isinstance(request.changeset_id, str) or not re.fullmatch(r"CHANGE-[A-Z0-9][A-Z0-9_-]*", request.changeset_id)):
        diagnostics.append(Diagnostic("EPE-AGENT-CHANGESET", Severity.ERROR, "changeset_id 格式非法"))
    if (not isinstance(request.target_entities, tuple) or not request.target_entities
            or not all(isinstance(value, str) and value for value in request.target_entities)):
        diagnostics.append(Diagnostic("EPE-AGENT-TARGET", Severity.ERROR, "target_entities 必须为非空字符串元组"))
    if request.expected_design_revision is not None and (not isinstance(request.expected_design_revision, str) or re.fullmatch(r"[0-9a-fA-F]{64}", request.expected_design_revision) is None):
        diagnostics.append(Diagnostic("EPE-AGENT-DESIGN-REVISION", Severity.ERROR, "expected_design_revision 必须为 64 位十六进制摘要"))
    if (not isinstance(request.write_scope, tuple)
            or any(not isinstance(value, str) or not value or value.startswith("/") or ".." in PurePosixPath(value).parts or "\\" in value for value in request.write_scope)):
        diagnostics.append(Diagnostic("EPE-AGENT-SCOPE", Severity.ERROR, "write_scope 必须为仓库相对 glob 元组"))
    if request.operation == "start_implementation" and not request.write_scope:
        diagnostics.append(Diagnostic("EPE-AGENT-SCOPE", Severity.ERROR, "start_implementation 必须声明 write_scope"))
    if not isinstance(request.parameters, dict):
        diagnostics.append(Diagnostic("EPE-AGENT-PARAMETERS", Severity.ERROR, "parameters 必须为对象"))
    if request.trusted_identity is None or not isinstance(request.trusted_identity, dict) or not isinstance(request.trusted_identity.get("source"), str) or not request.trusted_identity.get("source"):
        diagnostics.append(Diagnostic("EPE-AGENT-IDENTITY", Severity.ERROR, "宿主身份必须来自可信通道"))
    return AgentResponse("blocked" if diagnostics else "accepted", [d.message for d in diagnostics], diagnostics, next_steps=["补齐请求字段并从宿主可信通道注入身份"] if diagnostics else [])
