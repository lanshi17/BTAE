import json

from epe.cli import main


def test_audit_verify_cli_reports_empty_and_tampered_chain(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "audit", "verify"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["events"] == 0
    audit = tmp_path / "engineering/audit/events.jsonl"
    audit.parent.mkdir(parents=True, exist_ok=True); audit.write_text('{"bad":true}\n')
    assert main(["--root", str(tmp_path), "--format", "json", "audit", "verify"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"
