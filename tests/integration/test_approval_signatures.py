import json
import shutil
import subprocess

import pytest
import yaml

from epe.adapters.approval_identity import approval_payload
from epe.cli import main


pytestmark = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen unavailable")


def sign(tmp_path, key, record):
    payload_path = tmp_path / "approval-payload"
    payload_path.write_bytes(approval_payload(record))
    subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-n", "epe-approval", "-f", str(key), str(payload_path)], check=True, capture_output=True)
    record["signature"] = payload_path.with_name(payload_path.name + ".sig").read_text()
    payload_path.with_name(payload_path.name + ".sig").unlink()
    return record


def test_real_signature_forgery_risk_and_revocation(tmp_path, capsys):
    key = tmp_path.parent / (tmp_path.name + "-approver")
    attacker = tmp_path.parent / (tmp_path.name + "-attacker")
    for key_path in (key, attacker):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key_path)], check=True)
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "docs").mkdir()
    design = tmp_path / "docs/design.md"
    design.write_text("---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: draft\n---\n# Example\n")
    config_path = tmp_path / "engineering/epe.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["approval_trust"] = {"identities": {"alice": {"public_key": key.with_suffix(".pub").read_text().strip(), "kind": "human", "risk_scope": ["high"]}}}
    config_path.write_text(yaml.safe_dump(config))
    assert main(["--root", str(tmp_path), "--format", "json", "design", "validate", "CLASS-001"]) == 0
    revision = json.loads(capsys.readouterr().out)["data"]["revision"]
    record = {"schema_version": 1, "id": "APPROVAL-001", "entity_id": "CLASS-001", "revision": revision,
              "decision": "approved", "identity": {"id": "alice"}, "authorization_source": "review",
              "timestamp": "2026-11-19T00:00:00Z", "risk_scope": ["high"]}
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(sign(tmp_path, attacker, dict(record))))
    cmd = ["--root", str(tmp_path), "--format", "json", "design", "approve", "CLASS-001", "--record", "record.json"]
    assert main(cmd) == 1
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "EPE-APPROVAL-IDENTITY"
    signed = sign(tmp_path, key, dict(record))
    changed = dict(signed, risk_scope=["medium", "high"])
    record_path.write_text(json.dumps(changed))
    assert main(cmd) == 1
    capsys.readouterr()
    record_path.write_text(json.dumps(signed))
    assert main(cmd) == 0
    capsys.readouterr()
    assert main(cmd) == 0  # identical immutable import is idempotent
    capsys.readouterr()
    task = {"id": "TASK-001", "type": "feature", "objective": "test", "acceptance": ["ok"], "risk": "high", "target_entities": ["CLASS-001"]}
    (tmp_path / "task.json").write_text(json.dumps(task))
    assert main(["--root", str(tmp_path), "--format", "json", "task", "create", "--file", "task.json"]) == 0
    capsys.readouterr()
    check = ["--root", str(tmp_path), "--format", "json", "check", "--task", "TASK-001"]
    main(check)
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is True
    config["approval_trust"]["identities"]["alice"]["risk_scope"] = ["medium"]
    config_path.write_text(yaml.safe_dump(config))
    main(check)
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is False
    config["approval_trust"]["identities"]["alice"]["risk_scope"] = ["high"]
    config["approval_trust"]["identities"]["alice"]["kind"] = "service"
    config_path.write_text(yaml.safe_dump(config))
    main(check)
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is False
    config["approval_trust"]["identities"]["alice"]["kind"] = "human"
    config_path.write_text(yaml.safe_dump(config))
    original = design.read_bytes()
    design.write_bytes(original + b"changed\n")
    main(check)
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is False
    design.write_bytes(original)
    # A signed revocation references the original immutable approval.
    revoke = dict(record, id="APPROVAL-002", decision="revoked", supersedes="APPROVAL-001")
    record_path.write_text(json.dumps(sign(tmp_path, key, revoke)))
    assert main(cmd) == 0
    capsys.readouterr()
    assert main(check) != 0
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-GATE-APPROVAL" for d in result["diagnostics"])
    assert design.read_text().endswith("# Example\n")


