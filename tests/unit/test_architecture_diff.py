from epe.verification.architecture import diff_architecture_snapshots


def node(identifier, kind="Source"):
    return {"id": identifier, "kind": kind, "source": {"path": identifier}}


def edge(source, target, relation="depends_on"):
    return {"from": source, "to": target, "relation": relation,
            "origin": {"type": "static", "source": source},
            "confidence": 1.0, "verified": False}


def test_architecture_diff_reports_stable_node_and_edge_delta_with_provenance():
    previous = {"content_digest": "old", "complete": True, "nodes": [node("A"), node("B")], "edges": [edge("A", "B")], "diagnostics": []}
    current = {"content_digest": "new", "complete": True, "nodes": [node("A"), node("C")], "edges": [edge("A", "C")], "diagnostics": []}
    result = diff_architecture_snapshots(previous, current)
    assert result["status"] == "changed" and not result["incomplete"]
    assert [item["id"] for item in result["added_nodes"]] == ["C"]
    assert [item["id"] for item in result["removed_nodes"]] == ["B"]
    assert result["added_edges"][0]["origin"]["type"] == "static"
    assert result["removed_edges"][0]["to"] == "B"


def test_architecture_diff_preserves_unknown_as_incomplete():
    snapshot = {"content_digest": "same", "complete": True, "nodes": [], "edges": [],
                "diagnostics": [{"code": "EPE-AST-DYNAMIC", "message": "dynamic"}]}
    result = diff_architecture_snapshots(snapshot, snapshot)
    assert result["status"] == "unchanged" and result["incomplete"]
    assert result["unknowns"]["current"]
