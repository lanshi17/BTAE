from epe.verification.architecture import validate_architecture


def test_forbidden_dependency_rule_matches_globs_only():
    snapshot = {"diagnostics": [], "edges": [{"from": "SRC-src/domain/a.py", "to": "SRC-src/infra/b.py", "relation": "depends_on"}]}
    data, diagnostics = validate_architecture(snapshot, {"forbidden_dependencies": [{"id": "R1", "from": "SRC-src/domain/*", "to": "SRC-src/infra/*"}]})
    assert data["status"] == "fail"
    assert any(d.code == "EPE-ARCH-FORBIDDEN" for d in diagnostics)


def test_similar_but_unmatched_dependency_is_not_forbidden():
    snapshot = {"diagnostics": [], "edges": [{"from": "SRC-src/domain/a.py", "to": "SRC-src/infrastructure/b.py", "relation": "depends_on"}]}
    data, diagnostics = validate_architecture(snapshot, {"forbidden_dependencies": [{"from": "SRC-src/domain/*", "to": "SRC-src/infra/*"}]})
    assert data["status"] == "pass"
    assert not diagnostics
