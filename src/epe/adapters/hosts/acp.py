"""Bounded Hermes ACP initialization and session transport."""

from __future__ import annotations

import json
import math
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from epe.adapters.hosts.base import HostCapabilities


class ACPProtocolError(ValueError):
    """The ACP peer returned an invalid or failed JSON-RPC message."""


class HermesACPSession:
    """An explicitly opened, prompt-free ACP session."""

    def __init__(self, process: subprocess.Popen, selector: selectors.BaseSelector,
                 timeout: float, output_limit: int):
        self._process = process
        self._selector = selector
        self._timeout = timeout
        self._output_limit = output_limit
        self._pending = b""
        self._consumed = 0
        self.session_id = ""
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._selector.close()
        try:
            os.killpg(self._process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self._process.wait()
        self._process.stdin.close()
        self._process.stdout.close()

    def __enter__(self) -> "HermesACPSession":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class HermesACPAdapter:
    """Probe Hermes ACP and optionally open an empty session."""

    def __init__(self, command: list[str], cwd: Path, timeout: float = 10.0,
                 output_limit: int = 1024 * 1024):
        if (not command or not all(isinstance(arg, str) and arg for arg in command)
                or not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
                or not math.isfinite(timeout) or timeout <= 0
                or type(output_limit) is not int or output_limit <= 0):
            raise ValueError("invalid ACP command, timeout, or output limit")
        self.command = list(command)
        self.cwd = cwd.resolve()
        self.timeout = float(timeout)
        self.output_limit = output_limit

    def handshake(self) -> HostCapabilities:
        try:
            with self._open_session(open_empty=False):
                pass
        except (OSError, UnicodeError, json.JSONDecodeError, TimeoutError, ValueError):
            return HostCapabilities("hermes", "1", False, False, True, False, (), "handshake-failed")
        return HostCapabilities("hermes", "1", False, False, True, False, (), "handshaken-untrusted")

    def open_session(self, cwd: Path | None = None) -> HermesACPSession:
        """Open a session with no MCP servers; caller must close the result."""
        return self._open_session(open_empty=True, cwd=cwd)

    def _open_session(self, open_empty: bool, cwd: Path | None = None) -> HermesACPSession:
        process = subprocess.Popen(
            self.command, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        selector = selectors.DefaultSelector()
        session = HermesACPSession(process, selector, self.timeout, self.output_limit)
        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            initialized = self._request(session, "initialize", {
                "protocolVersion": 1,
                "clientCapabilities": {},
                "clientInfo": {"name": "btae-epe", "version": "0.1"},
            }, request_id=1)
            self._validate_initialize(initialized)
            if not open_empty:
                return session
            value = self._request(session, "session/new", {
                "cwd": str((cwd or self.cwd).resolve()), "mcpServers": [],
            }, request_id=2)
            if not isinstance(value, dict) or not isinstance(value.get("sessionId"), str) or not value["sessionId"]:
                raise ACPProtocolError("ACP session/new response lacks sessionId")
            session.session_id = value["sessionId"]
            return session
        except BaseException:
            session.close()
            raise

    def _request(self, session: HermesACPSession, method: str, params: dict[str, Any], request_id: int) -> Any:
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        session._process.stdin.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
        session._process.stdin.flush()
        while True:
            message = self._read_message(session)
            if "id" not in message and isinstance(message.get("method"), str):
                continue
            if type(message.get("id")) is not int or message["id"] != request_id:
                raise ACPProtocolError("unexpected ACP response ID")
            if "error" in message:
                raise ACPProtocolError("ACP request failed")
            return message.get("result")

    def _read_message(self, session: HermesACPSession) -> dict[str, Any]:
        deadline = time.monotonic() + session._timeout
        while True:
            while b"\n" in session._pending:
                line, session._pending = session._pending.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise ACPProtocolError("invalid ACP JSON") from exc
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise ACPProtocolError("invalid ACP message")
                return message
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not session._selector.select(remaining):
                raise TimeoutError("ACP request timed out")
            chunk = os.read(session._process.stdout.fileno(), min(65536, session._output_limit + 1 - session._consumed))
            if not chunk:
                raise ACPProtocolError("ACP stream closed before response")
            session._consumed += len(chunk)
            if session._consumed > session._output_limit:
                raise ACPProtocolError("ACP output limit exceeded")
            session._pending += chunk

    @staticmethod
    def _validate_initialize(value: Any) -> None:
        if not isinstance(value, dict) or type(value.get("protocolVersion")) is not int or value["protocolVersion"] != 1:
            raise ACPProtocolError("ACP protocol version mismatch")
        info = value.get("agentInfo")
        if not isinstance(info, dict) or not isinstance(info.get("name"), str) or not info["name"]:
            raise ACPProtocolError("ACP agent information missing")
