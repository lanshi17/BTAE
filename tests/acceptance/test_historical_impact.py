import json

from epe.cli import main


def call(root, capsys, *args):
    code = main(["--root", str(root), "--format", "json", *args])
    return code, json.loads(capsys.readouterr().out)


def setup_graph(root, capsys):
    assert call(root, capsys, "init")[0] == 0
    (root / "src").mkdir()
    (root / "src/a.py").write_text("class A: pass\n")
    (root / "src/b.py").write_text("import a\n")
    code, _ = call(root, capsys, "graph", "build")
    assert code == 0
    return json.loads((root / ".engineering/current.json").read_text())["generation"]


def test_deleted_and_moved_source_uses_selected_history(tmp_path, capsys):
    previous = setup_graph(tmp_path, capsys)
    (tmp_path / "src/a.py").rename(tmp_path / "src/moved.py")
    assert call(tmp_path, capsys, "graph", "build")[0] == 0
    code, output = call(tmp_path, capsys, "impact", "analyze", "SRC-src/a.py", "--previous-generation", previous, "--new-entity", "SRC-src/moved.py")
    assert code == 0
    data = output["data"]
    assert data["historical_generation"] == previous and data["current_generation"] != previous
    assert data["identity_mapping"] == "caller_supplied"
    assert "SRC-src/b.py" in {item["entity_id"] for item in data["historical"]["impacts"]}
    assert "SRC-src/b.py" not in {item["entity_id"] for item in data["current"]["impacts"]}
    code, output = call(tmp_path, capsys, "impact", "analyze", "SRC-src/a.py", "--previous-generation", previous)
    assert code == 0 and output["data"]["current"] is None


def test_history_requires_fresh_current_and_valid_snapshot(tmp_path, capsys):
    previous = setup_graph(tmp_path, capsys)
    (tmp_path / "src/a.py").unlink()
    code, output = call(tmp_path, capsys, "impact", "analyze", "SRC-src/a.py", "--previous-generation", previous)
    assert code != 0 and output["diagnostics"][0]["code"] == "EPE-GRAPH-STALE"
    assert call(tmp_path, capsys, "graph", "build")[0] == 0
    code, _ = call(tmp_path, capsys, "impact", "analyze", "MISSING", "--previous-generation", previous)
    assert code == 1
    code, _ = call(tmp_path, capsys, "impact", "analyze", "SRC-src/a.py", "--previous-generation", "../bad")
    assert code != 0
    path = tmp_path / ".engineering/generations" / previous / "graph.json"
    snapshot = json.loads(path.read_text()); snapshot["edges"] = []; path.write_text(json.dumps(snapshot))
    code, output = call(tmp_path, capsys, "impact", "analyze", "SRC-src/a.py", "--previous-generation", previous)
    assert code != 0 and output["diagnostics"][0]["code"] == "EPE-GRAPH-HISTORY"
