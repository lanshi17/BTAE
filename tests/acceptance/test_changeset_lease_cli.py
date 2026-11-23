import json

from epe.cli import main


def setup_project(root, capsys):
    assert main(["--root", str(root), "init"]) == 0
    capsys.readouterr()
    tasks = root / "engineering/tasks"; tasks.mkdir(parents=True, exist_ok=True)
    changes = root / "engineering/changesets"; changes.mkdir(parents=True, exist_ok=True)
    (tasks / "TASK-001.json").write_text(json.dumps({"schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "lease", "acceptance": ["ok"], "risk": "low", "target_entities": ["MOD-001"], "changeset": "CHANGE-001", "status": "active", "revision": 1}))
    (changes / "CHANGE-001.json").write_text(json.dumps({"schema_version": 1, "id": "CHANGE-001", "task": "TASK-001", "owner": "alice", "affected_entities": ["MOD-001"], "write_scope": ["src/**"], "protected": [], "dependencies": [], "status": "active", "revision": 1}))


def test_lease_cli_lifecycle_and_inspect_is_read_only(tmp_path, capsys):
    setup_project(tmp_path, capsys)
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["changeset", "lease", "acquire", "CHANGE-001", "--owner", "alice", "--ttl", "30"]) == 0
    acquired = json.loads(capsys.readouterr().out)["data"]
    assert main(base + ["changeset", "lease", "inspect", "CHANGE-001"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["lease"]["lease_id"] == acquired["lease_id"]
    assert main(base + ["changeset", "lease", "release", "CHANGE-001", "--owner", "alice", "--lease-id", acquired["lease_id"]]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["released"] is True
    events = [json.loads(line)["event_type"] for line in (tmp_path / "engineering/audit/events.jsonl").read_text().splitlines()]
    assert events[-2:] == ["changeset_lease_acquired", "changeset_lease_released"]
    release_event = json.loads((tmp_path / "engineering/audit/events.jsonl").read_text().splitlines()[-1])
    assert release_event["payload"]["record_sha256"]


def test_lease_audit_failure_returns_recovery_record(tmp_path, capsys, monkeypatch):
    setup_project(tmp_path, capsys)
    import epe.cli as cli
    real_append = cli._append_state_audit
    monkeypatch.setattr(cli, "_append_state_audit", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("audit unavailable")))
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["changeset", "lease", "acquire", "CHANGE-001", "--owner", "alice", "--ttl", "30"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "error" and result["data"]["audit_recorded"] is False
    lease_id = result["data"]["lease"]["lease_id"]
    monkeypatch.setattr(cli, "_append_state_audit", real_append)
    assert main(base + ["changeset", "lease", "release", "CHANGE-001", "--owner", "alice", "--lease-id", lease_id]) == 0
    capsys.readouterr()
