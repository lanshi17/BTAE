from epe.adapters.protocol import AgentRequest, validate_request


def test_agent_request_rejects_self_declared_identity():
    response = validate_request(AgentRequest("r1", "start_implementation", "TASK-1", None, ("CLASS-1",), None, ("src/**",), trusted_identity={"role": "human"}))
    assert response.decision == "blocked"
    assert any(d.code == "EPE-AGENT-IDENTITY" for d in response.diagnostics)
