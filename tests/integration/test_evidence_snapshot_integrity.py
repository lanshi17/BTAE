import json
import sys

from epe.core.registry import Registry
from epe.graph.builder import build_graph, load_graph
from epe.parsers.python import parse_python
from epe.verification.runner import evidence_validity, run_checks


def config():
    return {"managed": {"design_roots": ["docs"], "code_roots": ["src"],
                        "test_roots": ["tests"], "contract_roots": []},
            "policies": {"verification": "engineering/policies/verification.yaml"}}


def test_change_during_real_check_remains_stale(tmp_path):
    (tmp_path / "src").mkdir()
    source = tmp_path / "src/a.py"
    source.write_text("value = 1\n")
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    command = [sys.executable, "-c", "from pathlib import Path; Path('src/a.py').write_text('value = 2\\n')"]
    policy.write_text(json.dumps({"checks": [{"id": "mutate", "command": command}]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
    assert not diagnostics
    assert evidence[0]["result"] == "passed"
    assert evidence[0]["validity"] == "stale"
    assert evidence_validity(tmp_path, config(), evidence[0]) == "stale"


def test_custom_policy_changes_invalidate_evidence_even_when_excluded(tmp_path):
    cfg = config()
    cfg["policies"]["verification"] = "custom/verification.json"
    cfg["exclude"] = ["custom"]
    policy = tmp_path / "custom/verification.json"
    policy.parent.mkdir()
    check = {"id": "check", "command": [sys.executable, "-c", "pass"]}
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, diagnostics = run_checks(tmp_path, cfg, "TASK-001")
    assert not diagnostics
    assert evidence_validity(tmp_path, cfg, evidence[0], check) == "valid"
    policy.write_text(policy.read_text() + "\n")
    assert evidence_validity(tmp_path, cfg, evidence[0], check) == "stale"
    policy.unlink()
    assert evidence_validity(tmp_path, cfg, evidence[0], check) == "unknown"


def test_custom_policy_modified_by_check_marks_run_stale(tmp_path):
    cfg = config()
    cfg["policies"]["verification"] = "custom/verification.json"
    policy = tmp_path / "custom/verification.json"
    policy.parent.mkdir()
    command = [sys.executable, "-c", "from pathlib import Path; p=Path('custom/verification.json'); p.write_text(p.read_text()+'\\n')"]
    policy.write_text(json.dumps({"checks": [{"id": "change-policy", "command": command}]}))
    evidence, diagnostics = run_checks(tmp_path, cfg, "TASK-001")
    assert not diagnostics
    assert evidence[0]["result"] == "passed"
    assert evidence[0]["validity"] == "stale"
    assert evidence_validity(tmp_path, cfg, evidence[0]) == "stale"


def test_graph_rejects_changed_inputs_and_tampering(tmp_path):
    (tmp_path / "src").mkdir()
    source = tmp_path / "src/a.py"
    source.write_text("class A: pass\n")
    cfg = config()
    built = build_graph(tmp_path, Registry(), [parse_python(source.read_bytes(), "src/a.py")], cfg)
    assert built.published and load_graph(tmp_path, cfg)[0] is not None
    source.write_text("class B: pass\n")
    assert load_graph(tmp_path, cfg)[1][0].code == "EPE-GRAPH-STALE"
    source.write_text("class A: pass\n")
    path = tmp_path / ".engineering/generations" / built.snapshot["content_digest"] / "graph.json"
    snapshot = json.loads(path.read_text())
    snapshot["nodes"] = []
    path.write_text(json.dumps(snapshot))
    assert load_graph(tmp_path, cfg)[1][0].code == "EPE-GRAPH-INTEGRITY"


def test_unknown_test_runner_cannot_claim_success(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "unknown", "kind": "test", "command": [sys.executable, "-c", "print('ok')"]}]}))
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence[0]["result"] == "error"
    assert evidence[0]["termination_reason"] == "unsupported_test_parser"


def test_environment_mismatch_is_unknown(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "ok", "command": [sys.executable, "-c", "pass"]}]}))
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence_validity(tmp_path, config(), evidence[0]) == "valid"
    evidence[0]["environment"]["python"] = "0.0.0"
    assert evidence_validity(tmp_path, config(), evidence[0]) == "unknown"


