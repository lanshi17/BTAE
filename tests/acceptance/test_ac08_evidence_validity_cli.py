from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_ac08_tampered_artifact_invalid_and_missing_environment_unknown(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        result = json.loads(process.stdout)
        assert process.returncode == expected, result
        assert result["command"] and isinstance(result["diagnostics"], list)
        return result

    run("init")
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs/design.md").write_text("---\nid: CLASS-001\ntype: Class\nname: E\ndesign_status: reviewed\n---\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (tmp_path / "engineering/policies/verification.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "checks": [{"id": "pytest", "kind": "test", "result_parser": "pytest",
                                            "command": [sys.executable, "-m", "pytest", "-q", "tests"]}],
    }, sort_keys=False), encoding="utf-8")
    (tmp_path / "task.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "AC-08",
        "acceptance": ["validity is conservative"], "risk": "low", "target_entities": ["CLASS-001"],
    }, sort_keys=False), encoding="utf-8")
    run("task", "create", "--file", "task.yaml")
    verified = run("verify", "TASK-001")
    assert verified["status"] == "passed"
    evidence_path = next((tmp_path / "engineering/evidence").glob("*/evidence.json"))
    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    output_path = tmp_path / "engineering/evidence" / record["run_id"] / "output.log"
    output_path.write_text(output_path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    checked = run("check", "--task", "TASK-001", expected=3)
    current = next(item for item in checked["data"]["evidence"] if item["run_id"] == record["run_id"])
    assert current["validity"] == "invalid"
    assert any(item["code"] in {"EPE-GATE-TEST", "EPE-GATE-EVIDENCE"} for item in checked["diagnostics"])

    output_path.write_text(record["provenance"].get("output", "") if False else output_path.read_text(encoding="utf-8").replace("tampered\n", ""), encoding="utf-8")
    stored = json.loads(evidence_path.read_text(encoding="utf-8"))
    stored.pop("environment", None)
    evidence_path.write_text(json.dumps(stored), encoding="utf-8")
    checked = run("check", "--task", "TASK-001", expected=3)
    current = next(item for item in checked["data"]["evidence"] if item["run_id"] == record["run_id"])
    assert current["validity"] == "unknown"
    assert any(item["code"] in {"EPE-GATE-TEST", "EPE-GATE-EVIDENCE"} for item in checked["diagnostics"])
