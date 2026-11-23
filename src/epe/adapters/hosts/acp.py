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


class ACPSessionClosed(ACPProtocolError):
    """The caller closed the ACP session while an operation was pending."""


def _terminate_process(process: subprocess.Popen, *, force: bool) -> None:
    """Terminate the ACP child without assuming process groups on non-POSIX hosts."""
    try:
        if os.name == "posix":
            # The group may outlive its leader; still signal it after the direct
            # child exits so descendants holding protocol pipes are cleaned up.
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
        elif process.poll() is not None:
            return
        elif force:
            process.kill()
        else:
            process.terminate()
    except (OSError, ProcessLookupError):
        pass


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
        self._request_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._reader_done = threading.Event()
        self._reader_done.set()
        self._active_readers = 0
        self._wakeup_read, self._wakeup_write = os.pipe()
        self.session_id = ""
        self._closed = False

    def close(self) -> None:
        """Close the session and wake any in-flight reader without racing selector use."""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            process = self._process
            selector = self._selector
            # Keep the wakeup descriptors alive until the byte is sent.
            try:
                os.write(self._wakeup_write, b"x")
            except OSError:
                pass

        # Closing the protocol streams lets an in-flight selector/read observe EOF.
        # The state flag is checked before and after every blocking operation, so a
        # caller-side close is reported as ACPSessionClosed rather than a timeout.
        try:
            _terminate_process(process, force=True)
        finally:
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
            try:
                process.wait(timeout=max(1.0, min(self._timeout, 5.0)))
            except (OSError, subprocess.TimeoutExpired):
                pass

        # Do not close a selector while another thread is inside select().  The
        # final reader closes it after observing the closed state; a short wait
        # handles the usual EOF path without making close unbounded.
        self._reader_done.wait(timeout=max(1.0, min(self._timeout, 5.0)))
        with self._state_lock:
            if self._active_readers == 0:
                self._close_selector(selector)

    def __enter__(self) -> "HermesACPSession":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def prompt(self, text: str) -> dict[str, Any]:
        """Send one text prompt; the result is model output, never a gate decision."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("session is closed or prompt is empty")
        self._ensure_open()
        result = self._request("session/prompt", {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": text}],
        })
        if not isinstance(result, dict):
            self.close()
            raise ACPProtocolError("ACP session/prompt response is not an object")
        return result

    def cancel(self) -> None:
        """Send ACP's session/cancel notification for the current operation."""
        self._ensure_open()
        if not self.session_id:
            raise ValueError("session is closed or has no session ID")
        payload = {"jsonrpc": "2.0", "method": "session/cancel",
                   "params": {"sessionId": self.session_id}}
        try:
            self._send(payload)
        except (TimeoutError, ACPProtocolError, OSError):
            self.close()
            raise

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        if not self._request_lock.acquire(blocking=False):
            raise ACPProtocolError("concurrent ACP requests are not supported")
        try:
            self._ensure_open()
            deadline = time.monotonic() + self._timeout
            request_id = self._next_id
            self._next_id += 1
            payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
            self._send(payload, deadline)
            while True:
                message = self._read_message(deadline)
                if "id" not in message and isinstance(message.get("method"), str):
                    continue
                if type(message.get("id")) is not int or message["id"] != request_id:
                    raise ACPProtocolError("unexpected ACP response ID")
                if "error" in message:
                    raise ACPProtocolError("ACP request failed")
                return message.get("result")
        except (TimeoutError, ACPProtocolError, OSError):
            self.close()
            raise
        finally:
            self._request_lock.release()

    def _ensure_open(self) -> None:
        with self._state_lock:
            if self._closed:
                raise ACPSessionClosed("ACP session is closed")

    def _close_selector(self, selector: selectors.BaseSelector) -> None:
        try:
            selector.close()
        except (OSError, ValueError):
            pass
        for fd_name in ("_wakeup_read", "_wakeup_write"):
            fd = getattr(self, fd_name)
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_name, None)

    def _send(self, payload: dict[str, Any], deadline: float | None = None) -> None:
        self._ensure_open()
        deadline = deadline if deadline is not None else time.monotonic() + self._timeout
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        if not self._write_lock.acquire(timeout=max(0, deadline - time.monotonic())):
            raise TimeoutError("ACP request timed out while waiting to write")
        try:
            self._ensure_open()
            with self._state_lock:
                self._ensure_open()
                self._active_readers += 1
                self._reader_done.clear()
            try:
                with selectors.DefaultSelector() as writer:
                    writer.register(self._process.stdin, selectors.EVENT_WRITE)
                    writer.register(self._wakeup_read, selectors.EVENT_READ)
                    remaining = memoryview(encoded)
                    while remaining:
                        self._ensure_open()
                        wait = deadline - time.monotonic()
                        if wait <= 0:
                            raise TimeoutError("ACP request timed out while writing")
                        ready = writer.select(wait)
                        if not ready:
                            raise TimeoutError("ACP request timed out while writing")
                        self._ensure_open()
                        if any(key.fd == self._wakeup_read for key, _ in ready):
                            self._ensure_open()
                        if any(key.fileobj is self._process.stdin for key, _ in ready):
                            try:
                                written = os.write(self._process.stdin.fileno(), remaining)
                            except BlockingIOError:
                                continue
                            if not written:
                                raise OSError("incomplete ACP request")
                            remaining = remaining[written:]
            except TimeoutError:
                raise
            except (OSError, ValueError) as exc:
                if self._closed:
                    raise ACPSessionClosed("ACP session is closed") from exc
                raise ACPProtocolError("ACP request could not be written") from exc
            finally:
                self._operation_finished()
        finally:
            self._write_lock.release()

    def _operation_finished(self) -> None:
        with self._state_lock:
            self._active_readers -= 1
            if self._active_readers == 0:
                self._reader_done.set()
                if self._closed:
                    self._close_selector(self._selector)

    def _read_message(self, deadline: float) -> dict[str, Any]:
        with self._state_lock:
            if self._closed:
                raise ACPSessionClosed("ACP session is closed")
            self._active_readers += 1
            self._reader_done.clear()
        try:
            while True:
                self._ensure_open()
                if time.monotonic() >= deadline:
                    raise TimeoutError("ACP request timed out")
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
                if remaining <= 0:
                    raise TimeoutError("ACP request timed out")
                try:
                    ready = self._selector.select(remaining)
                except (OSError, ValueError) as exc:
                    if self._closed:
                        raise ACPSessionClosed("ACP session is closed") from exc
                    raise
                if not ready:
                    raise TimeoutError("ACP request timed out")
                if any(key.fd == self._wakeup_read for key, _ in ready):
                    self._ensure_open()
                self._ensure_open()
                try:
                    stdout_fd = self._process.stdout.fileno()
                    if not any(key.fd == stdout_fd for key, _ in ready):
                        continue
                    chunk = os.read(stdout_fd, min(65536, self._output_limit + 1 - self._consumed))
                except (OSError, ValueError) as exc:
                    if self._closed:
                        raise ACPSessionClosed("ACP session is closed") from exc
                    raise ACPProtocolError("ACP stream could not be read") from exc
                if not chunk:
                    if self._closed:
                        raise ACPSessionClosed("ACP session is closed")
                    raise ACPProtocolError("ACP stream closed before response")
                self._consumed += len(chunk)
                if self._consumed > self._output_limit:
                    raise ACPProtocolError("ACP output limit exceeded")
                self._pending += chunk
        finally:
            self._operation_finished()


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
        if os.name != "posix":
            raise OSError("ACP session transport requires POSIX pipe selectors")
        process = subprocess.Popen(
            self.command, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0, start_new_session=os.name == "posix",
        )
        selector = None
        session = None
        try:
            selector = selectors.DefaultSelector()
            session = HermesACPSession(process, selector, self.timeout, self.output_limit)
            os.set_blocking(process.stdin.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            selector.register(session._wakeup_read, selectors.EVENT_READ)
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
            if session is not None:
                session.close()
            else:
                if selector is not None:
                    selector.close()
                _terminate_process(process, force=True)
                for stream in (process.stdin, process.stdout):
                    if stream is not None:
                        stream.close()
                try:
                    process.wait(timeout=max(1.0, min(self.timeout, 5.0)))
                except subprocess.TimeoutExpired:
                    pass
            raise

    def _request(self, session: HermesACPSession, method: str, params: dict[str, Any], request_id: int) -> Any:
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        deadline = time.monotonic() + session._timeout
        session._send(payload, deadline)
        while True:
            message = session._read_message(deadline)
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