def test_evidence_expiration_and_clock_uncertainty(tmp_path):
    class Clock:
        def __init__(self, value): self.value = value
        def now_utc(self): return self.value
        def monotonic(self): return 0

    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    check = {"id": "ok", "command": [sys.executable, "-c", "pass"], "max_age_seconds": 60}
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001", clock=Clock("2026-01-01T00:00:00Z"))
    assert not diagnostics
    record = evidence[0]
    assess = lambda time: evidence_validity(tmp_path, config(), record, check, Clock(time))
    assert assess("2026-01-01T00:01:00Z") == "valid"
    assert assess("2026-01-01T00:01:01Z") == "stale"
    assert assess("2025-12-31T23:59:59Z") == "unknown"
    assert assess("2026-01-01T00:00:00") == "unknown"
    record["finished_at"] = "invalid"
    assert assess("2026-01-01T00:00:00Z") == "unknown"
    assert evidence_validity(tmp_path, config(), record, {"id": "ok"}, Clock("2030-01-01T00:00:00Z")) == "valid"


def test_invalid_evidence_expiration_is_rejected_by_policy(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    for age in (0, -1, True, 1.5, "60"):
        check = {"id": "invalid", "command": [sys.executable, "-c", "pass"], "max_age_seconds": age}
        policy.write_text(json.dumps({"checks": [check]}))
        evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
        assert not evidence and diagnostics, age


def test_evidence_schema_rejects_extra_fields_but_legacy_environment_is_unknown(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "ok", "command": [sys.executable, "-c", "pass"]}]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
    assert not diagnostics
    record = evidence[0]
    record.pop("environment")
    assert evidence_validity(tmp_path, config(), record) == "unknown"
    record["unexpected"] = True
    record_path = tmp_path / "engineering/evidence" / record["run_id"] / "evidence.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    loaded, diagnostics = __import__("epe.verification.runner", fromlist=["load_evidence"]).load_evidence(tmp_path, config(), "TASK-001")
    assert not loaded and any(item.code == "EPE-EVIDENCE-READ" for item in diagnostics)


def test_allowed_environment_is_filtered_and_values_are_not_recorded(tmp_path, monkeypatch):
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    monkeypatch.setenv("EPE_SECRET_FIXTURE", "do-not-pass")
    command = [sys.executable, "-c", "import os,sys; sys.exit(1 if os.getenv('EPE_SECRET_FIXTURE') else 0)"]
    check = {"id": "filtered", "command": command, "allowed_env": ["PATH"]}
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
    assert not diagnostics and evidence[0]["result"] == "passed"
    provenance = evidence[0]["provenance"]
    assert provenance["environment_mode"] == "allowlist"
    assert provenance["allowed_env"] == ["PATH"]
    assert "do-not-pass" not in json.dumps(evidence)


def test_verification_policy_rejects_symlinked_parent_directory(tmp_path):
    from epe.verification.runner import run_checks
    outside = tmp_path / "outside-policy"; outside.mkdir()
    (outside / "verification.json").write_text(json.dumps({"checks": [{"id": "ok", "command": [sys.executable, "-c", "pass"]}]}), encoding="utf-8")
    (tmp_path / "custom").symlink_to(outside, target_is_directory=True)
    cfg = config(); cfg["policies"]["verification"] = "custom/verification.json"
    evidence, diagnostics = run_checks(tmp_path, cfg, "TASK-001")
    assert not evidence and diagnostics[0].code == "EPE-VERIFY-POLICY"


