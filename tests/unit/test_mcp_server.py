import json
import os
import subprocess
import sys
from pathlib import Path

from epe.mcp_server import dispatch, design_plan, project_context


ROOT = Path(__file__).resolve().parents[2]


def test_design_plan_is_draft_and_workflow_specific():
    result = design_plan({
        "objective": "add an API boundary",
        "change_type": "feature",
        "risk": "high",
        "target_entities": ["MOD-009"],
    })
    assert result["status"] == "draft"
    assert result["approval_required"] is True
    assert "acceptance" in result["task"]["required_fields"]
    assert "Evidence and finalize gate" in result["traceability_chain"]


def test_project_context_reports_sources_and_does_not_write(tmp_path):
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    result = project_context({"root": str(ROOT), "objective": "change parser mapping", "change_type": "bugfix", "target_entities": ["MOD-002"]})
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert result["status"] == "ready"
    assert any(source["path"] == "AGENTS.md" for source in result["sources"])
    assert before == after


def test_stdio_mcp_entry_supports_initialize_tools_and_tool_call(tmp_path):
    env = dict(os.environ, BTAE_ROOT=str(ROOT), PYTHONPATH=str(ROOT / "src"))
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "btae_design_plan", "arguments": {"objective": "add a parser", "change_type": "feature"}}},
    ]
    process = subprocess.run(
        [sys.executable, str(ROOT / "mcp/btae_server.py")],
        input="\n".join(json.dumps(message) for message in messages) + "\n",
        text=True,
        capture_output=True,
        env=env,
        cwd=tmp_path,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    responses = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
    assert [response["id"] for response in responses] == [1, 2, 3]
    names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert {"btae_project_context", "btae_design_plan", "btae_validate_project"} <= names
    payload = json.loads(responses[2]["result"]["structuredContent"] if isinstance(responses[2]["result"].get("structuredContent"), str) else responses[2]["result"]["content"][0]["text"])
    assert payload["status"] == "draft"


def test_initialize_negotiates_a_supported_protocol_version():
    result = dispatch({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    assert result["result"]["protocolVersion"] == "2025-06-18"
