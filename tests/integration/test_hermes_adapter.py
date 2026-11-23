import json
import subprocess
import sys
from pathlib import Path

import pytest

from epe.adapters.hosts.hermes import HermesHostAdapter
from epe.adapters.protocol import AgentRequest


def request():
    return AgentRequest("REQ-1", "verify", "TASK-1", "CHANGE-1", ("CLASS-1",), "a" * 64, ("src/**",), {}, {"source": "host", "id": "runner"})


def fake_command():
    code = "import json,sys; p=json.loads(sys.stdin.read()); print(json.dumps({'status':'ok','capabilities':{'protocol_version':'1','trusted_identity':True,'write_isolation':True,'process_group_control':True,'cancellation':True,'operations':['verify']}} if p.get('operation')=='capabilities' else {'status':'ok','response':{'decision':'accepted','reasons':['fake hermes']}}))"
    return [sys.executable, "-c", code]


def test_unconfigured_hermes_is_explicitly_unsupported():
    adapter = HermesHostAdapter()
    assert adapter.handshake().status == "unsupported-unintegrated"
    assert adapter.dispatch(request()).decision == "unsupported"


def signed_fake_command(key: Path):
    code = f'''import json, pathlib, subprocess, sys, tempfile
p=json.load(sys.stdin)
if p["operation"] == "capabilities":
 caps={{"protocol_version":"1","trusted_identity":True,"write_isolation":True,"process_group_control":True,"cancellation":True,"operations":["verify"]}}
 payload={{"protocol_version":"1","nonce":p["nonce"],"capabilities":caps}}
 with tempfile.TemporaryDirectory() as d:
  path=pathlib.Path(d)/"payload"
  path.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")))
  subprocess.run(["ssh-keygen","-Y","sign","-q","-n","epe-host-capability","-f",{str(key)!r},str(path)],check=True,capture_output=True)
  caps["attestation"]={{"identity":"hermes-runner","nonce":p["nonce"],"signature":path.with_name(path.name+".sig").read_text()}}
  print(json.dumps({{"status":"ok","capabilities":caps}}))
else:
 print(json.dumps({{"status":"ok","response":{{"decision":"accepted","reasons":["signed fixture"]}}}}))
'''
    return [sys.executable, "-c", code]


def test_configured_hermes_requires_and_uses_signed_handshake(tmp_path):
    key = tmp_path / "host-key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    config = {"host_trust": {"identities": {"hermes-runner": {
        "public_key": key.with_suffix(".pub").read_text().strip(), "operations": ["verify"]}}}}
    adapter = HermesHostAdapter(signed_fake_command(key), attestation_config=config)
    capabilities = adapter.handshake()
    assert capabilities.status == "handshaken"
    assert capabilities.write_isolation is True
    assert adapter.dispatch(request()).decision == "accepted"


def test_hermes_runs_bridge_in_explicit_repository_directory(tmp_path):
    code = ("import json,os,sys; p=json.load(sys.stdin); "
            "print(json.dumps({'status':'ok','capabilities':{'protocol_version':'1','operations':['verify']}} "
            "if p.get('operation')=='capabilities' else {'status':'ok','response':{'decision':'accepted','reasons':[os.getcwd()]}}))")
    adapter = HermesHostAdapter([sys.executable, "-c", code], cwd=tmp_path)
    assert adapter.dispatch(request()).reasons == [str(tmp_path)]


def test_legacy_trusted_flag_does_not_elevate_unsigned_capabilities():
    code = "import json; print(json.dumps({'status':'ok','capabilities':{'protocol_version':'1','trusted_identity':True,'write_isolation':True,'operations':['start_implementation']}}))"
    adapter = HermesHostAdapter([sys.executable, "-c", code], trusted_capabilities=True)
    capabilities = adapter.handshake()
    assert capabilities.status == "handshaken-untrusted"
    assert capabilities.operations == ()
    assert not capabilities.trusted_identity and not capabilities.write_isolation


def test_hermes_rejects_handshake_protocol_mismatch():
    code = "import json; print(json.dumps({'status':'ok','capabilities':{'protocol_version':'2','operations':['verify']}}))"
    adapter = HermesHostAdapter([sys.executable, "-c", code])
    assert adapter.handshake().status == "handshake-failed"


