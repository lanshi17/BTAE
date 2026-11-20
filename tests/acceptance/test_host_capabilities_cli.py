import json

from epe.cli import main


def test_host_capabilities_cli_is_machine_readable(capsys):
    assert main(["--format", "json", "host", "capabilities"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["protocol_version"] == "1"
    hermes = next(item for item in result["data"]["hosts"] if item["host_id"] == "hermes")
    assert hermes["status"] == "unsupported-unintegrated"
