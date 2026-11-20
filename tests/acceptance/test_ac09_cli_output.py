from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_ac09_json_stdout_exit_codes_and_log_separation(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str, expected: int):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.returncode == expected, process.stdout
        assert "Traceback" not in process.stdout and "Traceback" not in process.stderr
        assert process.stderr == ""
        lines = [line for line in process.stdout.splitlines() if line.strip()]
        assert len(lines) == 1, process.stdout
        result = json.loads(lines[0])
        assert set(("schema_version", "command", "status", "diagnostics", "data", "evidence_ids")) <= set(result)
        assert result["command"]
        return result

    init = run("init", expected=0)
    assert init["status"] == "passed"
    (tmp_path / "task.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "AC-09",
        "acceptance": ["logs stay in evidence"], "risk": "low", "target_entities": ["MOD-001"],
    }, sort_keys=False), encoding="utf-8")
    run("task", "create", "--file", "task.yaml", expected=0)
    (tmp_path / "engineering/policies/verification.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "checks": [{"id": "noisy-failure", "command": [sys.executable, "-c", "import sys; print('child stdout'); print('child stderr', file=sys.stderr); raise SystemExit(9)"]}],
    }, sort_keys=False), encoding="utf-8")
    failed = run("verify", "TASK-001", expected=1)
    assert failed["status"] == "blocked" and failed["data"]["results"][0]["result"] == "failed"
    assert "child stdout" not in json.dumps(failed) or "child stdout" in json.dumps(failed["data"]["results"][0])
    assert "child stderr" in json.dumps(failed["data"]["results"][0])

    invalid = run("task", "classify", "BAD-ID", expected=2)
    assert invalid["status"] == "error" and invalid["diagnostics"][0]["code"] == "EPE-TASK-ID"
    unsupported = run("host", "capabilities", expected=0)
    hermes = next(host for host in unsupported["data"]["hosts"] if host["host_id"] == "hermes")
    assert hermes["status"] == "unsupported-unintegrated"
