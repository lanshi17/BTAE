import json
import sys
import time
import threading
from pathlib import Path

import pytest

import epe.adapters.hosts.acp as acp_module
from epe.adapters.hosts.acp import ACPProtocolError, ACPSessionClosed, HermesACPAdapter


def command(body: str) -> list[str]:
    return [sys.executable, "-c", "import json,sys,time; sys.stdin.readline(); " + body]


def response(protocol=1, request_id=1, name="fixture"):
    return json.dumps({"jsonrpc": "2.0", "id": request_id,
                       "result": {"protocolVersion": protocol, "agentInfo": {"name": name, "version": "1"}}})


def test_handshake_is_explicitly_untrusted_and_has_no_workflow_operations(tmp_path: Path):
    body = f"print({response()!r}, flush=True); time.sleep(10)"
    result = HermesACPAdapter(command(body), tmp_path, timeout=2).handshake()
    assert result.status == "handshaken-untrusted"
    assert not result.trusted_identity and not result.write_isolation
    assert result.operations == () and result.process_group_control is True


@pytest.mark.parametrize("body", [
    "print('not-json', flush=True)",
    f"print({response(request_id=2)!r}, flush=True)",
    f"print({response(protocol=2)!r}, flush=True)",
])
def test_malformed_handshake_fails_closed(tmp_path: Path, body: str):
    assert HermesACPAdapter(command(body), tmp_path, timeout=2).handshake().status == "handshake-failed"


def test_timeout_and_output_limit_fail_closed(tmp_path: Path):
    assert HermesACPAdapter(command("time.sleep(10)"), tmp_path, timeout=0.1).handshake().status == "handshake-failed"
    assert HermesACPAdapter(command("print('x'*1000, flush=True)"), tmp_path, timeout=2, output_limit=64).handshake().status == "handshake-failed"


def session_fixture():
    script = r'''
import json,sys
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentInfo":{"name":"fixture","version":"1"}}}), flush=True)
    elif req["method"] == "session/new":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"SESSION-1"}}), flush=True)
    elif req["method"] == "session/prompt":
        assert req["params"]["sessionId"] == "SESSION-1"
        assert req["params"]["prompt"][0]["type"] == "text"
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"stopReason":"end_turn"}}), flush=True)
'''
    return [sys.executable, "-c", script]


def test_open_session_is_explicit_and_disables_mcp(tmp_path: Path):
    with HermesACPAdapter(session_fixture(), tmp_path, timeout=2).open_session() as session:
        assert session.session_id == "SESSION-1"


def test_open_session_rejects_missing_session_id(tmp_path: Path):
    script = "import json,sys; [print(json.dumps({'jsonrpc':'2.0','id':json.loads(x)['id'],'result':{'protocolVersion':1,'agentInfo':{'name':'fixture'}} if json.loads(x)['method']=='initialize' else {'result':{}}}),flush=True) for x in sys.stdin]"
    with pytest.raises(ValueError, match="sessionId"):
        HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=2).open_session()


def test_prompt_is_explicit_text_only_and_returns_transport_result(tmp_path: Path):
    with HermesACPAdapter(session_fixture(), tmp_path, timeout=2).open_session() as session:
        assert session.prompt("hello") == {"stopReason": "end_turn"}
        with pytest.raises(ValueError, match="empty"):
            session.prompt(" ")


def test_cancel_sends_notification_and_unblocks_prompt(tmp_path: Path):
    script = r'''
import json,sys
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentInfo":{"name":"fixture"}}}),flush=True)
    elif req["method"] == "session/new":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"SESSION-1"}}),flush=True)
    elif req["method"] == "session/prompt":
        continue
    elif req["method"] == "session/cancel":
        print(json.dumps({"jsonrpc":"2.0","id":3,"result":{"stopReason":"cancelled"}}),flush=True)
'''
    with HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=2).open_session() as session:
        result = []
        worker = threading.Thread(target=lambda: result.append(session.prompt("slow")))
        worker.start(); time.sleep(0.1); session.cancel(); worker.join(timeout=2)
        assert result == [{"stopReason": "cancelled"}]


