import json

from epe.verification.runner import _validate_evidence_record


def _record():
    return {
        "schema_version": 1,
        "id": "EVIDENCE-1",
        "run_id": "RUN-1",
        "task_id": None,
        "changeset_id": None,
        "target_entities": [],
        "checker": "check",
        "checker_version": "1",
        "command": ["python", "-c", "pass"],
        "cwd": ".",
        "started_at": "2026-11-22T00:00:00Z",
        "finished_at": "2026-11-22T00:00:01Z",
        "exit_code": 0,
        "termination_reason": None,
        "result": "passed",
        "validity": "valid",
        "input_manifest": {"entries": [], "digest": "a" * 64},
        "artifacts": [{"path": "output.log", "sha256": "b" * 64}],
        "environment": {},
        "provenance": {},
    }


def test_evidence_schema_rejects_artifact_without_digest(tmp_path):
    value = _record()
    value["artifacts"] = [{"path": "output.log"}]
    try:
        _validate_evidence_record(tmp_path, value)
    except ValueError as exc:
        assert "artifacts" in str(exc)
    else:
        raise AssertionError("malformed artifact was accepted")
