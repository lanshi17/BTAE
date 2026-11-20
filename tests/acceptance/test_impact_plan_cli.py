import json

from epe.cli import main


def test_impact_plan_cli_falls_back_on_parser_change(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "previous.json").write_text(json.dumps({"complete": True, "schema_version": 1, "content_digest": "old", "input_manifest": {"entries": []}}))
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "impact", "plan", "--previous", "previous.json", "--previous-parser-version", "0"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["full_rebuild"] is True
