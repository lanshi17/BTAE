from __future__ import annotations

import math
import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from epe.adapters.clock import SystemClock


DEFAULT_MAX_OUTPUT_BYTES = 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024


@dataclass
class ProcessResult:
    argv: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    termination_reason: str | None = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    cancelled: bool = False
    stdin_incomplete: bool = False


def _signal_process_tree(proc: subprocess.Popen, sig: signal.Signals) -> None:
    try:
        if os.name == "posix":
            os.killpg(proc.pid, sig)
        elif sig == signal.SIGTERM:
            proc.terminate()
        else:
            proc.kill()
    except (OSError, ProcessLookupError):
        pass


def run_process(
    argv: Sequence[str],
    cwd: Path,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
    *,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    termination_grace: float = 1.0,
    cancel_event: threading.Event | None = None,
    input_data: bytes | None = None,
) -> ProcessResult:
    """Run argv without a shell, retaining bounded output and reaping its process group.

    Output pipes are always drained, even after the retention cap is reached, so a
    verbose child cannot block on a full pipe or grow the parent's buffers without
    limit. Process-group termination is enforced on POSIX. Other platforms only
    provide direct-child termination and should not claim group isolation.
    """
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes < 0:
        raise ValueError("max_output_bytes must be a non-negative integer")
    if not math.isfinite(termination_grace) or termination_grace < 0:
        raise ValueError("termination_grace must be a finite non-negative number")
    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("timeout must be a finite positive number or None")

    command = list(argv)
    clock = SystemClock()
    started = clock.monotonic()
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
            start_new_session=os.name == "posix",
            env=dict(env) if env is not None else None,
        )
    except OSError as exc:
        return ProcessResult(command, None, "", str(exc), clock.monotonic() - started, termination_reason="start_error")

    if input_data is not None and not isinstance(input_data, bytes):
        _signal_process_tree(proc, signal.SIGKILL)
        proc.wait()
        raise TypeError("input_data must be bytes or None")
    input_state = {"sent": 0, "failed": False}
    writer: threading.Thread | None = None
    if input_data is not None:
        def write_input() -> None:
            try:
                assert proc.stdin is not None
                view = memoryview(input_data)
                while view:
                    written = proc.stdin.write(view)
                    if written is None or written <= 0:
                        input_state["failed"] = True
                        break
                    input_state["sent"] += written
                    view = view[written:]
            except (OSError, ValueError):
                input_state["failed"] = True
            finally:
                try:
                    proc.stdin.close()
                except (OSError, ValueError):
                    pass
        writer = threading.Thread(target=write_input, daemon=True, name=f"epe-{proc.pid}-stdin")

    captured = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = {"stdout": False, "stderr": False}

    def drain(name: str, stream) -> None:
        target = captured[name]
        try:
            while True:
                chunk = stream.read(_READ_CHUNK_BYTES)
                if not chunk:
                    return
                remaining = max_output_bytes - len(target)
                if remaining > 0:
                    target.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[name] = True
        except (OSError, ValueError):
            # A force-closed pipe is already represented by its truncation status
            # or by the process termination result.
            return

    readers = [
        threading.Thread(target=drain, args=("stdout", proc.stdout), daemon=True, name=f"epe-{proc.pid}-stdout"),
        threading.Thread(target=drain, args=("stderr", proc.stderr), daemon=True, name=f"epe-{proc.pid}-stderr"),
    ]
    for reader in readers:
        reader.start()
    if writer is not None:
        writer.start()

    deadline = started + timeout if timeout is not None else None
    termination_reason: str | None = None
    terminate_at: float | None = None
    kill_sent = False
    force_close_at: float | None = None
    while proc.poll() is None or any(reader.is_alive() for reader in readers) or (writer is not None and writer.is_alive()):
        now = clock.monotonic()
        if termination_reason is None:
            if cancel_event is not None and cancel_event.is_set():
                termination_reason = "cancelled"
            elif deadline is not None and now >= deadline:
                termination_reason = "timeout"
            if termination_reason is not None:
                _signal_process_tree(proc, signal.SIGTERM)
                terminate_at = now + termination_grace
        elif not kill_sent and terminate_at is not None and now >= terminate_at:
            _signal_process_tree(proc, signal.SIGKILL)
            kill_sent = True
            force_close_at = now + max(termination_grace, 1.0)

        if kill_sent and force_close_at is not None and now >= force_close_at:
            # A process that escaped the process group must not hold this caller
            # forever. Closing parent-side pipes bounds shutdown while preserving
            # an explicit truncation signal for the incomplete stream.
            for name, stream in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                if any(reader.is_alive() and reader.name.endswith(name) for reader in readers):
                    truncated[name] = True
                    try:
                        stream.close()
                    except OSError:
                        pass
            break
        time.sleep(0.02)

    for reader in readers:
        reader.join(timeout=max(termination_grace, 1.0))
    if writer is not None:
        writer.join(timeout=max(termination_grace, 1.0))
    if proc.poll() is None:
        _signal_process_tree(proc, signal.SIGKILL)
    try:
        returncode = proc.wait(timeout=max(termination_grace, 1.0))
    except subprocess.TimeoutExpired:
        # Keep shutdown bounded even if the OS cannot promptly reap a killed child.
        returncode = proc.poll()
    for stream in (proc.stdout, proc.stderr):
        try:
            stream.close()
        except OSError:
            pass

    return ProcessResult(
        command,
        returncode,
        captured["stdout"].decode("utf-8", errors="replace"),
        captured["stderr"].decode("utf-8", errors="replace"),
        clock.monotonic() - started,
        timed_out=termination_reason == "timeout",
        termination_reason=termination_reason,
        stdout_truncated=truncated["stdout"],
        stderr_truncated=truncated["stderr"],
        cancelled=termination_reason == "cancelled",
        stdin_incomplete=input_data is not None and (input_state["failed"] or input_state["sent"] != len(input_data)),
    )
