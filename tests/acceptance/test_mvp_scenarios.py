import json
import subprocess
import sys

from epe.cli import main


def _project(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "docs").mkdir(); (tmp_path / "src").mkdir()
    (tmp_path / "docs" / "x.md").write_text("---\nid: CLASS-001\ntype: Class\nname: X\ndesign_status: draft\nimplementation_status: implemented\nimplementation:\n  - path: src/x.py\n    symbol: X\n---\n", encoding="utf-8")
    (tmp_path / "src" / "x.py").write_text("class X:\n    pass\n", encoding="utf-8")
    (tmp_path / "task.yaml").write_text("id: TASK-001\ntype: feature\nobjective: x\nacceptance: [x]\nrisk: low\ntarget_entities: [CLASS-001]\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "task", "create", "--file", "task.yaml"]) == 0
    capsys.readouterr()


def test_mapping_deletion_blocks(tmp_path, capsys):
    _project(tmp_path, capsys)
    (tmp_path / "src" / "x.py").write_text("class Other:\n    pass\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "mapping", "validate"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "error" or result["status"] == "blocked"
    assert any(d["code"] == "EPE-MAPPING-SYMBOL" for d in result["diagnostics"])


def test_failed_check_creates_blocking_evidence(tmp_path, capsys):
    _project(tmp_path, capsys)
    (tmp_path / "engineering" / "policies" / "verification.yaml").write_text("schema_version: 1\nchecks:\n  - id: CHECK-FAIL\n    command: [python, -c, \"raise SystemExit(2)\"]\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "verify", "TASK-001"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "blocked"
    assert result["evidence_ids"]
    assert result["data"]["results"][0]["result"] == "failed"


def test_invalid_check_configuration_cannot_report_pass(tmp_path, capsys):
    _project(tmp_path, capsys)
    (tmp_path / "engineering/policies/verification.yaml").write_text(
        'checks:\n  - id: OK\n    command: [python, -c, pass]\n  - id: BAD\n    command: bad\n', encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "verify", "TASK-001"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "error"
    assert not result["evidence_ids"]
    assert any(d["code"] == "EPE-VERIFY-CONFIG" for d in result["diagnostics"])


def test_check_blocks_missing_changeset_and_policy(tmp_path, capsys):
    _project(tmp_path, capsys)
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "check", "--task", "TASK-001"]) != 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] != "passed"
    codes = {d["code"] for d in result["diagnostics"]}
    assert "EPE-CHANGESET-MISSING" in codes
    assert "EPE-VERIFY-NO-CHECKS" in codes


def test_check_requires_evidence_for_every_configured_check(tmp_path, capsys):
    assert subprocess.run(["git", "init", "-q", str(tmp_path)], capture_output=True).returncode == 0
    _project(tmp_path, capsys)
    task_file = tmp_path / "engineering/tasks/TASK-001.json"
    task = json.loads(task_file.read_text()); task["changeset"] = "CHANGE-001"
    task_file.write_text(json.dumps(task))
    changesets = tmp_path / "engineering/changesets"; changesets.mkdir(exist_ok=True)
    (changesets / "CHANGE-001.json").write_text(json.dumps({"write_scope": ["**"], "protected": []}))
    policy = {"schema_version": 1, "checks": [
        {"id": "ONE", "command": [sys.executable, "-c", "pass"]},
        {"id": "TWO", "command": [sys.executable, "-c", "pass"]}]}
    (tmp_path / "engineering/policies/verification.yaml").write_text(json.dumps(policy))
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "verify", "TASK-001"]) == 0
    result = json.loads(capsys.readouterr().out)
    for item in result["data"]["results"]:
        if item["checker"] == "TWO":
            (tmp_path / "engineering/evidence" / item["run_id"] / "evidence.json").unlink()
    assert main(["--root", str(tmp_path), "--format", "json", "check", "--task", "TASK-001"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-GATE-EVIDENCE" and "TWO" in d["message"] for d in result["diagnostics"])
    assert any(d["code"] == "EPE-EVIDENCE-READ" for d in result["diagnostics"])
    assert any(d["code"] in {"EPE-CHANGESET-INVALID", "EPE-SCOPE-BASELINE"} for d in result["diagnostics"])


def test_architecture_rejects_missing_policy(tmp_path, capsys):
    _project(tmp_path, capsys)
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    (tmp_path / "engineering/policies/architecture.yaml").unlink()
    assert main(["--root", str(tmp_path), "--format", "json", "architecture", "validate"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "error"