def test_design_revision_binds_raw_extensions_and_rejects_symlink(tmp_path):
    from epe.core.models import Entity, SourceLocation
    from epe.design.manager import design_revision
    source = tmp_path / "design.md"; source.write_text("# design\n")
    entity = Entity(1, "CLASS-001", "Class", "Class", SourceLocation("design.md"), raw={"id": "CLASS-001", "type": "Class", "name": "Class", "extensions": {"owner": "a"}})
    first = design_revision(tmp_path, entity)
    entity.raw["extensions"]["owner"] = "b"
    second = design_revision(tmp_path, entity)
    assert first != second
    link = tmp_path / "linked.md"; link.symlink_to(source)
    entity.source = SourceLocation("linked.md")
    import pytest
    with pytest.raises(ValueError):
        design_revision(tmp_path, entity)


def test_audit_failure_leaves_approval_ineligible_until_signed_retry(tmp_path, capsys, monkeypatch):
    import epe.cli as cli
    key = tmp_path.parent / (tmp_path.name + "-key")
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    base = ["--root", str(tmp_path), "--format", "json"]
    assert main(base + ["init"]) == 0; capsys.readouterr()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/design.md").write_text("---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: draft\n---\n# Example\n")
    config_path = tmp_path / "engineering/epe.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["approval_trust"] = {"identities": {"alice": {"public_key": key.with_suffix('.pub').read_text().strip(), "kind": "human", "risk_scope": ["high"]}}}
    config_path.write_text(yaml.safe_dump(config))
    assert main(base + ["design", "validate", "CLASS-001"]) == 0
    revision = json.loads(capsys.readouterr().out)["data"]["revision"]
    record = {"schema_version": 1, "id": "APPROVAL-001", "entity_id": "CLASS-001", "revision": revision, "decision": "approved", "identity": {"id": "alice"}, "authorization_source": "review", "timestamp": "2026-11-19T00:00:00Z", "risk_scope": ["high"]}
    (tmp_path / "record.json").write_text(json.dumps(sign(tmp_path, key, record)))
    command = base + ["design", "approve", "CLASS-001", "--record", "record.json"]
    real_append = cli.append_audit
    monkeypatch.setattr(cli, "append_audit", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")))
    assert main(command) != 0
    assert any(d["code"] == "EPE-AUDIT-WRITE" for d in json.loads(capsys.readouterr().out)["diagnostics"])
    monkeypatch.setattr(cli, "append_audit", real_append)
    task = {"id": "TASK-001", "type": "feature", "objective": "test", "acceptance": ["ok"], "risk": "high", "target_entities": ["CLASS-001"]}
    (tmp_path / "task.json").write_text(json.dumps(task))
    assert main(base + ["task", "create", "--file", "task.json"]) == 0; capsys.readouterr()
    main(base + ["check", "--task", "TASK-001"])
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is False
    monkeypatch.setattr(cli, "append_audit", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")))
    assert main(command) != 0; capsys.readouterr()
    monkeypatch.setattr(cli, "append_audit", real_append)
    assert main(command) == 0; capsys.readouterr()
    main(base + ["check", "--task", "TASK-001"])
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is True
    events = (tmp_path / "engineering/audit/events.jsonl").read_text().splitlines()
    event_types = [json.loads(event)["event_type"] for event in events]
    assert event_types == ["task_created", "approval_committed"]
    assert main(command) == 0; capsys.readouterr()
    assert len((tmp_path / "engineering/audit/events.jsonl").read_text().splitlines()) == 2
    # A valid signed revocation must remain conservative if its audit append fails.
    revoked = dict(record, id="APPROVAL-002", decision="revoked", supersedes="APPROVAL-001")
    (tmp_path / "record.json").write_text(json.dumps(sign(tmp_path, key, revoked)))
    monkeypatch.setattr(cli, "append_audit", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")))
    assert main(command) != 0; capsys.readouterr()
    main(base + ["check", "--task", "TASK-001"])
    assert json.loads(capsys.readouterr().out)["data"]["design_ok"] is False
    monkeypatch.setattr(cli, "append_audit", real_append)
    assert main(command) == 0; capsys.readouterr()
    audit = tmp_path / "engineering/audit/events.jsonl"
    audit.write_text(audit.read_text() + "broken\n")
    assert main(command) != 0; capsys.readouterr()
    main(base + ["check", "--task", "TASK-001"])
    output = json.loads(capsys.readouterr().out)
    assert output["data"]["design_ok"] is False
    assert any(d["code"] == "EPE-AUDIT-INTEGRITY" for d in output["diagnostics"])
