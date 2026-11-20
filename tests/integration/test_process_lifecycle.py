from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from threading import Event, Thread

from epe.adapters.process import run_process


def _running_process(pid: int) -> bool:
    proc = Path(f"/proc/{pid}/stat")
    try:
        return proc.read_text().split()[2] != "Z"
    except (OSError, IndexError):
        return False


def test_timeout_terminates_process_group_descendants(tmp_path):
    pid_file = tmp_path / "child.pid"
    marker = tmp_path / "child-survived"
    child = "import pathlib,time; time.sleep(1.2); pathlib.Path(%r).write_text('alive')" % str(marker)
    parent = "import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-c',%r]); pathlib.Path(%r).write_text(str(p.pid)); time.sleep(30)" % (child, str(pid_file))
    result = run_process([sys.executable, "-c", parent], tmp_path, timeout=0.3, termination_grace=0.1)
    assert result.timed_out and result.termination_reason == "timeout"
    child_pid = int(pid_file.read_text())
    deadline = time.monotonic() + 2
    while _running_process(child_pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _running_process(child_pid)
    assert not marker.exists()


def test_cancellation_terminates_process_group(tmp_path):
    cancelled = Event()
    timer = Thread(target=lambda: (time.sleep(0.2), cancelled.set()), daemon=True)
    timer.start()
    result = run_process([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path, cancel_event=cancelled, termination_grace=0.1)
    assert result.cancelled and result.termination_reason == "cancelled"
    assert result.returncode is not None


def test_timeout_escalates_to_sigkill_for_term_ignoring_child(tmp_path):
    code = "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
    result = run_process([sys.executable, "-c", code], tmp_path, timeout=0.2, termination_grace=0.1)
    assert result.timed_out and result.returncode is not None


def test_stdin_timeout_when_child_never_reads(tmp_path):
    # Run in a separate process so a regression cannot hang the test suite.
    import subprocess
    code = """from pathlib import Path
import sys
from epe.adapters.process import run_process
r = run_process([sys.executable, '-c', 'import time; time.sleep(10)'], Path.cwd(), timeout=0.3, termination_grace=0.1, input_data=b'x' * (2 * 1024 * 1024))
assert r.timed_out and r.stdin_incomplete
"""
    proc = subprocess.run([sys.executable, "-c", code], cwd=Path.cwd(), timeout=4, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_full_duplex_large_input_not_deadlocked_or_truncated(tmp_path):
    data = b"x" * (512 * 1024)
    code = "import sys; sys.stdout.buffer.write(b'o'*200000); sys.stdout.buffer.flush(); data=sys.stdin.buffer.read(); sys.stderr.write(str(len(data)))"
    result = run_process([sys.executable, "-c", code], tmp_path, timeout=3, input_data=data)
    assert result.returncode == 0 and not result.stdin_incomplete
    assert result.stderr == str(len(data)) and len(result.stdout) == 200000


def test_early_stdin_close_is_reported_even_with_success_exit(tmp_path):
    result = run_process([sys.executable, "-c", "import os; os.close(0)"], tmp_path, timeout=3, input_data=b"x" * (1024 * 1024))
    assert result.returncode == 0 and result.stdin_incomplete


def test_cancel_during_blocked_stdin(tmp_path):
    cancelled = Event()
    timer = Thread(target=lambda: (time.sleep(0.2), cancelled.set()), daemon=True)
    timer.start()
    result = run_process([sys.executable, "-c", "import time; time.sleep(10)"], tmp_path,
                         timeout=3, cancel_event=cancelled, termination_grace=0.1,
                         input_data=b"x" * (1024 * 1024))
    assert result.cancelled and result.stdin_incomplete
