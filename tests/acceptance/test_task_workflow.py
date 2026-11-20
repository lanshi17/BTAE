import json

from epe.cli import main


def create(tmp_path, capsys, kind="feature", extra=""):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "task.yaml").write_text(f"id: TASK-001\ntype: {kind}\nobjective: work\nacceptance: [ok]\nrisk: low\ntarget_entities: [CLASS-001]\n{extra}")
    assert main(["--root", str(tmp_path), "--format", "json", "task", "create", "--file", "task.yaml"]) == 0
    capsys.readouterr()


def test_feature_activate_and_complete_requires_gate(tmp_path, capsys):
    create(tmp_path, capsys)
    assert main(["--root", str(tmp_path), "--format", "json", "task", "transition", "TASK-001", "activate"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "task", "transition", "TASK-001", "complete"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
    assert main(["--root", str(tmp_path), "--format", "json", "task", "transition", "TASK-001", "complete", "--gate", "passed"]) == 1
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "EPE-TASK-GATE-UNTRUSTED"
    assert json.loads((tmp_path / "engineering/tasks/TASK-001.json").read_text())["status"] == "active"


def test_task_cannot_be_created_as_completed(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "task.yaml").write_text("id: TASK-001\ntype: feature\nobjective: work\nacceptance: [ok]\nrisk: low\ntarget_entities: [CLASS-001]\nstatus: completed\n")
    assert main(["--root", str(tmp_path), "--format", "json", "task", "create", "--file", "task.yaml"]) == 1
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "EPE-TASK-INITIAL-STATE"


def test_special_workflows_require_their_evidence(tmp_path, capsys):
    bug = tmp_path / "bug"; bug.mkdir()
    create(bug, capsys, "bugfix")
    assert main(["--root", str(bug), "--format", "json", "task", "transition", "TASK-001", "activate"]) == 1
    assert any("reproduction" in d["message"] for d in json.loads(capsys.readouterr().out)["diagnostics"])
    exploration = tmp_path / "exploration"; exploration.mkdir()
    create(exploration, capsys, "exploration", "hypothesis: test\n")
    assert main(["--root", str(exploration), "--format", "json", "task", "transition", "TASK-001", "activate"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["status"] == "active"
