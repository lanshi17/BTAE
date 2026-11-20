from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from epe.adapters.protocol import AgentRequest, AgentResponse, validate_request
from epe.core.diagnostics import Diagnostic, Severity


@dataclass(frozen=True)
class HostCapabilities:
    host_id: str
    protocol_version: str
    trusted_identity: bool
    write_isolation: bool
    process_group_control: bool
    cancellation: bool
    operations: tuple[str, ...]
    status: str = "measured"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def capability_matrix() -> list[HostCapabilities]:
    return [
        HostCapabilities("local-cli", "1", False, False, True, True, ("verify",), "measured"),
        HostCapabilities("hermes", "1", False, False, False, False, (), "unsupported-unintegrated"),
    ]


class LocalHostAdapter:
    """A conservative local adapter: it can report capabilities and reject writes."""

    capabilities = HostCapabilities("local-cli", "1", False, False, True, True, ("verify",), "measured")

    def dispatch(self, request: AgentRequest) -> AgentResponse:
        shape = validate_request(request)
        if shape.decision == "blocked":
            return shape
        if request.operation != "verify":
            diagnostic = Diagnostic("EPE-HOST-UNSUPPORTED", Severity.INFO, f"local-cli 不支持宿主操作: {request.operation}")
            return AgentResponse("unsupported", [diagnostic.message], [diagnostic], next_steps=["使用已测量的宿主适配器，或通过 CLI 执行只读检查"])
        if not self.capabilities.process_group_control:
            diagnostic = Diagnostic("EPE-HOST-CAPABILITY", Severity.ERROR, "宿主没有进程组控制能力")
            return AgentResponse("blocked", [diagnostic.message], [diagnostic])
        return AgentResponse("accepted", reasons=["请求形状和本地进程控制能力可用"], next_steps=["由应用层根据 Task/ChangeSet 形成已授权 ExecutionPlan"])
