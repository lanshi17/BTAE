from types import SimpleNamespace

from epe.governance.gates import finalize_gate


def evidence(checker, finished_at, result="passed", **overrides):
    return {"id": "EVIDENCE-" + checker, "checker": checker, "checker_version": "1",
            "command": ["run", checker], "task_id": "TASK-1", "changeset_id": "CHANGE-1",
            "validity": "valid", "result": result, "finished_at": finished_at, **overrides}


def test_each_configured_check_requires_matching_evidence():
    task = SimpleNamespace(id="TASK-1", changeset="CHANGE-1")
    checks = [{"id": "A", "command": ["run", "A"]}, {"id": "B", "command": ["run", "B"]}]
    status, diagnostics = finalize_gate(task, True, True, True, [evidence("A", "2026-01-01T00:00:00Z")], True, checks)
    assert status == "blocked"
    assert any("B" in d.message for d in diagnostics)
    records = [evidence("A", "2026-01-01T00:00:00Z", "failed"),
               evidence("A", "2026-01-02T00:00:00Z"), evidence("B", "2026-01-02T00:00:00Z")]
    assert finalize_gate(task, True, True, True, records, True, checks)[0] == "passed"
    records.append(evidence("B", "2026-01-03T00:00:00Z", "failed"))
    assert finalize_gate(task, True, True, True, records, True, checks)[0] == "blocked"


def test_wrong_command_or_task_never_satisfies_check():
    task = SimpleNamespace(id="TASK-1", changeset="CHANGE-1")
    checks = [{"id": "A", "command": ["run", "A"]}]
    assert finalize_gate(task, True, True, True, [evidence("A", "2026-01-01", command=["wrong"])], True, checks)[0] == "blocked"
    assert finalize_gate(task, True, True, True, [evidence("A", "2026-01-01", task_id="TASK-2")], True, checks)[0] == "blocked"
    assert finalize_gate(task, True, True, True, [], True, [])[0] == "blocked"


def test_latest_record_must_be_valid_even_if_older_record_passed():
    task = SimpleNamespace(id="TASK-1", changeset="CHANGE-1")
    checks = [{"id": "A", "command": ["run", "A"]}]
    earlier = evidence("A", "2026-01-01T00:00:00Z")
    for validity, result in (("unknown", "failed"), ("invalid", "passed"), ("stale", "passed")):
        later = evidence("A", "2026-01-02T00:00:00Z", result, validity=validity)
        assert finalize_gate(task, True, True, True, [earlier, later], True, checks)[0] == "blocked"
        latest = evidence("A", "2026-01-03T00:00:00Z")
        assert finalize_gate(task, True, True, True, [earlier, later, latest], True, checks)[0] == "passed"


def test_evidence_order_uses_timezone_and_rejects_ambiguous_times():
    task = SimpleNamespace(id="TASK-1", changeset="CHANGE-1")
    checks = [{"id": "A", "command": ["run", "A"]}]
    earlier = evidence("A", "2026-01-02T01:00:00+02:00")
    later = evidence("A", "2026-01-02T00:00:00Z", "failed")
    assert finalize_gate(task, True, True, True, [earlier, later], True, checks)[0] == "blocked"
    for timestamp in (None, "garbage", "2026-01-02T00:00:00"):
        invalid = evidence("A", timestamp, "failed")
        status, diagnostics = finalize_gate(task, True, True, True, [earlier, invalid], True, checks)
        assert status == "blocked" and any(d.code == "EPE-GATE-EVIDENCE-ORDER" for d in diagnostics)
    same_time_failed = evidence("A", "2026-01-01T23:00:00Z", "failed")
    assert finalize_gate(task, True, True, True, [earlier, same_time_failed], True, checks)[0] == "blocked"


def test_task_validation_rejects_unknown_and_invalid_revision():
    from epe.governance.tasks import validate_task
    base = {"id": "TASK-1", "type": "feature", "objective": "work", "acceptance": ["done"], "risk": "low", "target_entities": ["CLASS-1"]}
    for extra in ({"unknown": True}, {"schema_version": 2}, {"revision": 0}, {"revision": True}, {"revision": "1"}, {"acceptance": [1]}, {"target_entities": [None]}):
        task, diagnostics = validate_task({**base, **extra})
        assert task is None and diagnostics
    task, diagnostics = validate_task({**base, "schema_version": 1, "revision": 1})
    assert task is not None and not diagnostics


def test_changeset_transition_is_pure_and_requires_scope_for_completion():
    from epe.governance.baseline import transition_changeset
    value = {"id": "CHANGE-1", "status": "planned", "revision": 1}
    updated, errors = transition_changeset(value, "activate", expected_revision=1)
    assert not errors and updated["status"] == "active" and updated["revision"] == 2 and value["status"] == "planned"
    blocked, errors = transition_changeset(updated, "complete", expected_revision=2, scope_ok=False)
    assert blocked is None and errors
    aborted, errors = transition_changeset(updated, "abort", expected_revision=2)
    assert not errors and aborted["status"] == "aborted" and aborted["revision"] == 3


def test_unhashable_task_fields_are_diagnostics():
    from epe.governance.tasks import validate_task
    base = {"id": "TASK-1", "type": "feature", "objective": "work", "acceptance": ["done"], "risk": "low", "target_entities": ["CLASS-1"]}
    for patch in ({"type": []}, {"risk": {}}, {"status": []}, {3: "bad"}):
        task, diagnostics = validate_task({**base, **patch})
        assert task is None and diagnostics
