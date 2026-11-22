import json
import subprocess
import sys

from epe.cli import main
from epe.governance.baseline import capture_baseline, compare_baseline
from epe.governance.tasks import check_scope


def setup_project(root, capsys):
    assert subprocess.run(["git", "init", "-q", str(root)], capture_output=True).returncode == 0
    assert main(["--root", str(root), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (root / "src").mkdir(); (root / "docs").mkdir()
    (root / "src/old name.py").write_text("original\n")
    (root / "docs/protected.md").write_text("original\n")
    task = {"id": "TASK-001", "type": "feature", "objective": "test", "acceptance": ["verified"], "risk": "low", "target_entities": ["CLASS-001"], "changeset": "CHANGE-001"}
    (root / "task.yaml").write_text(json.dumps(task))
    assert main(["--root", str(root), "--format", "json", "task", "create", "--file", "task.yaml"]) == 0
    capsys.readouterr()
    change = {"id": "CHANGE-001", "task": "TASK-001", "owner": "developer", "affected_entities": ["CLASS-001"], "write_scope": ["src"], "protected": ["docs"], "dependencies": [], "status": "active"}
    (root / "change.yaml").write_text(json.dumps(change))
    return change


def test_baseline_tracks_committed_renamed_and_protected_changes(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    args = ["--root", str(tmp_path), "--format", "json", "changeset", "create", "--file", "change.yaml"]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["baseline_manifest"]
    change_path = tmp_path / "engineering/changesets/CHANGE-001.json"
    baseline_path = tmp_path / "engineering/changesets/CHANGE-001.baseline.json"
    before = (change_path.read_bytes(), baseline_path.read_bytes())
    assert main(args) == 5
    capsys.readouterr()
    assert before == (change_path.read_bytes(), baseline_path.read_bytes())
    (tmp_path / "src/old name.py").rename(tmp_path / "src/new name.py")
    (tmp_path / "src/new name.py").write_text("changed\n")
    (tmp_path / "docs/protected.md").write_text("changed\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "changes"], cwd=tmp_path, check=True)
    change = json.loads(change_path.read_text())
    actual = compare_baseline(tmp_path, {}, change)
    assert actual == ["docs/protected.md", "src/new name.py", "src/old name.py"]
    assert check_scope(actual, change["write_scope"], change["protected"])[1] == ["docs/protected.md"]
    widened = dict(change, write_scope=["**"], protected=[])
    try:
        compare_baseline(tmp_path, {}, widened)
    except ValueError as exc:
        assert "摘要" in str(exc)
    else:
        raise AssertionError("changed scope accepted without a new baseline")
    baseline = json.loads(baseline_path.read_text()); baseline["entries"] = []
    baseline_path.write_text(json.dumps(baseline))
    try:
        compare_baseline(tmp_path, {}, change)
    except ValueError as exc:
        assert "摘要" in str(exc)
    else:
        raise AssertionError("tampered baseline accepted")


def test_changeset_runtime_validation_rejects_unknown_and_wrong_typed_fields():
    from epe.governance.baseline import validate_changeset
    base = {"id": "CHANGE-001", "task": "TASK-001", "owner": "owner", "affected_entities": ["CLASS-001"], "write_scope": ["src/**"], "protected": [], "dependencies": [], "status": "planned"}
    import pytest
    with pytest.raises(ValueError, match="未知字段"):
        validate_changeset({**base, "unknown": True}, "TASK-001")
    with pytest.raises(ValueError, match="缺少有效"):
        validate_changeset({**base, "dependencies": ["bad"]}, "TASK-001")
    with pytest.raises(ValueError, match="缺少有效"):
        validate_changeset({**base, "baseline_manifest": []}, "TASK-001")


def test_changeset_schema_rejects_empty_required_collections():
    import json
    import jsonschema
    from pathlib import Path
    schema = json.loads((Path(__file__).resolve().parents[2] / "engineering/schemas/changeset.schema.json").read_text(encoding="utf-8"))
    value = {"schema_version": 1, "id": "CHANGE-001", "task": "TASK-001", "owner": "owner", "affected_entities": [], "write_scope": [], "protected": [], "dependencies": [], "status": "planned"}
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(value))
    assert errors


def test_baseline_rejects_escape_symlink(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    (tmp_path / "src/escape").symlink_to(tmp_path.parent, target_is_directory=True)
    assert main(["--root", str(tmp_path), "--format", "json", "changeset", "create", "--file", "change.yaml"]) == 3
    assert not (tmp_path / "engineering/changesets/CHANGE-001.json").exists()


def test_check_uses_registered_baseline(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    (tmp_path / "docs/design.md").write_text("---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: draft\n---\n# Example\n")
    (tmp_path / "engineering/policies/verification.yaml").write_text(json.dumps({"checks": [{"id": "check", "command": [sys.executable, "-c", "pass"]}]}))
    assert main(["--root", str(tmp_path), "--format", "json", "changeset", "create", "--file", "change.yaml"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "verify", "TASK-001"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "check", "--task", "TASK-001"]) == 0
    capsys.readouterr()
    (tmp_path / "docs/protected.md").write_text("out of scope\n")
    assert main(["--root", str(tmp_path), "--format", "json", "check", "--task", "TASK-001"]) != 0
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-GATE-SCOPE" for d in result["diagnostics"])


def test_task_completion_rechecks_actual_gate(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    (tmp_path / "docs/design.md").write_text("---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: draft\n---\n# Example\n")
    (tmp_path / "engineering/policies/verification.yaml").write_text(json.dumps({"checks": [{"id": "check", "command": [sys.executable, "-c", "pass"]}]}))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["task", "transition", "TASK-001", "activate"]) == 0
    capsys.readouterr()
    assert main(base + ["changeset", "create", "--file", "change.yaml"]) == 0
    capsys.readouterr()
    assert main(base + ["graph", "build"]) == 0
    capsys.readouterr()
    assert main(base + ["task", "transition", "TASK-001", "complete"]) == 1
    assert any(d["code"] == "EPE-TASK-GATE" for d in json.loads(capsys.readouterr().out)["diagnostics"])
    assert main(base + ["verify", "TASK-001"]) == 0
    capsys.readouterr()
    assert main(base + ["task", "transition", "TASK-001", "complete", "--expected-revision", "1"]) == 1
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "EPE-TASK-REVISION"
    assert main(base + ["task", "transition", "TASK-001", "complete", "--expected-revision", "2"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["status"] == "completed"


def test_git_provenance_exposes_untracked_and_status_facts(tmp_path):
    from epe.adapters.git import git_provenance
    import subprocess
    (tmp_path / "file.txt").write_text("one")
    before = git_provenance(tmp_path)
    assert before["git_available"] is False or before["commit"] is None
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    (tmp_path / "new.txt").write_text("new")
    value = git_provenance(tmp_path)
    assert value["git_available"] and "new.txt" in value["untracked"] and value["dirty"]


def test_changeset_lifecycle_transitions_and_revision_conflicts(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    assert main(["--root", str(tmp_path), "--format", "json", "task", "transition", "TASK-001", "activate"]) == 0
    capsys.readouterr()
    change = json.loads((tmp_path / "change.yaml").read_text())
    change["status"] = "planned"
    (tmp_path / "change.yaml").write_text(json.dumps(change))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["changeset", "create", "--file", "change.yaml"]) == 0
    capsys.readouterr()
    assert main(base + ["changeset", "transition", "CHANGE-001", "activate", "--expected-revision", "1"]) == 0
    activated = json.loads(capsys.readouterr().out)
    assert activated["data"]["status"] == "active" and activated["data"]["revision"] == 2
    assert main(base + ["changeset", "transition", "CHANGE-001", "activate", "--expected-revision", "1"]) == 1
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "EPE-CHANGESET-REVISION"
    (tmp_path / "docs/new.md").write_text("out of scope")
    assert main(base + ["changeset", "transition", "CHANGE-001", "complete", "--expected-revision", "2"]) == 1
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["diagnostics"][0]["code"] == "EPE-GATE-SCOPE"
    assert main(base + ["changeset", "transition", "CHANGE-001", "abort", "--expected-revision", "2"]) == 0
    aborted = json.loads(capsys.readouterr().out)
    assert aborted["data"]["status"] == "aborted" and aborted["data"]["revision"] == 3
    from epe.adapters.audit import read_audit_events
    events = read_audit_events(tmp_path / "engineering/audit/events.jsonl")
    types = [event["event_type"] for event in events]
    assert "task_created" in types
    assert types.count("task_transition") == 1
    assert "changeset_created" in types
    assert types.count("changeset_transition") == 2
    assert all(event["payload"].get("record_sha256") for event in events if event["event_type"] in {"task_created", "task_transition", "changeset_created", "changeset_transition"})


def test_changeset_complete_requires_clean_declared_scope(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    change = json.loads((tmp_path / "change.yaml").read_text()); change["status"] = "planned"
    (tmp_path / "change.yaml").write_text(json.dumps(change))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["changeset", "create", "--file", "change.yaml"]) == 0; capsys.readouterr()
    assert main(base + ["changeset", "transition", "CHANGE-001", "activate"]) == 0; capsys.readouterr()
    # A clean scope alone cannot establish task completion.
    assert main(base + ["changeset", "transition", "CHANGE-001", "complete", "--expected-revision", "2"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-CHANGESET-GATE" for d in result["diagnostics"])


def test_changeset_completion_requires_real_gate_and_bound_active_task(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    (tmp_path / "docs/design.md").write_text("---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: draft\n---\n# Example\n")
    (tmp_path / "engineering/policies/verification.yaml").write_text(json.dumps({"checks": [{"id": "check", "command": [sys.executable, "-c", "pass"]}]}))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["task", "transition", "TASK-001", "activate"]) == 0; capsys.readouterr()
    assert main(base + ["changeset", "create", "--file", "change.yaml"]) == 0; capsys.readouterr()
    assert main(base + ["graph", "build"]) == 0; capsys.readouterr()
    assert main(base + ["changeset", "transition", "CHANGE-001", "complete"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-CHANGESET-GATE" for d in output["diagnostics"])
    assert json.loads((tmp_path / "engineering/changesets/CHANGE-001.json").read_text())["status"] == "active"
    assert main(base + ["verify", "TASK-001"]) == 0; capsys.readouterr()
    assert main(base + ["changeset", "transition", "CHANGE-001", "complete"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["status"] == "completed"


def test_legacy_baseline_can_be_read_but_not_transitioned(tmp_path, capsys):
    from epe.core.fingerprint import sha256_json
    setup_project(tmp_path, capsys)
    change = json.loads((tmp_path / "change.yaml").read_text()); change["status"] = "planned"
    (tmp_path / "change.yaml").write_text(json.dumps(change))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["changeset", "create", "--file", "change.yaml"]) == 0; capsys.readouterr()
    path = tmp_path / "engineering/changesets/CHANGE-001.json"
    bp = tmp_path / "engineering/changesets/CHANGE-001.baseline.json"
    stored = json.loads(path.read_text()); baseline = json.loads(bp.read_text())
    declared = {k: v for k, v in stored.items() if k != "baseline_manifest"}
    legacy = sha256_json({"entries": baseline["entries"], "changeset": declared})
    baseline["digest"] = stored["baseline_manifest"] = legacy
    bp.write_text(json.dumps(baseline)); path.write_text(json.dumps(stored))
    assert compare_baseline(tmp_path, {}, stored) == []
    assert main(base + ["changeset", "transition", "CHANGE-001", "activate"]) == 1
    assert any(d["code"] == "EPE-CHANGESET-LEGACY" for d in json.loads(capsys.readouterr().out)["diagnostics"])
    assert json.loads(path.read_text())["status"] == "planned"


def test_aborted_changeset_cannot_satisfy_task_check(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    (tmp_path / "docs/design.md").write_text("---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: draft\n---\n# Example\n")
    (tmp_path / "engineering/policies/verification.yaml").write_text(json.dumps({"checks": [{"id": "check", "command": [sys.executable, "-c", "pass"]}]}))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["changeset", "create", "--file", "change.yaml"]) == 0; capsys.readouterr()
    assert main(base + ["graph", "build"]) == 0; capsys.readouterr()
    assert main(base + ["verify", "TASK-001"]) == 0; capsys.readouterr()
    assert main(base + ["changeset", "transition", "CHANGE-001", "abort"]) == 0; capsys.readouterr()
    assert main(base + ["check", "--task", "TASK-001"]) != 0
    assert any(d["code"] == "EPE-SCOPE-BASELINE" for d in json.loads(capsys.readouterr().out)["diagnostics"])
