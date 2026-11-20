from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


SOURCE = Path(__file__).resolve().parents[2] / "src"


def project(tmp_path: Path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        result = json.loads(process.stdout)
        assert process.returncode == expected, result
        assert result["command"] and isinstance(result["diagnostics"], list)
        return result

    result = run("init")
    assert result["status"] == "passed"
    (tmp_path / "task.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "AC-06",
        "acceptance": ["actual result is recorded"], "risk": "low", "target_entities": ["CLASS-001"],
    }, sort_keys=False), encoding="utf-8")
    run("task", "create", "--file", "task.yaml")
    return run


def configure(root: Path, check: dict):
    policy = root / "engineering/policies/verification.yaml"
    policy.write_text(yaml.safe_dump({"schema_version": 1, "checks": [check]}, sort_keys=False), encoding="utf-8")


def evidence(root: Path, result: dict):
    assert len(result["evidence_ids"]) == 1
    matches = list((root / "engineering/evidence").glob("*/evidence.json"))
    assert len(matches) == 1
    record = json.loads(matches[0].read_text(encoding="utf-8"))
    assert record["id"] == result["evidence_ids"][0]
    assert record["run_id"] in matches[0].parts
    assert record["artifacts"]
    return record


def test_ac06_pass_and_assertion_failure_are_real_and_distinct(tmp_path):
    passed_root = tmp_path / "passed"; passed_root.mkdir()
    run = project(passed_root)
    configure(passed_root, {"id": "command", "command": [sys.executable, "-c", "print('ok')"]})
    passed_result = run("verify", "TASK-001")
    assert passed_result["status"] == "passed"
    passed = evidence(passed_root, passed_result)
    assert passed["result"] == "passed" and passed["validity"] == "valid"
    assert passed["exit_code"] == 0 and passed["termination_reason"] is None

    failed_root = tmp_path / "failed"; failed_root.mkdir()
    run = project(failed_root)
    configure(failed_root, {"id": "command", "command": [sys.executable, "-c", "raise SystemExit(7)"]})
    failed_result = run("verify", "TASK-001", expected=1)
    failed = evidence(failed_root, failed_result)
    assert failed_result["status"] == "blocked"
    assert failed["result"] == "failed" and failed["termination_reason"] == "nonzero_exit"
    assert failed["exit_code"] == 7 and failed["validity"] == "valid"


def test_ac06_zero_passed_pytest_is_unconfirmed_not_passed(tmp_path):
    run = project(tmp_path)
    tests = tmp_path / "tests"; tests.mkdir()
    (tests / "test_skip.py").write_text(
        "import pytest\n@pytest.mark.skip(reason='intentionally skipped')\ndef test_skip(): pass\n",
        encoding="utf-8",
    )
    configure(tmp_path, {
        "id": "pytest", "kind": "test", "result_parser": "pytest",
        "command": [sys.executable, "-m", "pytest", "-q", "tests"],
    })
    result = run("verify", "TASK-001", expected=3)
    record = evidence(tmp_path, result)
    assert result["status"] == "error"
    assert record["result"] == "error" and record["termination_reason"] == "test_execution_unconfirmed"
    summary = json.loads((tmp_path / "engineering/evidence" / record["run_id"] / "test-summary.json").read_text())
    assert summary == {"passed": 0, "failed": 0, "skipped": 1}


def test_ac06_zero_collected_and_failed_test_have_distinct_evidence(tmp_path):
    empty_root = tmp_path / "empty"; empty_root.mkdir()
    run = project(empty_root)
    (empty_root / "tests").mkdir()
    configure(empty_root, {
        "id": "pytest", "kind": "test", "result_parser": "pytest",
        "command": [sys.executable, "-m", "pytest", "-q", "tests"],
    })
    empty_result = run("verify", "TASK-001", expected=3)
    empty = evidence(empty_root, empty_result)
    assert empty["result"] == "error" and empty["termination_reason"] == "test_execution_unconfirmed"
    empty_summary = json.loads((empty_root / "engineering/evidence" / empty["run_id"] / "test-summary.json").read_text())
    assert empty_summary == {"passed": 0, "failed": 0, "skipped": 0}

    failed_root = tmp_path / "assertion"; failed_root.mkdir()
    run = project(failed_root)
    tests = failed_root / "tests"; tests.mkdir()
    (tests / "test_fail.py").write_text("def test_fail():\n    assert False\n", encoding="utf-8")
    configure(failed_root, {
        "id": "pytest", "kind": "test", "result_parser": "pytest",
        "command": [sys.executable, "-m", "pytest", "-q", "tests"],
    })
    failed_result = run("verify", "TASK-001", expected=1)
    failed = evidence(failed_root, failed_result)
    assert failed["result"] == "failed" and failed["termination_reason"] == "test_failure_in_report"
    failed_summary = json.loads((failed_root / "engineering/evidence" / failed["run_id"] / "test-summary.json").read_text())
    assert failed_summary == {"passed": 0, "failed": 1, "skipped": 0}


def test_ac06_timeout_and_missing_command_have_distinct_evidence(tmp_path):
    timeout_root = tmp_path / "timeout"; timeout_root.mkdir()
    run = project(timeout_root)
    configure(timeout_root, {"id": "timeout", "command": [sys.executable, "-c", "import time; time.sleep(10)"], "timeout": 0.1})
    timeout_result = run("verify", "TASK-001", expected=3)
    timeout = evidence(timeout_root, timeout_result)
    assert timeout["result"] == "error" and timeout["termination_reason"] == "timeout"
    assert timeout["exit_code"] == -15

    missing_root = tmp_path / "missing"; missing_root.mkdir()
    run = project(missing_root)
    absent = missing_root / "bin/not-installed"
    configure(missing_root, {"id": "missing", "command": [str(absent)]})
    missing_result = run("verify", "TASK-001", expected=3)
    missing = evidence(missing_root, missing_result)
    assert missing["result"] == "error" and missing["termination_reason"] == "command_start_error"
    assert missing["exit_code"] is None
