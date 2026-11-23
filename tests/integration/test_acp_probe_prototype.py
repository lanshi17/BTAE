"""Exercises the exploration probe with real, controlled subprocesses."""
import importlib.util
import sys
import time
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


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 0, True])
def test_rejects_invalid_timeout_before_starting_process(tmp_path, timeout):
    with pytest.raises(ValueError, match="invalid"):
        module.probe(["does-not-exist"], tmp_path, timeout=timeout)


def test_cleans_descendant_after_leader_exits(tmp_path):
    marker = tmp_path / "survived"
    child = ("import time,pathlib,json; time.sleep(0.2); "
             "print(json.dumps({'jsonrpc':'2.0','id':1,'result':{'protocolVersion':1,'agentInfo':{'name':'fixture'}}}),flush=True); "
             "time.sleep(1); pathlib.Path(%r).write_text('alive')") % str(marker)
    body = "import subprocess; subprocess.Popen([sys.executable,'-c',%r])" % child
    module.probe(command(body), tmp_path, timeout=2)
    time.sleep(1.2)
    assert not marker.exists()
