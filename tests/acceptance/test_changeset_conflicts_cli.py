import json

from epe.cli import main


def write_change(root, identifier, write_scope, protected=(), status="active"):
    path = root / "engineering/changesets" / f"{identifier}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"id": identifier, "owner": identifier.lower(),
                                "write_scope": list(write_scope), "protected": list(protected),
                                "status": status}), encoding="utf-8")


def test_changeset_conflicts_cli_is_read_only_and_blocking(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "init"]) == 0
    capsys.readouterr()
    write_change(tmp_path, "CHANGE-001", ["src/**"])
    write_change(tmp_path, "CHANGE-002", ["src/epe/cli.py"])
    assert main(["--root", str(tmp_path), "--format", "json", "changeset", "conflicts"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "blocked" and result["data"]["conflicts"]
    assert (tmp_path / "engineering/changesets/CHANGE-001.json").exists()


def test_changeset_conflicts_cli_passes_disjoint_active_ranges(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "init"]) == 0
    capsys.readouterr()
    write_change(tmp_path, "CHANGE-001", ["src/**"])
    write_change(tmp_path, "CHANGE-002", ["docs/**"])
    assert main(["--root", str(tmp_path), "--format", "json", "changeset", "conflicts"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "passed" and result["data"]["conflicts"] == []


def test_changeset_conflicts_ignores_derived_baseline_and_lease_records(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "init"]) == 0
    capsys.readouterr()
    write_change(tmp_path, "CHANGE-001", ["src/**"])
    changes = tmp_path / "engineering/changesets"
    (changes / "CHANGE-001.baseline.json").write_text(json.dumps({"status": "active", "write_scope": ["**"]}))
    (changes / "CHANGE-001.lease.json").write_text(json.dumps({"status": "active", "write_scope": ["**"]}))
    assert main(["--root", str(tmp_path), "--format", "json", "changeset", "conflicts"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["changesets"] == 1 and result["data"]["conflicts"] == []
