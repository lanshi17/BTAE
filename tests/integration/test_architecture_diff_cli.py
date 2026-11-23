import json

from epe.cli import main


def test_architecture_diff_cli_compares_selected_history(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "src").mkdir()
    source = tmp_path / "src/a.py"
    source.write_text("value = 1\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    first = json.loads(capsys.readouterr().out)["data"]["content_digest"]
    source.write_text("value = 2\n", encoding="utf-8")
    (tmp_path / "src/b.py").write_text("value = 3\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "architecture", "diff", "--previous-generation", first]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "passed"
    assert result["data"]["previous_digest"] == first
    assert result["data"]["current_digest"] != first
    assert result["data"]["status"] == "changed"
