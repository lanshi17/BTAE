import pytest

from epe.graph.builder import trace_path


def edge(frm, to, relation="depends_on", origin="explicit", confidence=1):
    return {"from": frm, "to": to, "relation": relation,
            "origin": {"type": origin, "source": "fixture.md"}, "confidence": confidence}


def test_shortest_path_filters_direction_and_is_deterministic():
    edges = [edge("A", "C"), edge("A", "B"), edge("B", "D", "realizes"),
             edge("C", "D"), edge("D", "A")]
    snapshot = {"nodes": [{"id": x} for x in "ABCD"], "edges": edges, "content_digest": "example"}
    result = trace_path(snapshot, "A", "D")
    assert [step["edge"]["to"] for step in result["path"]] == ["B", "D"]
    assert result == trace_path(dict(snapshot, edges=list(reversed(edges))), "A", "D")
    filtered = trace_path(snapshot, "A", "D", relation_types={"depends_on"})
    assert [step["edge"]["to"] for step in filtered["path"]] == ["C", "D"]
    reverse = trace_path(snapshot, "D", "B", direction="in")
    assert reverse["found"] and reverse["path"][0]["direction"] == "in"
    assert trace_path(snapshot, "A", "A")["path"] == []


def test_search_budget_absence_and_uncertainty_are_distinct():
    snapshot = {"nodes": [{"id": x} for x in "ABCD"],
                "edges": [edge("A", "B", origin="inferred"), edge("B", "C")],
                "diagnostics": [{"code": "EPE-AST-DYNAMIC"}]}
    truncated = trace_path(snapshot, "A", "C", budget=1)
    assert not truncated["found"] and truncated["truncated"]
    found = trace_path(snapshot, "A", "C", budget=2)
    assert found["found"] and found["classification"] == "candidate"
    assert found["analysis_diagnostics"] == snapshot["diagnostics"]
    missing = trace_path(snapshot, "A", "D")
    assert not missing["found"] and not missing["truncated"]
    with pytest.raises(ValueError): trace_path(snapshot, "A", "absent")
    with pytest.raises(ValueError): trace_path(snapshot, "A", "C", budget=0)


@pytest.mark.parametrize("confidence", [None, True, float("nan"), 0.5])
def test_malformed_or_uncertain_edge_metadata_is_candidate(confidence):
    snapshot = {
        "nodes": [{"id": "A"}, {"id": "B"}],
        "edges": [{"from": "A", "to": "B", "relation": "depends_on",
                   "origin": "untrusted-shape", "confidence": confidence}],
    }
    result = trace_path(snapshot, "A", "B")
    assert result["found"] and result["classification"] == "candidate"
