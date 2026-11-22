import json

from epe.cli import _normalize_result, _print
from epe.core.models import CommandResult


def test_result_normalizer_rejects_non_json_data_without_crashing(capsys):
    result = _normalize_result(CommandResult("fixture", "passed", data=object()))
    assert result["status"] == "error"
    assert result["diagnostics"][0]["code"] == "EPE-RESULT-SCHEMA"

    assert _print(CommandResult("fixture", "passed", data=object()), "json") == 3
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "error"
    assert output["diagnostics"][0]["code"] == "EPE-RESULT-SCHEMA"


def test_result_normalizer_preserves_valid_contract():
    result = _normalize_result(CommandResult("fixture", "passed", data={"ok": True}))
    assert result == {
        "schema_version": 1,
        "command": "fixture",
        "status": "passed",
        "diagnostics": [],
        "data": {"ok": True},
        "evidence_ids": [],
    }


def test_result_normalizer_converts_schema_validation_failure_to_error():
    result = _normalize_result(CommandResult("fixture", "not-a-status"))
    assert result["status"] == "error"
    assert result["diagnostics"][0]["code"] == "EPE-RESULT-SCHEMA"
