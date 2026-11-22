"""Human-labeled synthetic expectations; not a real-world recall benchmark."""
import json
from pathlib import Path

from epe.graph.builder import analyze_impact

from .evaluate import evaluate_cases, score_case


def test_labeled_impact_scenarios():
    cases = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        graph = {"nodes": [{"id": node} for node in case["nodes"]], "edges": case["edges"]}
        report = analyze_impact(graph, case["changed"])
        actual = {item["entity_id"]: item["classification"] for item in report["impacts"]}
        assert actual == case["expected"], case["name"]
        assert not report["incomplete"], case["name"]


def test_evaluator_reports_overall_and_classification_metrics():
    cases = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))["cases"]
    result = evaluate_cases(cases)
    assert result["benchmark_type"] == "synthetic_regression"
    assert result["case_count"] == 3
    assert result["exact_match_rate"] == 1.0
    assert result["aggregate"]["overall"]["f1"] == 1.0
    assert result["aggregate"]["by_classification"]["candidate"]["recall"] == 1.0
    assert all(case["exact_match"] and not case["incomplete"] for case in result["cases"])


def test_score_case_exposes_false_positive_and_negative_counts():
    result = score_case({"CLASS-A": "determined"}, {"CLASS-A": "candidate", "CLASS-B": "candidate"})
    assert result["overall"] == {
        "true_positive": 1,
        "false_positive": 1,
        "false_negative": 0,
        "precision": 0.5,
        "recall": 1.0,
        "f1": 2 / 3,
    }
    assert result["by_classification"]["determined"]["recall"] == 0.0
