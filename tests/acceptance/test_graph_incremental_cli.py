import json

from epe.cli import main


def test_graph_build_incremental_cli_publishes(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "src").mkdir(); (tmp_path / "src/a.py").write_text("value = 1\n")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    previous = tmp_path / "previous.json"
    previous.write_bytes((tmp_path / ".engineering/graph.json").read_bytes())
    (tmp_path / "src/a.py").write_text("value = 2\n")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build", "--incremental-from", "previous.json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["published"] is True


def test_impact_plan_rebuilds_if_previous_snapshot_is_corrupt(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "src").mkdir(); (tmp_path / "src/a.py").write_text("value = 1\n")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    previous = tmp_path / "previous.json"
    graph = json.loads((tmp_path / ".engineering/graph.json").read_text())
    graph["code_facts"] = []
    previous.write_text(json.dumps(graph))
    assert main(["--root", str(tmp_path), "--format", "json", "impact", "plan", "--previous", "previous.json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["full_rebuild"] is True
    assert output["data"]["reason"] == "snapshot_invalid_or_incompatible"
