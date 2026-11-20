from epe.core.registry import build_registry


def entities():
    return [({"id": "CLASS-1", "type": "Class", "name": "A"}, "a.md", 1), ({"id": "SRC-1", "type": "Source", "name": "a", "source": {"path": "a.py"}}, "a.py", 1)]


def test_verified_relation_requires_auditable_fields():
    result = build_registry(entities(), [({"from": "CLASS-1", "to": "SRC-1", "relation": "realizes", "verified": True, "origin": {"type": "explicit", "source": "a.md"}, "confidence": 1}, "r.yaml")])
    assert any(d.code == "EPE-RELATION-VERIFICATION" for d in result.diagnostics)
    result = build_registry(entities(), [({"from": "CLASS-1", "to": "SRC-1", "relation": "realizes", "verified": True, "origin": {"type": "explicit", "source": "a.md"}, "confidence": 1, "verification": {"verifier": "ci", "method": "ast", "timestamp": "now", "version": "1"}}, "r.yaml")])
    assert not any(d.code == "EPE-RELATION-VERIFICATION" for d in result.diagnostics)


def test_relation_schema_rejects_missing_origin_source_and_unknown_fields():
    from epe.core.registry import build_registry
    from epe.core.models import Entity, SourceLocation
    entities = [("CLASS-1", "Class"), ("SRC-1", "Source")]
    candidates = [({"id": eid, "type": typ, "name": eid, "source": {"path": f"{eid}.md"}}, f"{eid}.md", 1) for eid, typ in entities]
    base = {"from": "CLASS-1", "to": "SRC-1", "relation": "realizes", "origin": {"type": "explicit"}, "confidence": 1, "verified": False}
    result = build_registry(candidates, [(base, "r.yaml")])
    assert not result.complete and any(d.code == "EPE-RELATION-ORIGIN" for d in result.diagnostics)
    base["origin"]["source"] = "r.yaml"; base["extra"] = True
    result = build_registry(candidates, [(base, "r.yaml")])
    assert not result.complete and any(d.code == "EPE-RELATION-FIELDS" for d in result.diagnostics)


def test_relation_schema_rejects_mismatched_verification_state():
    from epe.core.registry import build_registry
    candidates = [({"id": "CLASS-1", "type": "Class", "name": "Class", "source": {"path": "class.md"}}, "class.md", 1), ({"id": "SRC-1", "type": "Source", "name": "Source", "source": {"path": "src.py"}}, "src.py", 1)]
    verification = {"verifier": "ci", "method": "test", "timestamp": "2026-01-01T00:00:00Z", "version": "1"}
    raw = {"from": "CLASS-1", "to": "SRC-1", "relation": "realizes", "origin": {"type": "explicit", "source": "r.yaml"}, "confidence": 1, "verified": False, "verification": verification}
    result = build_registry(candidates, [(raw, "r.yaml")])
    assert not result.complete and any(d.code == "EPE-RELATION-VERIFICATION" for d in result.diagnostics)