def test_real_pytest_requires_executed_tests(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"
    policy.parent.mkdir(parents=True)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text("def test_pass():\n    assert True\n")
    check = {"id": "pytest", "kind": "test", "result_parser": "pytest",
             "command": [sys.executable, "-m", "pytest", "-q", "tests"]}
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
    assert not diagnostics
    assert evidence[0]["result"] == "passed"
    (tests / "test_sample.py").write_text("# no tests\n")
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence[0]["result"] != "passed"


def test_required_artifact_must_be_updated_by_the_run(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    artifact = tmp_path / "result.txt"; artifact.write_text("old")
    check = {"id": "artifact", "command": [sys.executable, "-c", "pass"], "artifacts": ["result.txt"]}
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
    assert not diagnostics
    assert evidence[0]["result"] == "error" and evidence[0]["termination_reason"] == "artifact_not_updated"
    assert evidence_validity(tmp_path, config(), evidence[0]) == "valid"
    check["command"] = [sys.executable, "-c", "from pathlib import Path; Path('result.txt').write_text('old')"]
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence[0]["result"] == "passed"
    assert any(a["path"] == "result.txt" for a in evidence[0]["artifacts"])
    artifact.unlink()
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence[0]["result"] == "passed"


def test_invalid_artifact_configuration_does_not_run(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    for invalid in ("result.txt", ["../outside"], ["result.txt", "result.txt"]):
        check = {"id": "bad", "command": [sys.executable, "-c", "raise RuntimeError('must not run')"], "artifacts": invalid}
        policy.write_text(json.dumps({"checks": [check]}))
        evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
        assert not evidence and diagnostics[0].code == "EPE-VERIFY-CONFIG"


def test_pytest_gate_rejects_fake_summary_and_conflicting_output(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    for command in ([sys.executable, "-c", "print('1 passed')"],
                    [sys.executable, "-m", "pytest", "--junitxml=chosen.xml"]):
        policy.write_text(json.dumps({"checks": [{"id": "test", "kind": "test", "result_parser": "pytest", "command": command}]}))
        evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
        assert not diagnostics and evidence[0]["result"] == "error"
        assert evidence[0]["termination_reason"] == "unsupported_pytest_command"
        assert evidence[0]["provenance"]["effective_command"] == []


def test_pytest_gate_uses_case_results_for_skips_and_passes(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    tests = tmp_path / "tests"; tests.mkdir()
    test_file = tests / "test_sample.py"
    check = {"id": "test", "kind": "test", "result_parser": "pytest", "command": [sys.executable, "-m", "pytest", "-q", "tests"]}
    policy.write_text(json.dumps({"checks": [check]}))
    test_file.write_text("import pytest\n@pytest.mark.skip(reason='skip')\ndef test_skip(): pass\n")
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence[0]["result"] == "error" and evidence[0]["termination_reason"] == "test_execution_unconfirmed"
    test_file.write_text("def test_ok(): pass\n")
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    assert evidence[0]["result"] == "passed"
    assert evidence[0]["command"] == check["command"]
    assert evidence[0]["provenance"]["effective_command"][-1].startswith("--junitxml=")
    summary = next(a for a in evidence[0]["artifacts"] if a["path"].endswith("test-summary.json"))
    assert json.loads((tmp_path / summary["path"]).read_text())["passed"] == 1
    assert not list((tmp_path / "engineering/evidence").glob("*/pytest-result.xml"))


def test_test_gate_rejects_legacy_or_inconsistent_pass_evidence(tmp_path):
    import copy
    from types import SimpleNamespace
    from epe.governance.gates import finalize_gate
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    tests = tmp_path / "tests"; tests.mkdir()
    (tests / "test_pass.py").write_text("def test_pass(): pass\n")
    check = {"id": "pytest", "kind": "test", "result_parser": "pytest", "command": [sys.executable, "-m", "pytest", "-q", "tests"]}
    policy.write_text(json.dumps({"checks": [check]}))
    evidence, _ = run_checks(tmp_path, config(), "TASK-001")
    record = evidence[0]
    task = SimpleNamespace(id="TASK-001", changeset=None)
    assert evidence_validity(tmp_path, config(), record, check) == "valid"
    assert finalize_gate(task, True, True, True, [record], True, [check])[0] == "passed"
    legacy = copy.deepcopy(record); del legacy["provenance"]["test_protocol"]
    assert evidence_validity(tmp_path, config(), legacy, check) == "unknown"
    assert finalize_gate(task, True, True, True, [legacy], True, [check])[0] == "blocked"
    wrong_command = copy.deepcopy(record); wrong_command["provenance"]["effective_command"] = check["command"]
    assert evidence_validity(tmp_path, config(), wrong_command, check) == "unknown"
    no_summary = copy.deepcopy(record)
    no_summary["artifacts"] = [a for a in no_summary["artifacts"] if not a["path"].endswith("test-summary.json")]
    no_summary["validity"] = evidence_validity(tmp_path, config(), no_summary, check)
    assert no_summary["validity"] == "unknown"
    assert finalize_gate(task, True, True, True, [no_summary], True, [check])[0] == "blocked"
    summary = next(a for a in record["artifacts"] if a["path"].endswith("test-summary.json"))
    (tmp_path / summary["path"]).write_text('{"passed": 0, "failed": 0, "skipped": 0}')
    assert evidence_validity(tmp_path, config(), record, check) == "invalid"


def test_evidence_marks_truncated_process_output(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    command = [sys.executable, "-c", "import os; os.write(1, b'x'*(2*1024*1024)); os.write(2, b'y'*(2*1024*1024))"]
    policy.write_text(json.dumps({"checks": [{"id": "verbose", "command": command}]}))
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001")
    assert not diagnostics and evidence[0]["result"] == "passed"
    assert evidence[0]["provenance"]["output_truncated"] == {"stdout": True, "stderr": True}
    log = next(item for item in evidence[0]["artifacts"] if item["path"].endswith("output.log"))
    assert (tmp_path / log["path"]).stat().st_size < 3 * 1024 * 1024


def test_verification_cancellation_is_recorded_as_error(tmp_path):
    import threading
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "long", "command": [sys.executable, "-c", "import time; time.sleep(30)"]}]}))
    cancelled = threading.Event()
    timer = threading.Timer(0.2, cancelled.set); timer.start()
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-001", cancel_event=cancelled)
    timer.cancel()
    assert not diagnostics and len(evidence) == 1
    assert evidence[0]["result"] == "error" and evidence[0]["termination_reason"] == "cancelled"


def test_invalid_evidence_root_is_rejected_before_check_executes(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    marker = tmp_path / "executed"
    command = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('yes')"]
    policy.write_text(json.dumps({"checks": [{"id": "must-not-run", "command": command}]}))
    cfg = config(); cfg["storage"] = {"evidence": "../outside"}
    evidence, diagnostics = run_checks(tmp_path, cfg, "TASK-1")
    assert not evidence and diagnostics and diagnostics[0].code == "EPE-VERIFY-ARTIFACT"
    assert not marker.exists()


def test_evidence_record_is_published_as_no_overwrite_artifact(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "ok", "command": [sys.executable, "-c", "pass"]}]}))
    records, diagnostics = run_checks(tmp_path, config(), "TASK-1")
    assert not diagnostics and len(records) == 1
    path = tmp_path / "engineering/evidence" / records[0]["run_id"] / "evidence.json"
    stored = json.loads(path.read_text())
    assert stored["id"] == records[0]["id"] and stored["result"] == "passed"


