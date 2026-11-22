from __future__ import annotations

import json
from pathlib import Path
from dataclasses import asdict
from typing import Any

from epe.adapters.protocol import AgentRequest, AgentResponse, validate_request
from epe.adapters.hosts.base import HostCapabilities
from epe.core.diagnostics import Diagnostic, Severity
from epe.adapters.process import run_process


class HermesHostAdapter:
    """JSON-line bridge for an explicitly configured Hermes host command.

    The bridge never infers identity or write isolation. The host must return a
    capability handshake before requests are accepted; missing configuration is
    an explicit unsupported state.
    """

    def __init__(self, command: list[str] | None = None, timeout: float = 10.0,
                 trusted_capabilities: bool = False, cwd: Path | None = None):
        self.command = command
        self.timeout = timeout
        self.trusted_capabilities = trusted_capabilities
        self.cwd = (cwd or Path.cwd()).resolve()
        self.capabilities = HostCapabilities("hermes", "1", False, False, False, False, (), "unsupported-unintegrated")

    def handshake(self) -> HostCapabilities:
        if not self.command:
            self.capabilities = HostCapabilities("hermes", "1", False, False, False, False, (), "unsupported-unintegrated")
            return self.capabilities
        response = self._call({"protocol_version": "1", "operation": "capabilities"})
        if response is None or response.get("status") != "ok" or not isinstance(response.get("capabilities"), dict):
            self.capabilities = HostCapabilities("hermes", "1", False, False, False, False, (), "handshake-failed")
            return self.capabilities
        value = response["capabilities"]
        if value.get("protocol_version", "1") != "1":
            self.capabilities = HostCapabilities("hermes", str(value.get("protocol_version")), False, False, False, False, (), "handshake-failed")
            return self.capabilities
        flags = ("trusted_identity", "write_isolation", "process_group_control", "cancellation")
        operations_value = value.get("operations", [])
        if (not isinstance(operations_value, list)
                or any(not isinstance(item, str) or not item for item in operations_value)
                or any(type(value.get(name, False)) is not bool for name in flags)):
            self.capabilities = HostCapabilities("hermes", "1", False, False, False, False, (), "handshake-failed")
            return self.capabilities
        operations = tuple(operations_value)
        status = "handshaken" if self.trusted_capabilities else "handshaken-untrusted"
        self.capabilities = HostCapabilities("hermes", str(value.get("protocol_version", "1")), bool(value.get("trusted_identity", False)) and self.trusted_capabilities, bool(value.get("write_isolation", False)) and self.trusted_capabilities, bool(value.get("process_group_control", False)), bool(value.get("cancellation", False)), operations, status)
        return self.capabilities

    def dispatch(self, request: AgentRequest) -> AgentResponse:
        shape = validate_request(request)
        if shape.decision == "blocked": return shape
        capabilities = self.handshake()
        if capabilities.status not in {"handshaken", "handshaken-untrusted"} or request.operation not in capabilities.operations or (not self.trusted_capabilities and request.operation != "verify"):
            diagnostic = Diagnostic("EPE-HOST-UNSUPPORTED", Severity.INFO, f"Hermes 未声明可执行操作: {request.operation}")
            return AgentResponse("unsupported", [diagnostic.message], [diagnostic], next_steps=["配置并验证 Hermes capability handshake"])
        response = self._call({"protocol_version": "1", "operation": request.operation, "request": asdict(request)})
        if not isinstance(response, dict) or response.get("status") != "ok":
            diagnostic = Diagnostic("EPE-HOST-RESPONSE", Severity.ERROR, "Hermes 返回无效或失败响应")
            return AgentResponse("error", [diagnostic.message], [diagnostic])
        value = response.get("response")
        if not isinstance(value, dict) or not isinstance(value.get("decision"), str) or value["decision"] not in {"accepted", "blocked", "unsupported", "error"}:
            diagnostic = Diagnostic("EPE-HOST-RESPONSE", Severity.ERROR, "Hermes 响应缺少有效 decision")
            return AgentResponse("error", [diagnostic.message], [diagnostic])
        if any(not isinstance(value.get(name, []), list)
               or any(not isinstance(item, str) for item in value.get(name, []))
               for name in ("reasons", "evidence_ids", "next_steps")):
            diagnostic = Diagnostic("EPE-HOST-RESPONSE", Severity.ERROR, "Hermes 响应字段必须为字符串数组")
            return AgentResponse("error", [diagnostic.message], [diagnostic])
        return AgentResponse(str(value["decision"]), list(value.get("reasons", [])), [], list(value.get("evidence_ids", [])), list(value.get("next_steps", [])))

    def _call(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.command or not isinstance(self.command, list) or not self.command or not all(isinstance(item, str) and item for item in self.command): return None
        process = run_process(self.command, self.cwd, timeout=self.timeout, max_output_bytes=1024 * 1024, input_data=(json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        if (process.returncode != 0 or process.timed_out or process.cancelled
                or process.stdout_truncated or process.stderr_truncated or process.stdin_incomplete):
            return None
        try:
            value = json.loads(process.stdout)
        except (TypeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None
