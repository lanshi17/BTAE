import json
import sys
import time
from pathlib import Path

import pytest

from epe.adapters.hosts.acp import HermesACPAdapter


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
'''
    return [sys.executable, "-c", script]


def test_open_session_is_explicit_and_disables_mcp(tmp_path: Path):
    with HermesACPAdapter(session_fixture(), tmp_path, timeout=2).open_session() as session:
        assert session.session_id == "SESSION-1"


def test_open_session_rejects_missing_session_id(tmp_path: Path):
    script = "import json,sys; [print(json.dumps({'jsonrpc':'2.0','id':json.loads(x)['id'],'result':{'protocolVersion':1,'agentInfo':{'name':'fixture'}} if json.loads(x)['method']=='initialize' else {'result':{}}}),flush=True) for x in sys.stdin]"
    with pytest.raises(ValueError, match="sessionId"):
        HermesACPAdapter([sys.executable, "-c", script], tmp_path, timeout=2).open_session()
