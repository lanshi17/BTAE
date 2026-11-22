"""Evaluate labeled impact-analysis cases.

This evaluator is intentionally usable with synthetic regression cases and with a
future independently labeled dataset that keeps the same JSON shape. Its output
must not be interpreted as evidence of real-world recall until such a dataset is
available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from epe.graph.builder import analyze_impact

CLASSIFICATIONS = ("determined", "candidate")


def _metrics(expected: set[str], actual: set[str]) -> dict[str, Any]:
    true_positive = len(expected & actual)
    false_positive = len(actual - expected)
    false_negative = len(expected - actual)
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (true_positive / precision_denominator) if precision_denominator else None
    recall = (true_positive / recall_denominator) if recall_denominator else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else None
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def score_case(expected: Mapping[str, str], actual: Mapping[str, str]) -> dict[str, Any]:
    """Score one case as a binary impact set and by classification."""

    result: dict[str, Any] = {
        "overall": _metrics(set(expected), set(actual)),
        "by_classification": {},
        "exact_match": dict(expected) == dict(actual),
    }
    for classification in CLASSIFICATIONS:
        expected_set = {entity_id for entity_id, value in expected.items() if value == classification}
        actual_set = {entity_id for entity_id, value in actual.items() if value == classification}
        result["by_classification"][classification] = _metrics(expected_set, actual_set)
    return result


def _add_counts(target: dict[str, int], metrics: Mapping[str, Any]) -> None:
    for field in ("true_positive", "false_positive", "false_negative"):
        target[field] += int(metrics[field])


def _from_counts(counts: Mapping[str, int]) -> dict[str, Any]:
    return _metrics(
        set(range(counts["true_positive"] + counts["false_negative"])),
        set(range(counts["true_positive"] + counts["false_positive"])),
    ) | {field: counts[field] for field in ("true_positive", "false_positive", "false_negative")}


def evaluate_cases(cases: Iterable[Mapping[str, Any]], analyzer: Callable[..., Mapping[str, Any]] = analyze_impact) -> dict[str, Any]:
    """Run the analyzer and return reproducible aggregate metrics."""

    case_results: list[dict[str, Any]] = []
    aggregate_counts = {field: 0 for field in ("true_positive", "false_positive", "false_negative")}
    classification_counts = {name: dict(aggregate_counts) for name in CLASSIFICATIONS}
    complete = True
    exact_matches = 0
    for case in cases:
        graph = {"nodes": [{"id": node} for node in case["nodes"]], "edges": case["edges"]}
        report = analyzer(graph, case["changed"])
        actual = {item["entity_id"]: item["classification"] for item in report.get("impacts", [])}
        expected = dict(case["expected"])
        score = score_case(expected, actual)
        complete = complete and not bool(report.get("incomplete"))
        exact_matches += int(score["exact_match"])
        _add_counts(aggregate_counts, score["overall"])
        for classification in CLASSIFICATIONS:
            _add_counts(classification_counts[classification], score["by_classification"][classification])
        case_results.append({"name": case["name"], "incomplete": bool(report.get("incomplete")), **score})
    case_count = len(case_results)
    return {
        "schema_version": 1,
        "benchmark_type": "synthetic_regression",
        "case_count": case_count,
        "all_cases_complete": complete,
        "exact_match_rate": (exact_matches / case_count) if case_count else None,
        "aggregate": {
            "overall": _from_counts(aggregate_counts),
            "by_classification": {name: _from_counts(counts) for name, counts in classification_counts.items()},
        },
        "cases": case_results,
        "limitations": [
            "当前 cases.json 是人工构造的合成回归集，不是独立真实项目标注集。",
            "指标不能用于宣称 BTAE 的真实召回率、成本收益或优于对照方法。",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate labeled impact-analysis cases")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.cases.read_text(encoding="utf-8"))
    result = evaluate_cases(payload["cases"])
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
