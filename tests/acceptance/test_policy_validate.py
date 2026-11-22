import json

from epe.cli import main


def test_policy_validate_cli_accepts_initialized_policies(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "policy", "validate"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["valid"] is True


def test_policy_validate_reports_unknown_fields(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    path = tmp_path / "engineering/policies/architecture.yaml"
    path.write_text("schema_version: 1\nforbidden_dependencies: []\nunknown: true\n")
    assert main(["--root", str(tmp_path), "--format", "json", "policy", "validate"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "error"
    assert any(d["code"] == "EPE-POLICY-INVALID" for d in result["diagnostics"])


def test_policy_validate_rejects_workflow_without_mandatory_fact(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    path = tmp_path / "engineering/workflows/bugfix.yaml"
    path.write_text("schema_version: 1\ntype: bugfix\nrequired: [objective, acceptance, target_entities]\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "policy", "validate"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-WORKFLOW-INVALID" for d in result["diagnostics"])


def test_policy_validator_rejects_symlinked_policy_parent(tmp_path):
    from epe.governance.policies import validate_policy_files
    outside = tmp_path / "outside-policy"; outside.mkdir()
    (outside / "verification.yaml").write_text("schema_version: 1\nchecks: []\n", encoding="utf-8")
    (tmp_path / "engineering").mkdir()
    (tmp_path / "engineering" / "linked").symlink_to(outside, target_is_directory=True)
    config = {"policies": {"verification": "engineering/linked/verification.yaml", "architecture": "engineering/linked/verification.yaml"}}
    _, diagnostics = validate_policy_files(tmp_path, config)
    assert any(item.code == "EPE-POLICY-READ" for item in diagnostics)


def test_architecture_and_verify_consumers_reject_schema_invalid_policy(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs/module.md").write_text("---\nid: MOD-A\ntype: Module\nname: A\n---\n")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src/a.py").write_text("value = 1\n")
    architecture = tmp_path / "engineering/policies/architecture.yaml"
    architecture.write_text("schema_version: 1\nforbidden_dependencies: []\nunknown: true\n")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "architecture", "validate"]) != 0
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-ARCH-POLICY" for d in result["diagnostics"])
    verification = tmp_path / "engineering/policies/verification.yaml"
    verification.write_text("schema_version: 1\nchecks:\n  - id: ok\n    command: [python, -c, pass]\nunknown: true\n")
    from epe.verification.runner import run_checks
    evidence, diagnostics = run_checks(tmp_path, {"policies": {"verification": "engineering/policies/verification.yaml"}}, "TASK-1")
    assert not evidence and any(d.code == "EPE-POLICY-INVALID" for d in diagnostics)
