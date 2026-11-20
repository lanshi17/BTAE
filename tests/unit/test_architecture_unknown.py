from epe.verification.architecture import validate_architecture


def test_dynamic_analysis_gap_is_unknown_and_blocking():
    snapshot = {"diagnostics": [{"code": "EPE-AST-DYNAMIC", "message": "dynamic"}], "edges": []}
    data, diagnostics = validate_architecture(snapshot, {"forbidden_dependencies": [], "unknown_is_blocking": True})
    assert data["status"] == "fail"
    assert diagnostics and diagnostics[0].code == "EPE-ARCH-UNKNOWN"


def test_module_coverage_unknown_respects_policy_and_never_claims_pass():
    snapshot = {"nodes": [{"id": "MOD-A", "kind": "Module"}, {"id": "SRC-a", "kind": "Source"}],
                "edges": [], "diagnostics": [], "module_coverage": "unconfigured"}
    blocked, diagnostics = validate_architecture(snapshot, {})
    assert blocked["status"] == "fail" and diagnostics[0].is_error
    assert blocked["unknowns"][0]["code"] == "EPE-ARCH-MODULE-COVERAGE"
    allowed, diagnostics = validate_architecture(snapshot, {"unknown_is_blocking": False})
    assert allowed["status"] == "unknown" and not diagnostics[0].is_error
    clean, diagnostics = validate_architecture(dict(snapshot, module_coverage="configured"), {})
    assert clean["status"] == "pass" and not diagnostics
    no_modules, diagnostics = validate_architecture(dict(snapshot, nodes=[snapshot["nodes"][1]]), {})
    assert no_modules["status"] == "pass" and not diagnostics
    violated = dict(snapshot, edges=[{"from": "MOD-A", "to": "MOD-A", "relation": "depends_on"}])
    report, _ = validate_architecture(violated, {"unknown_is_blocking": False})
    assert report["status"] == "fail"


def test_allowed_dynamic_gap_remains_unknown():
    snapshot = {"nodes": [], "diagnostics": [{"code": "EPE-AST-DYNAMIC"}], "edges": []}
    report, diagnostics = validate_architecture(snapshot, {"unknown_is_blocking": False})
    assert report["status"] == "unknown" and not diagnostics[0].is_error