def test_hermes_rejects_oversized_handshake_output():
    code = "import sys; sys.stdout.write('x' * (2*1024*1024))"
    adapter = HermesHostAdapter([sys.executable, "-c", code], timeout=2)
    assert adapter.handshake().status == "handshake-failed"


def test_hermes_rejects_timeout_without_hanging():
    code = "import time; time.sleep(30)"
    adapter = HermesHostAdapter([sys.executable, "-c", code], timeout=0.2)
    assert adapter.handshake().status == "handshake-failed"


def test_hermes_rejects_response_if_request_was_not_fully_sent(monkeypatch):
    from epe.adapters.process import ProcessResult
    import epe.adapters.hosts.hermes as hermes
    response = json.dumps({"status": "ok", "capabilities": {"protocol_version": "1", "operations": ["verify"]}})
    monkeypatch.setattr(hermes, "run_process", lambda *args, **kwargs: ProcessResult([], 0, response, "", 0.1, stdin_incomplete=True))
    assert HermesHostAdapter([sys.executable]).handshake().status == "handshake-failed"


@pytest.mark.parametrize("capabilities", [
    {"operations": None}, {"operations": "verify"}, {"operations": ["verify", 1]},
    {"operations": ["verify"], "write_isolation": "false"},
    {"operations": ["verify"], "trusted_identity": 1},
    {"operations": ["verify"], "cancellation": None},
])
def test_hermes_rejects_malformed_capabilities(capabilities):
    payload = json.dumps({"status": "ok", "capabilities": capabilities})
    command = [sys.executable, "-c", f"print({payload!r})"]
    result = HermesHostAdapter(command, trusted_capabilities=True).handshake()
    assert result.status == "handshake-failed"
    assert not result.write_isolation and not result.trusted_identity


@pytest.mark.parametrize("response", [
    {"decision": []}, {"decision": "accepted", "reasons": "ok"},
    {"decision": "accepted", "evidence_ids": None},
    {"decision": "accepted", "next_steps": [1]},
])
def test_hermes_rejects_malformed_dispatch_response(response):
    handshake = {"status": "ok", "capabilities": {"protocol_version": "1", "operations": ["verify"]}}
    operation = {"status": "ok", "response": response}
    code = ("import json,sys; p=json.load(sys.stdin); "
            f"print(json.dumps({handshake!r} if p['operation']=='capabilities' else {operation!r}))")
    assert HermesHostAdapter([sys.executable, "-c", code]).dispatch(request()).decision == "error"


def test_hermes_preserves_structured_diagnostics():
    handshake = {"status": "ok", "capabilities": {"protocol_version": "1", "operations": ["verify"]}}
    operation = {"status": "ok", "response": {"decision": "blocked", "reasons": ["gate"],
        "diagnostics": [{"code": "EPE-GATE", "severity": "error", "message": "阻断", "line": 2}],
        "evidence_ids": [], "next_steps": ["修复"]}}
    code = ("import json,sys; p=json.load(sys.stdin); "
            f"print(json.dumps({handshake!r} if p['operation']=='capabilities' else {operation!r}, ensure_ascii=False))")
    response = HermesHostAdapter([sys.executable, "-c", code]).dispatch(request())
    assert response.decision == "blocked"
    assert response.diagnostics[0].code == "EPE-GATE"
    assert response.diagnostics[0].line == 2


@pytest.mark.parametrize("diagnostics", [
    [{"severity": "error", "message": "missing code"}],
    [{"code": "EPE", "severity": "fatal", "message": "bad severity"}],
    [{"code": "EPE", "severity": "error", "message": "unknown", "extra": True}],
    [{"code": "EPE", "severity": "error", "message": "bad line", "line": 0}],
    "not-an-array",
])
def test_hermes_rejects_malformed_structured_diagnostics(diagnostics):
    handshake = {"status": "ok", "capabilities": {"protocol_version": "1", "operations": ["verify"]}}
    operation = {"status": "ok", "response": {"decision": "blocked", "reasons": [],
        "diagnostics": diagnostics, "evidence_ids": [], "next_steps": []}}
    code = ("import json,sys; p=json.load(sys.stdin); "
            f"print(json.dumps({handshake!r} if p['operation']=='capabilities' else {operation!r}))")
    response = HermesHostAdapter([sys.executable, "-c", code]).dispatch(request())
    assert response.decision == "error"
    assert response.diagnostics[0].code == "EPE-HOST-RESPONSE"
