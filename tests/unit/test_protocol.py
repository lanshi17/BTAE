from epe.adapters.protocol import AgentRequest, validate_request
from dataclasses import asdict
import json
from pathlib import Path
import jsonschema


def test_agent_request_rejects_self_declared_identity():
    response = validate_request(AgentRequest("r1", "start_implementation", "TASK-1", None, ("CLASS-1",), None, ("src/**",), trusted_identity={"role": "human"}))
    assert response.decision == "blocked"
    assert any(d.code == "EPE-AGENT-IDENTITY" for d in response.diagnostics)


def test_agent_request_and_unsupported_response_match_machine_contracts():
    request = AgentRequest("REQ-1", "verify", "TASK-1", None, ("CLASS-1",), None,
                           ("src/**",), trusted_identity={"source": "host"})
    request_schema = json.loads((Path("engineering/schemas/agent-request.schema.json")).read_text())
    response_schema = json.loads((Path("engineering/schemas/agent-response.schema.json")).read_text())
    jsonschema.Draft202012Validator(request_schema).validate(json.loads(json.dumps(asdict(request))))
    jsonschema.Draft202012Validator(response_schema).validate({
        "decision": "unsupported", "reasons": ["not integrated"], "diagnostics": [],
        "evidence_ids": [], "next_steps": ["configure host"]
    })


def test_agent_request_schema_requires_protocol_and_trusted_identity():
    schema = json.loads(Path("engineering/schemas/agent-request.schema.json").read_text())
    value = json.loads(json.dumps(asdict(AgentRequest("REQ-1", "verify", "TASK-1", None,
                                                      ("CLASS-1",), None, ("src/**",),
                                                      trusted_identity={"source": "host"}))))
    value.pop("protocol_version")
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(value)
    value["protocol_version"] = "1"
    value.pop("trusted_identity")
    with __import__("pytest").raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(value)
