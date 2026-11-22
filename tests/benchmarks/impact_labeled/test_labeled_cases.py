"""Human-labeled synthetic expectations; not a real-world recall benchmark."""
import json
from pathlib import Path

from epe.graph.builder import analyze_impact


def test_labeled_impact_scenarios():
    cases = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        graph = {"nodes": [{"id": node} for node in case["nodes"]], "edges": case["edges"]}
        report = analyze_impact(graph, case["changed"])
        actual = {item["entity_id"]: item["classification"] for item in report["impacts"]}
        assert actual == case["expected"], case["name"]
        assert not report["incomplete"], case["name"]