def test_close_wakes_pending_prompt_and_is_idempotent(tmp_path: Path):
    script = r'''
import json,sys,time
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentInfo":{"name":"fixture"}}}),flush=True)
    elif req["method"] == "session/new":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"SESSION-1"}}),flush=True)
    elif req["method"] == "session/prompt":
        time.sleep(30)
'''
    with HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=30).open_session() as session:
        errors = []

        def wait_for_prompt():
            try:
                session.prompt("slow")
            except BaseException as exc:  # assert the exact protocol error below
                errors.append(exc)

        worker = threading.Thread(target=wait_for_prompt)
        worker.start()
        time.sleep(0.1)
        session.close()
        session.close()
        worker.join(timeout=2)
        assert not worker.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], ACPSessionClosed)


def test_concurrent_prompts_fail_before_sharing_response_reader(tmp_path: Path):
    marker = tmp_path / "prompt-started"
    script = f'''
import json,sys,time
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        print(json.dumps({{"jsonrpc":"2.0","id":req["id"],"result":{{"protocolVersion":1,"agentInfo":{{"name":"fixture"}}}}}}),flush=True)
    elif req["method"] == "session/new":
        print(json.dumps({{"jsonrpc":"2.0","id":req["id"],"result":{{"sessionId":"SESSION-1"}}}}),flush=True)
    elif req["method"] == "session/prompt":
        open({str(marker)!r}, "w").close()
        time.sleep(0.4)
        print(json.dumps({{"jsonrpc":"2.0","id":req["id"],"result":{{"stopReason":"end_turn"}}}}),flush=True)
'''
    with HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=2).open_session() as session:
        result = []
        worker = threading.Thread(target=lambda: result.append(session.prompt("first")))
        worker.start()
        deadline = time.monotonic() + 1
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        with pytest.raises(ACPProtocolError, match="concurrent"):
            session.prompt("second")
        worker.join(timeout=2)
        assert not worker.is_alive() and result == [{"stopReason": "end_turn"}]


def test_prompt_write_timeout_closes_unresponsive_session(tmp_path: Path):
    script = r'''
import json,sys,time
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        result={"protocolVersion":1,"agentInfo":{"name":"fixture"}}
    else:
        result={"sessionId":"SESSION-1"}
    print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":result}),flush=True)
    if req["method"] == "session/new": time.sleep(30)
'''
    session = HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=0.5).open_session()
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        session.prompt("x" * (2 * 1024 * 1024))
    assert time.monotonic() - started < 3
    assert session._process.poll() is not None
    with pytest.raises(ACPSessionClosed):
        session.prompt("again")


def test_notifications_do_not_extend_request_deadline(tmp_path: Path):
    script = r'''
import json,sys,time
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"protocolVersion":1,"agentInfo":{"name":"fixture"}}}),flush=True)
    elif req["method"] == "session/new":
        print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":{"sessionId":"SESSION-1"}}),flush=True)
    else:
        for _ in range(30):
            print(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{}}),flush=True)
            time.sleep(0.05)
'''
    session = HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=0.4).open_session()
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        session.prompt("hello")
    assert time.monotonic() - started < 2
    assert session._process.poll() is not None


@pytest.mark.parametrize("failure_point", ["selector", "session"])
def test_open_session_reaps_child_when_resource_setup_fails(tmp_path: Path, monkeypatch, failure_point):
    processes = []
    original_popen = acp_module.subprocess.Popen

    def start_process(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process

    def fail(*args, **kwargs):
        raise OSError("resource allocation failed")

    monkeypatch.setattr(acp_module.subprocess, "Popen", start_process)
    if failure_point == "selector":
        monkeypatch.setattr(acp_module.selectors, "DefaultSelector", fail)
    else:
        monkeypatch.setattr(acp_module, "HermesACPSession", fail)
    with pytest.raises(OSError, match="resource allocation"):
        HermesACPAdapter([sys.executable, "-c", "import time; time.sleep(30)"], tmp_path).open_session()
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdin.closed and processes[0].stdout.closed


def test_invalid_prompt_result_closes_session(tmp_path: Path):
    script = r'''
import json,sys
for line in sys.stdin:
    req=json.loads(line)
    if req["method"] == "initialize":
        result={"protocolVersion":1,"agentInfo":{"name":"fixture"}}
    elif req["method"] == "session/new":
        result={"sessionId":"SESSION-1"}
    else:
        result=[]
    print(json.dumps({"jsonrpc":"2.0","id":req["id"],"result":result}),flush=True)
'''
    session = HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=2).open_session()
    with pytest.raises(ACPProtocolError, match="not an object"):
        session.prompt("hello")
    assert session._process.poll() is not None
    with pytest.raises(ACPSessionClosed):
        session.prompt("again")
