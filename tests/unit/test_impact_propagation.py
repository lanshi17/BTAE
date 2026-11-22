from epe.graph.builder import analyze_impact


def edge(source, target, relation, origin="explicit"):
    return {"from": source, "to": target, "relation": relation, "origin": {"type": origin}, "confidence": 1.0}


def fixture():
    return {"content_digest": "snapshot", "nodes": [
        {"id": "CLASS-A", "kind": "Class"},
        {"id": "CLASS-B", "kind": "Class"},
        {"id": "SRC-src/a.py", "kind": "Source", "source": {"path": "src/a.py"}},
        {"id": "SYM-src/a.py:A", "kind": "Symbol", "source": {"path": "src/a.py"}},
        {"id": "TEST-A", "kind": "Test"},
        {"id": "EVIDENCE-A", "kind": "Evidence"},
    ], "edges": [
        edge("CLASS-A", "SYM-src/a.py:A", "realizes"),
        edge("CLASS-B", "CLASS-A", "depends_on"),
        edge("CLASS-B", "TEST-A", "verified_by"),
        edge("TEST-A", "EVIDENCE-A", "evidenced_by"),
    ]}


def impacts(result):
    return {item["entity_id"]: item for item in result["impacts"]}


def test_code_change_reaches_design_consumers_and_evidence():
    result = analyze_impact(fixture(), ["SRC-src/a.py"])
    found = impacts(result)
    assert set(found) == {"SYM-src/a.py:A", "CLASS-A", "CLASS-B", "TEST-A", "EVIDENCE-A"}
    assert [step["direction"] for step in found["CLASS-A"]["path"]] == ["forward", "reverse"]
    assert found["EVIDENCE-A"]["origin_entity"] == "SRC-src/a.py"
    assert not result["incomplete"]


def test_design_change_reaches_implementation_without_infinite_cycle():
    graph = fixture(); graph["edges"].append(edge("CLASS-A", "CLASS-B", "depends_on"))
    found = impacts(analyze_impact(graph, ["CLASS-A"]))
    assert {"SRC-src/a.py", "SYM-src/a.py:A", "CLASS-B"} <= set(found)
    assert "CLASS-A" not in found


def test_candidate_uncertainty_propagates_and_determined_path_upgrades():
    graph = {"nodes": [{"id": x} for x in ["A", "B", "C", "D"]], "edges": [
        edge("A", "B", "verified_by", "inferred"), edge("B", "D", "verified_by"),
        edge("A", "C", "verified_by"), edge("C", "B", "verified_by"),
    ]}
    found = impacts(analyze_impact(graph, ["A"]))
    assert found["B"]["classification"] == "determined"
    assert found["D"]["classification"] == "determined"
    graph["edges"] = graph["edges"][:2]
    found = impacts(analyze_impact(graph, ["A"]))
    assert found["D"]["classification"] == "candidate"


def test_budget_boundary_and_unknowns_are_explicit():
    graph = {"nodes": [{"id": "A"}, {"id": "B"}], "edges": [edge("A", "B", "verified_by")],
             "diagnostics": [{"code": "EPE-AST-DYNAMIC", "message": "unknown"}]}
    exact = analyze_impact(graph, ["A"], 1)
    assert not exact["truncated"] and exact["incomplete"]
    graph["edges"].append(edge("B", "C", "verified_by"))
    limited = analyze_impact(graph, ["A", "MISSING"], 1)
    assert limited["truncated"] and limited["missing_entities"] == ["MISSING"]


def test_low_and_missing_confidence_remain_candidate_until_certain_path_exists():
    low = edge("A", "B", "verified_by")
    low["confidence"] = 0.5
    graph = {"nodes": [{"id": x} for x in ("A", "B", "C", "D")], "edges": [
        low, edge("B", "D", "verified_by"), edge("A", "C", "verified_by"),
    ]}
    found = impacts(analyze_impact(graph, ["A"]))
    assert found["B"]["classification"] == found["D"]["classification"] == "candidate"
    graph["edges"].append(edge("C", "B", "verified_by"))
    found = impacts(analyze_impact(graph, ["A"]))
    assert found["B"]["classification"] == found["D"]["classification"] == "determined"
    graph["edges"] = [edge("A", "B", "verified_by")]
    del graph["edges"][0]["confidence"]
    assert impacts(analyze_impact(graph, ["A"]))["B"]["classification"] == "candidate"
