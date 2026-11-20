from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_ac10_rebuild_is_identical_and_lock_conflict_preserves_current(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        lines = [line for line in process.stdout.splitlines() if line.strip()]
        assert len(lines) == 1
        result = json.loads(lines[0])
        assert process.returncode == expected, result
        return result

    run("init")
    (tmp_path / "src").mkdir()
    source = tmp_path / "src/a.py"
    source.write_text("class A:\n    pass\n", encoding="utf-8")
    first = run("graph", "build")
    assert first["status"] == "passed" and first["data"]["published"] is True
    first_digest = first["data"]["content_digest"]
    pointer_path = tmp_path / ".engineering/current.json"
    old_pointer = pointer_path.read_bytes()
    (tmp_path / ".engineering/graph.json").unlink()
    pointer_path.unlink()
    rebuilt = run("graph", "build")
    assert rebuilt["status"] == "passed" and rebuilt["data"]["content_digest"] == first_digest
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    assert pointer["generation"] == first_digest
    assert (tmp_path / ".engineering/generations" / first_digest / "graph.json").exists()

    source.write_text("class A:\n    value = 2\n", encoding="utf-8")
    pointer_before_conflict = pointer_path.read_bytes()
    lock_path = tmp_path / ".engineering/.write.lock"
    lock_path.write_text("other-writer\n", encoding="utf-8")
    conflict = run("graph", "build", expected=5)
    assert conflict["status"] == "blocked" and conflict["data"]["published"] is False
    assert any(item["code"] == "EPE-WRITE-CONFLICT" for item in conflict["diagnostics"])
    assert pointer_path.read_bytes() == pointer_before_conflict
    assert json.loads(pointer_path.read_text(encoding="utf-8"))["generation"] == first_digest
    assert not list((tmp_path / ".engineering/generations").glob(".tmp-*"))
    lock_path.unlink()
