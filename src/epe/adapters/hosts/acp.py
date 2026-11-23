"""Bounded Hermes ACP initialization transport.

This adapter intentionally stops at protocol initialization. A successful
handshake does not grant identity, write isolation, cancellation, or EPE
workflow permissions.
"""

from __future__ import annotations

import json
import math
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path

from epe.adapters.hosts.base import HostCapabilities


class HermesACPAdapter:
    """Probe a long-lived Hermes ACP JSON-RPC process without running a task."""

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
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": 1,
            "clientCapabilities": {},
            "clientInfo": {"name": "btae-epe", "version": "0.1"},
        }}
        process = subprocess.Popen(
            self.command, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        selector = selectors.DefaultSelector()
        try:
            process.stdin.write((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
            process.stdin.flush()
            selector.register(process.stdout, selectors.EVENT_READ)
            message = self._read_response(process, selector)
            result = message.get("result") if isinstance(message, dict) else None
            info = result.get("agentInfo") if isinstance(result, dict) else None
            valid = (
                isinstance(message, dict)
                and message.get("jsonrpc") == "2.0"
                and type(message.get("id")) is int and message["id"] == 1
                and isinstance(result, dict)
                and type(result.get("protocolVersion")) is int
                and result["protocolVersion"] == 1
                and isinstance(info, dict)
                and isinstance(info.get("name"), str) and bool(info["name"])
            )
            if not valid:
                return HostCapabilities("hermes", "1", False, False, True, False, (), "handshake-failed")
            return HostCapabilities("hermes", "1", False, False, True, False, (), "handshaken-untrusted")
        except (OSError, UnicodeError, json.JSONDecodeError, TimeoutError, ValueError):
            return HostCapabilities("hermes", "1", False, False, True, False, (), "handshake-failed")
        finally:
            selector.close()
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdin.close()
            process.stdout.close()

    def _read_response(self, process: subprocess.Popen, selector: selectors.BaseSelector) -> dict:
        deadline = time.monotonic() + self.timeout
        pending = b""
        consumed = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("ACP initialize timed out")
            chunk = os.read(process.stdout.fileno(), min(65536, self.output_limit + 1 - consumed))
            if not chunk:
                raise ValueError("ACP stream closed before initialize response")
            consumed += len(chunk)
            if consumed > self.output_limit:
                raise ValueError("ACP output limit exceeded")
            pending += chunk
            while b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                message = json.loads(line)
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    raise ValueError("invalid ACP message")
                if "id" not in message and isinstance(message.get("method"), str):
                    continue
                return message
