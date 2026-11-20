from epe.adapters.hosts.base import LocalHostAdapter, capability_matrix
from epe.adapters.protocol import AgentRequest


def request(operation):
    return AgentRequest("REQ-1", operation, "TASK-1", "CHANGE-1", ("CLASS-1",), "a" * 64, ("src/**",), {}, {"source": "host", "id": "runner"})


def test_local_host_reports_write_boundary_and_rejects_writes():
    adapter = LocalHostAdapter()
    assert adapter.capabilities.write_isolation is False
    assert adapter.dispatch(request("start_implementation")).decision == "unsupported"
    assert adapter.dispatch(request("finalize")).decision == "unsupported"
    assert adapter.dispatch(request("verify")).decision == "accepted"


def test_capability_matrix_marks_unintegrated_hermes_unsupported():
    rows = {row.host_id: row for row in capability_matrix()}
    assert rows["hermes"].status == "unsupported-unintegrated"
    assert rows["hermes"].operations == ()


def test_agent_request_rejects_invalid_identity_scope_and_revision():
    from epe.adapters.protocol import validate_request
    base = request("verify")
    cases = [
        AgentRequest("REQ-1", "verify", "bad", "CHANGE-1", ("CLASS-1",), "a" * 64, ("src/**",), {}, {"source": "host"}),
        AgentRequest("REQ-1", "verify", "TASK-1", "CHANGE-1", ("CLASS-1",), "bad", ("src/**",), {}, {"source": "host"}),
        AgentRequest("REQ-1", "verify", "TASK-1", "CHANGE-1", ("CLASS-1",), "a" * 64, ("../outside",), {}, {"source": "host"}),
        AgentRequest("REQ-1", "verify", "TASK-1", "CHANGE-1", ("CLASS-1",), "a" * 64, ("src\\\\x",), {}, {"source": "host"}),
    ]
    for candidate in cases:
        result = validate_request(candidate)
        assert result.decision == "blocked"
    assert validate_request(base).decision == "accepted"
