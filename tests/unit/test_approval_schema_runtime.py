from epe.design.manager import validate_approval_record


def test_approval_runtime_rejects_duplicate_risk_scope_values():
    record = {
        "schema_version": 1,
        "id": "APPROVAL-001",
        "entity_id": "CLASS-001",
        "revision": "a" * 64,
        "decision": "approved",
        "identity": {"id": "alice"},
        "authorization_source": "review",
        "timestamp": "2026-11-22T00:00:00Z",
        "risk_scope": ["low", "low"],
        "signature": "signature",
    }
    diagnostics = validate_approval_record(record)
    assert diagnostics and diagnostics[0].code == "EPE-APPROVAL-FIELDS"
