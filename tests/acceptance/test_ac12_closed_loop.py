"""AC-12: exercise the actual installed CLI boundary on temporary projects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


PROJECT_SOURCE = Path(__file__).resolve().parents[2] / "src"


def _runner(root: Path):
    env = dict(os.environ, PYTHONPATH=str(PROJECT_SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(root), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=root, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        try:
            result = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"CLI did not emit one JSON result: {process.stdout!r}") from exc
        assert process.returncode == expected, result
        assert result["command"]
        assert isinstance(result["diagnostics"], list)
        return result
    return run


def _project(root: Path):
    run = _runner(root)
    run("init")
    (root / "AGENTS.md").write_text("Fixture engineering rules.\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs/index.md").write_text("# Sample project\n", encoding="utf-8")
    (root / "docs/modules").mkdir(parents=True)
    (root / "docs/classes").mkdir(parents=True)
    (root / "src/sample").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "docs/modules/MOD-001.md").write_text(
        "---\nid: MOD-001\ntype: Module\nname: Sample\ndesign_status: reviewed\n"
        "implementation_status: implemented\nverification_status: pending\n---\n# Sample\n",
        encoding="utf-8",
    )
    (root / "docs/classes/CLASS-001.md").write_text(
        "---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: reviewed\n"
        "implementation_status: implemented\nverification_status: pending\n"
        "implementation:\n  - path: src/sample/example.py\n    symbol: Example\n---\n# Example\n",
        encoding="utf-8",
    )
    (root / "src/sample/example.py").write_text(
        "class Example:\n    def value(self):\n        return 42\n", encoding="utf-8"
    )
    (root / "tests/test_sample.py").write_text(
        "def test_sample_contract():\n    assert 40 + 2 == 42\n", encoding="utf-8"
    )
    config_path = root / "engineering/epe.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["managed"]["module_roots"] = {"MOD-001": ["src/sample"]}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    verification_path = root / "engineering/policies/verification.yaml"
    verification_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "checks": [{
            "id": "sample-pytest",
            "kind": "test",
            "result_parser": "pytest",
            "version": "1",
            "command": [sys.executable, "-m", "pytest", "-q", "tests"],
            "timeout": 30,
            "target_entities": ["CLASS-001"],
        }],
    }, sort_keys=False), encoding="utf-8")
    task_file = root / "task.yaml"
    task_file.write_text(yaml.safe_dump({
        "schema_version": 1,
        "id": "TASK-001",
        "type": "feature",
        "objective": "Verify the sample engineering loop",
        "acceptance": ["A real pytest Evidence is valid"],
        "risk": "low",
        "target_entities": ["CLASS-001"],
        "changeset": "CHANGE-001",
    }, sort_keys=False), encoding="utf-8")
    change_file = root / "change.yaml"
    change_file.write_text(yaml.safe_dump({
        "schema_version": 1,
        "id": "CHANGE-001",
        "task": "TASK-001",
        "owner": "fixture-owner",
        "affected_entities": ["MOD-001", "CLASS-001"],
        "write_scope": ["src/**", "tests/**", "docs/**"],
        "protected": ["engineering/**"],
        "dependencies": [],
        "status": "planned",
    }, sort_keys=False), encoding="utf-8")
    return run


def test_ac12_complete_cli_engineering_loop(tmp_path):
    run = _project(tmp_path)
    run("task", "create", "--file", "task.yaml")
    run("task", "transition", "TASK-001", "activate")
    run("changeset", "create", "--file", "change.yaml")
    run("changeset", "transition", "CHANGE-001", "activate")
    graph = run("graph", "build")
    assert graph["data"]["published"] is True
    context = run("context", "resolve", "TASK-001")
    assert context["data"]["task_id"] == "TASK-001"
    assert context["data"]["incomplete"] is False
    verified = run("verify", "TASK-001")
    assert len(verified["evidence_ids"]) == 1
    evidence_path = next((tmp_path / "engineering/evidence").glob("*/evidence.json"))
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["result"] == "passed" and evidence["validity"] == "valid"
    assert evidence["provenance"]["test_protocol"] == "pytest-junit-v1"
    architecture = run("architecture", "validate")
    assert architecture["data"]["status"] == "pass"
    checked = run("check", "--task", "TASK-001")
    assert checked["status"] == "passed"
    run("changeset", "transition", "CHANGE-001", "complete")
    completed = run("task", "transition", "TASK-001", "complete")
    assert completed["data"]["status"] == "completed"


def test_ac12_changed_input_cannot_finalize(tmp_path):
    run = _project(tmp_path)
    run("task", "create", "--file", "task.yaml")
    run("task", "transition", "TASK-001", "activate")
    run("changeset", "create", "--file", "change.yaml")
    run("changeset", "transition", "CHANGE-001", "activate")
    run("graph", "build")
    verified = run("verify", "TASK-001")
    assert verified["status"] == "passed"
    source = tmp_path / "src/sample/example.py"
    source.write_text("class Example:\n    def value(self):\n        return 99\n", encoding="utf-8")
    result = run("task", "transition", "TASK-001", "complete", expected=1)
    assert result["status"] == "blocked"
    assert any(d["code"] in {"EPE-GRAPH-STALE", "EPE-GATE-EVIDENCE", "EPE-GATE-TEST", "EPE-TASK-GATE"}
               for d in result["diagnostics"])
    stored = json.loads((tmp_path / "engineering/tasks/TASK-001.json").read_text(encoding="utf-8"))
    assert stored["status"] == "active"
