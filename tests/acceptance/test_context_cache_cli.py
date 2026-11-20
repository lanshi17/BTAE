import json

from epe.cli import main


def test_context_cli_reports_cache_hit_and_invalidates(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "task.yaml").write_text("id: TASK-001\ntype: feature\nobjective: context\nacceptance: [ok]\nrisk: low\ntarget_entities: [MOD-001]\nchangeset: CHANGE-001\n")
    (tmp_path / "docs/modules").mkdir(parents=True)
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "docs/modules/core.md").write_text("---\nid: MOD-001\ntype: Module\nname: Core\ndesign_status: draft\nimplementation_status: not_started\nverification_status: pending\n---\n# Core\n")
    assert main(["--root", str(tmp_path), "--format", "json", "task", "create", "--file", "task.yaml"]) == 0
    capsys.readouterr()
    (tmp_path / "change.yaml").write_text("id: CHANGE-001\ntask: TASK-001\nowner: owner\naffected_entities: [MOD-001]\nwrite_scope: [docs]\nprotected: [src]\ndependencies: []\nstatus: planned\n")
    assert main(["--root", str(tmp_path), "--format", "json", "changeset", "create", "--file", "change.yaml"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "context", "resolve", "TASK-001"]) == 0
    first = json.loads(capsys.readouterr().out)["data"]
    assert first["cache"] == "miss"
    sources = {item["source_type"]: item for item in first["items"]}
    assert "changeset" in sources and "policy" in sources
    assert sources["changeset"]["freshness"] == "unknown"
    assert "write_scope" in sources["changeset"]["content"]
    assert main(["--root", str(tmp_path), "--format", "json", "context", "resolve", "TASK-001"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["cache"] == "hit"
    change_path = tmp_path / "engineering/changesets/CHANGE-001.json"
    change = json.loads(change_path.read_text()); change["protected"] = ["src", "engineering"]
    change_path.write_text(json.dumps(change))
    assert main(["--root", str(tmp_path), "--format", "json", "context", "resolve", "TASK-001"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["cache"] == "miss"
    change["task"] = "TASK-WRONG"; change_path.write_text(json.dumps(change))
    assert main(["--root", str(tmp_path), "--format", "json", "context", "resolve", "TASK-001"]) == 1
    invalid = json.loads(capsys.readouterr().out)["data"]
    assert invalid["incomplete"] and "changeset:CHANGE-001" in invalid["omissions"]
    change["task"] = "TASK-001"; change_path.write_text(json.dumps(change))
    (tmp_path / "docs/index.md").write_text("changed")
    assert main(["--root", str(tmp_path), "--format", "json", "context", "resolve", "TASK-001"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["cache"] == "miss"
    assert any(d["code"] == "EPE-GRAPH-STALE" for d in result["diagnostics"])


def test_context_requires_declared_changeset(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "docs/core.md").write_text("---\nid: MOD-001\ntype: Module\nname: Core\n---\n# Core\n")
    (tmp_path / "task.yaml").write_text("id: TASK-001\ntype: feature\nobjective: goal\nacceptance: [ok]\nrisk: low\ntarget_entities: [MOD-001]\n")
    assert main(["--root", str(tmp_path), "--format", "json", "task", "create", "--file", "task.yaml"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "context", "resolve", "TASK-001"]) == 1
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["incomplete"] and "changeset:missing" in data["omissions"]
