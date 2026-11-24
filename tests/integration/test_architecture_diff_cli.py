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
    assert result["data"]["expected_architecture"]["status"] == "pass"


def test_architecture_diff_cli_reports_applied_exception(tmp_path, capsys):
    import yaml

    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "src/b.py").write_text("value = 1\n", encoding="utf-8")
    adr_dir = tmp_path / "docs/architecture/decisions"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-1.md").write_text(
        "---\nid: ADR-1\ntype: ADR\nname: exception\ndesign_status: approved\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "engineering/policies/architecture.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "forbidden_dependencies": [{"id": "R1", "from": "SRC-src/a.py", "to": "SRC-src/b.py"}],
        "exceptions": [{
            "id": "EX-1", "rule_id": "R1", "adr": "ADR-1",
            "from": "SRC-src/a.py", "to": "SRC-src/b.py",
            "review_until": "2099-01-01T00:00:00Z",
        }],
    }), encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    first = json.loads(capsys.readouterr().out)["data"]["content_digest"]
    (tmp_path / "src/c.py").write_text("value = 2\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "architecture", "diff", "--previous-generation", first]) == 0
    result = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in result["data"]["expected_architecture"]["exceptions_applied"]] == ["EX-1"]
