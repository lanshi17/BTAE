"""Bounded Hermes ACP initialization and session transport."""

from __future__ import annotations

import json
import math
import os
import selectors
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from epe.adapters.hosts.base import HostCapabilities


class ACPProtocolError(ValueError):
    """The ACP peer returned an invalid or failed JSON-RPC message."""


class HermesACPSession:
    """An explicitly opened ACP session with text-only prompt support."""

    def __init__(self, process: subprocess.Popen, selector: selectors.BaseSelector,
                 timeout: float, output_limit: int):
        self._process = process
        self._selector = selector
        self._timeout = timeout
        self._output_limit = output_limit
        self._pending = b""
        self._consumed = 0
        self._next_id = 3
        self._write_lock = threading.Lock()
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

    def prompt(self, text: str) -> dict[str, Any]:
        """Send one text prompt; the result is model output, never a gate decision."""
        if self._closed or not isinstance(text, str) or not text.strip():
            raise ValueError("session is closed or prompt is empty")
        result = self._request("session/prompt", {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": text}],
        })
        if not isinstance(result, dict):
            raise ACPProtocolError("ACP session/prompt response is not an object")
        return result

    def cancel(self) -> None:
        """Send ACP's session/cancel notification for the current operation."""
        if self._closed or not self.session_id:
            raise ValueError("session is closed or has no session ID")
        payload = {"jsonrpc": "2.0", "method": "session/cancel",
                   "params": {"sessionId": self.session_id}}
        with self._write_lock:
            self._process.stdin.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            self._process.stdin.flush()

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        request_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        with self._write_lock:
            self._process.stdin.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            self._process.stdin.flush()
        while True:
            message = self._read_message()
            if "id" not in message and isinstance(message.get("method"), str):
                continue
            if type(message.get("id")) is not int or message["id"] != request_id:
                raise ACPProtocolError("unexpected ACP response ID")
            if "error" in message:
                raise ACPProtocolError("ACP request failed")
            return message.get("result")

    def _read_message(self) -> dict[str, Any]:
        deadline = time.monotonic() + self._timeout
        while True:
            while b"\n" in self._pending:
                line, self._pending = self._pending.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise ACPProtocolError("invalid ACP JSON") from exc
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise ACPProtocolError("invalid ACP message")
                return message
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self._selector.select(remaining):
                raise TimeoutError("ACP request timed out")
            chunk = os.read(self._process.stdout.fileno(), min(65536, self._output_limit + 1 - self._consumed))
            if not chunk:
                raise ACPProtocolError("ACP stream closed before response")
            self._consumed += len(chunk)
            if self._consumed > self._output_limit:
                raise ACPProtocolError("ACP output limit exceeded")
            self._pending += chunk


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
            message = session._read_message()
            if "id" not in message and isinstance(message.get("method"), str):
                continue
            if type(message.get("id")) is not int or message["id"] != request_id:
                raise ACPProtocolError("unexpected ACP response ID")
            if "error" in message:
                raise ACPProtocolError("ACP request failed")
            return message.get("result")

    @staticmethod
    def _validate_initialize(value: Any) -> None:
        if not isinstance(value, dict) or type(value.get("protocolVersion")) is not int or value["protocolVersion"] != 1:
            raise ACPProtocolError("ACP protocol version mismatch")
        info = value.get("agentInfo")
        if not isinstance(info, dict) or not isinstance(info.get("name"), str) or not info["name"]:
            raise ACPProtocolError("ACP agent information missing")
