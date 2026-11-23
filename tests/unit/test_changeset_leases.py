from datetime import datetime, timedelta, timezone

import pytest

import epe.governance.leases as leases
from epe.governance.leases import LeaseConflict, LeaseError, acquire_lease, inspect_lease, release_lease, renew_lease


def config():
    return {"storage": {"changesets": "engineering/changesets", "derived": ".engineering"}}


def change(revision=1, status="active"):
    return {"id": "CHANGE-001", "task": "TASK-001", "owner": "alice", "affected_entities": ["MOD-001"],
            "write_scope": ["src/**"], "protected": [], "dependencies": [], "status": status, "revision": revision}


def test_lease_acquire_renew_release_and_inspect(tmp_path):
    value = acquire_lease(tmp_path, config(), change(), "alice", 30)
    assert value["owner"] == "alice" and value["revision"] == 1
    current = inspect_lease(tmp_path, config(), "CHANGE-001")
    assert current and current["expired"] is False
    renewed = renew_lease(tmp_path, config(), change(), "alice", value["lease_id"], 60)
    assert renewed["expires_at"] != value["expires_at"]
    assert release_lease(tmp_path, config(), "CHANGE-001", "alice", value["lease_id"]) is True
    assert inspect_lease(tmp_path, config(), "CHANGE-001") is None


def test_lease_conflicts_and_revision_mismatch(tmp_path):
    value = acquire_lease(tmp_path, config(), change(), "alice", 30)
    with pytest.raises(LeaseConflict):
        acquire_lease(tmp_path, config(), change(), "alice", 30)
    with pytest.raises(LeaseConflict):
        renew_lease(tmp_path, config(), change(revision=2), "alice", value["lease_id"], 30)
    with pytest.raises(LeaseConflict):
        release_lease(tmp_path, config(), "CHANGE-001", "bob", value["lease_id"])


def test_expired_lease_is_recovered_and_invalid_ttl_is_rejected(tmp_path, monkeypatch):
    initial = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(leases, "_now", lambda: initial)
    old = acquire_lease(tmp_path, config(), change(), "alice", 1)
    monkeypatch.setattr(leases, "_now", lambda: initial + timedelta(seconds=2))
    replacement = acquire_lease(tmp_path, config(), change(), "alice", 1)
    assert replacement["lease_id"] != old["lease_id"]
    with pytest.raises(LeaseError):
        acquire_lease(tmp_path, config(), change(), "alice", 0)
