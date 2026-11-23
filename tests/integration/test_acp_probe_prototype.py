"""Exercises the exploration probe with real, controlled subprocesses."""
import importlib.util
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("acp_probe", Path(__file__).parents[2] / "experiments/hermes_acp_probe.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def command(body):
    return [sys.executable, "-c", "import sys,json,time; sys.stdin.readline(); " + body]


def test_initialize_ignores_notification_and_preserves_untrusted_boundary(tmp_path):
    body = "print(json.dumps({'jsonrpc':'2.0','method':'progress'}), flush=True); print(json.dumps({'jsonrpc':'2.0','id':1,'result':{'protocolVersion':1,'agentInfo':{'name':'fixture','version':'1'}}}), flush=True); time.sleep(10)"
    result = module.probe(command(body), tmp_path, timeout=2)
    assert result == {"protocol_version": 1, "agent_name": "fixture", "agent_version": "1", "trusted_identity": False, "write_isolation": False, "scope": "initialize_only"}


@pytest.mark.parametrize("body", [
    "print('not-json',flush=True)",
    "print(json.dumps({'jsonrpc':'2.0','id':2,'result':{}}),flush=True)",
    "print(json.dumps({'jsonrpc':'2.0','id':1,'result':{'protocolVersion':2,'agentInfo':{'name':'fixture'}}}),flush=True)",
    "print(json.dumps({'jsonrpc':'2.0','id':1,'result':{'protocolVersion':True,'agentInfo':{'name':'fixture'}}}),flush=True)",
])
def test_invalid_response_fails_closed(tmp_path, body):
    with pytest.raises(ValueError):
        module.probe(command(body), tmp_path, timeout=2)


def test_timeout_and_output_limit(tmp_path):
    with pytest.raises(TimeoutError):
        module.probe(command("time.sleep(10)"), tmp_path, timeout=0.2)
    with pytest.raises(ValueError, match="limit"):
        module.probe(command("print('x'*1000,flush=True)"), tmp_path, timeout=2, limit=64)
