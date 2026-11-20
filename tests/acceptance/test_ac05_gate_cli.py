from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest
import yaml

from epe.adapters.approval_identity import approval_payload


SOURCE = Path(__file__).resolve().parents[2] / "src"


def cli(root: Path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(root), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=root, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        result = json.loads(process.stdout)
        assert result["command"] and isinstance(result["diagnostics"], list)
        assert process.returncode == expected, result
        return result
    return run


def prepare(root: Path, *, design: bool, risk: str = "low", wide_scope: bool = False, trust: dict | None = None):
    run = cli(root)
    assert run("init")["status"] == "passed"
    (root / "docs").mkdir(exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "README.md").write_text("protected baseline\n", encoding="utf-8")
    if design:
        (root / "docs/design.md").write_text(
            "---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: reviewed\n---\n# Example\n",
            encoding="utf-8",
        )
    config_path = root / "engineering/epe.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if trust is not None:
        config["approval_trust"] = trust
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (root / "engineering/policies/verification.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "checks": [{"id": "gate-check", "command": [sys.executable, "-c", "pass"], "version": "1"}],
    }, sort_keys=False), encoding="utf-8")
    (root / "task.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "AC-05 gate",
        "acceptance": ["all gate facts are current"], "risk": risk,
        "target_entities": ["CLASS-001"], "changeset": "CHANGE-001",
    }, sort_keys=False), encoding="utf-8")
    (root / "change.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "CHANGE-001", "task": "TASK-001", "owner": "developer",
        "affected_entities": ["CLASS-001"],
        "write_scope": ["**"] if wide_scope else ["src/**", "tests/**"],
        "protected": [] if wide_scope else ["README.md"],
        "dependencies": [], "status": "planned",
    }, sort_keys=False), encoding="utf-8")
    run("task", "create", "--file", "task.yaml")
    run("task", "transition", "TASK-001", "activate")
    run("changeset", "create", "--file", "change.yaml")
    run("changeset", "transition", "CHANGE-001", "activate")
    run("graph", "build")
    run("verify", "TASK-001")
    return run


def test_ac05_missing_design_and_high_risk_without_approval_block(tmp_path):
    missing = tmp_path / "missing-design"
    missing.mkdir()
    run = prepare(missing, design=False)
    result = run("check", "--task", "TASK-001", expected=1)
    assert result["status"] == "blocked"
    assert any(item["code"] == "EPE-DESIGN-MISSING" for item in result["diagnostics"])

    high = tmp_path / "high-risk"
    high.mkdir()
    run = prepare(high, design=True, risk="high")
    result = run("check", "--task", "TASK-001", expected=1)
    assert result["status"] == "blocked"
    assert any(item["code"] == "EPE-GATE-APPROVAL" for item in result["diagnostics"])


def test_ac05_signed_approval_becomes_stale_when_design_changes(tmp_path):
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen unavailable")
    with tempfile.TemporaryDirectory(prefix="epe-ac05-key-") as key_dir:
        key = Path(key_dir) / "approver"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
        identity = {"alice": {"public_key": key.with_suffix(".pub").read_text().strip(), "kind": "human", "risk_scope": ["high"]}}
        run = prepare(tmp_path, design=True, risk="high", wide_scope=True, trust={"identities": identity})
        revision_result = run("design", "validate", "CLASS-001")
        record = {
            "schema_version": 1, "id": "APPROVAL-001", "entity_id": "CLASS-001",
            "revision": revision_result["data"]["revision"], "decision": "approved",
            "identity": {"id": "alice"}, "authorization_source": "AC-05 acceptance",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "risk_scope": ["high"],
        }
        payload = approval_payload(record)
        payload_path = tmp_path / "approval-payload"
        payload_path.write_bytes(payload)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-n", "epe-approval", "-f", str(key), str(payload_path)], check=True, capture_output=True)
        record["signature"] = payload_path.with_name(payload_path.name + ".sig").read_text(encoding="utf-8")
        approval_path = tmp_path / "approval.json"
        approval_path.write_text(json.dumps(record), encoding="utf-8")
        run("design", "approve", "CLASS-001", "--record", "approval.json")
        assert run("check", "--task", "TASK-001")["status"] == "passed"

        design_path = tmp_path / "docs/design.md"
        design_path.write_text(design_path.read_text(encoding="utf-8") + "\nRevision changed after approval.\n", encoding="utf-8")
        run("graph", "build")
        run("verify", "TASK-001")
        stale = run("check", "--task", "TASK-001", expected=1)
        assert stale["status"] == "blocked"
        assert any(item["code"] == "EPE-GATE-APPROVAL" for item in stale["diagnostics"])


def test_ac05_out_of_scope_write_blocks_check(tmp_path):
    run = prepare(tmp_path, design=True)
    (tmp_path / "README.md").write_text("changed outside declared scope\n", encoding="utf-8")
    result = run("check", "--task", "TASK-001", expected=1)
    assert result["status"] in {"blocked", "error"}
    assert any(item["code"] == "EPE-GATE-SCOPE" for item in result["diagnostics"])
