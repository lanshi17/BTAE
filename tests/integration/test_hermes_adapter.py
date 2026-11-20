import json
import sys

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


def test_configured_hermes_requires_and_uses_handshake():
    adapter = HermesHostAdapter(fake_command(), trusted_capabilities=True)
    capabilities = adapter.handshake()
    assert capabilities.status == "handshaken"
    assert capabilities.write_isolation is True
    assert adapter.dispatch(request()).decision == "accepted"


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
