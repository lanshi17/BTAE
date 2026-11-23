import pytest

from epe.governance.conflicts import detect_changeset_conflicts


def change(identifier, write_scope, protected=(), status="active"):
    return {"id": identifier, "owner": identifier.lower(), "write_scope": list(write_scope),
            "protected": list(protected), "status": status}


def test_detects_write_and_protected_overlaps_with_stable_records():
    conflicts = detect_changeset_conflicts([
        change("CHANGE-002", ["src/**"], ["docs/api.md"]),
        change("CHANGE-001", ["src/epe/cli.py"], ["src/epe/hosts.py"]),
    ])
    assert [(item["left"]["id"], item["right"]["id"], item["left"]["field"], item["right"]["field"])
            for item in conflicts] == [
                ("CHANGE-001", "CHANGE-002", "protected", "write_scope"),
                ("CHANGE-001", "CHANGE-002", "write_scope", "write_scope"),
            ]
    assert all(item["conservative"] for item in conflicts)


def test_ignores_completed_changesets_and_disjoint_paths():
    assert detect_changeset_conflicts([
        change("CHANGE-001", ["src/**"], status="completed"),
        change("CHANGE-002", ["docs/**"]),
    ]) == []


def test_rejects_invalid_scope_declarations():
    with pytest.raises(ValueError):
        detect_changeset_conflicts([change("CHANGE-001", ["../outside"])])