def test_artifact_store_failure_cannot_return_completed_evidence(tmp_path, monkeypatch):
    from epe.adapters.artifact_store import ArtifactStore
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "ok", "command": [sys.executable, "-c", "pass"]}]}))
    def fail_write(self, relative_path, data):
        raise OSError("simulated disk full")
    monkeypatch.setattr(ArtifactStore, "write", fail_write)
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-1")
    assert evidence == []
    assert any(d.code == "EPE-VERIFY-ARTIFACT" for d in diagnostics)
    assert not list((tmp_path / "engineering/evidence").glob("*/evidence.json"))


def test_verification_uses_injected_clock_for_evidence_timestamps(tmp_path):
    policy = tmp_path / "engineering/policies/verification.yaml"; policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"checks": [{"id": "ok", "command": [sys.executable, "-c", "pass"]}]}))
    class FixedClock:
        def __init__(self): self.values = iter(["2026-01-02T03:04:05Z", "2026-01-02T03:04:06Z"])
        def now_utc(self): return next(self.values)
        def monotonic(self): return 1.0
    evidence, diagnostics = run_checks(tmp_path, config(), "TASK-1", clock=FixedClock())
    assert not diagnostics and evidence[0]["started_at"] == "2026-01-02T03:04:05Z"
    assert evidence[0]["finished_at"] == "2026-01-02T03:04:06Z"
