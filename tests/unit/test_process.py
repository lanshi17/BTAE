from __future__ import annotations

import sys

from epe.adapters.process import run_process


def test_process_captures_bounded_stdout_and_stderr_with_truncation():
    code = "import os; os.write(1, b'a'*200000); os.write(2, b'b'*180000)"
    result = run_process([sys.executable, "-c", code], __import__("pathlib").Path.cwd(), max_output_bytes=1024)
    assert result.returncode == 0
    assert len(result.stdout.encode()) <= 1024 and len(result.stderr.encode()) <= 1024
    assert result.stdout_truncated and result.stderr_truncated


def test_process_keeps_small_output_and_reports_start_error(tmp_path):
    result = run_process([sys.executable, "-c", "print('hello')"], tmp_path)
    assert result.stdout == "hello\n" and result.returncode == 0
    missing = run_process([str(tmp_path / "missing-executable")], tmp_path)
    assert missing.termination_reason == "start_error" and missing.returncode is None
    bad_cwd = run_process([sys.executable, "-c", "pass"], tmp_path / "missing-cwd")
    assert bad_cwd.termination_reason == "start_error" and bad_cwd.returncode is None


def test_process_rejects_invalid_argv_and_input_before_spawning(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        run_process([], tmp_path)
    with pytest.raises(ValueError):
        run_process([sys.executable, ""], tmp_path)
    with pytest.raises(TypeError):
        run_process([sys.executable, "-c", "pass"], tmp_path, input_data="text")


def test_process_rejects_invalid_bounds(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        run_process([sys.executable, "-c", "pass"], tmp_path, max_output_bytes=-1)
    with pytest.raises(ValueError):
        run_process([sys.executable, "-c", "pass"], tmp_path, timeout=0)


def test_process_termination_grace_must_be_nonnegative(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        run_process([sys.executable, "-c", "pass"], tmp_path, termination_grace=-0.1)


def test_non_posix_signal_falls_back_to_direct_process(monkeypatch):
    import epe.adapters.process as process
    class FakeProcess:
        pid = 123
        terminated = False
        killed = False
        def terminate(self): self.terminated = True
        def kill(self): self.killed = True
    fake = FakeProcess()
    monkeypatch.setattr(process.os, "name", "nt")
    process._signal_process_tree(fake, process.signal.SIGTERM)
    process._signal_process_tree(fake, process.signal.SIGKILL)
    assert fake.terminated and fake.killed
