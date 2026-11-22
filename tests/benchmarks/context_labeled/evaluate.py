"""Evaluate ContextBundle selection against labeled source paths.

The benchmark format deliberately separates expected paths from the actual
bundle. A future independent reviewer can replace the synthetic ``cases.json``
without changing the scoring or CLI. Synthetic output is not product-quality
evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _metrics(expected: set[str], actual: set[str]) -> dict[str, Any]:
    true_positive = len(expected & actual)
    false_positive = len(actual - expected)
    false_negative = len(expected - actual)
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = true_positive / precision_denominator if precision_denominator else None
    recall = true_positive / recall_denominator if recall_denominator else None
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else None
    return {"true_positive": true_positive, "false_positive": false_positive, "false_negative": false_negative, "precision": precision, "recall": recall, "f1": f1}


def score_bundle(expected_paths: Iterable[str], actual_items: Iterable[Mapping[str, Any]], required_paths: Iterable[str] = (), omissions: Iterable[str] = (), truncated_paths: Iterable[str] = (), budget: int | None = None, incomplete: bool = False) -> dict[str, Any]:
    """Score selected source paths and required C0 retention."""

    items = list(actual_items)
    expected = set(expected_paths)
    actual = {str(item["path"]) for item in items if item.get("path")}
    required = set(required_paths)
    selected_required = {
        str(item["path"])
        for item in items
        if item.get("path") in required and item.get("level") == "C0"
    }
    content_bytes = sum(len(str(item.get("content", "")).encode("utf-8")) for item in items)
    return {
        "selected_count": len(actual),
        "budget": budget,
        "content_bytes": content_bytes,
        "levels": {level: sum(1 for item in items if item.get("level") == level) for level in ("C0", "C1", "C2", "C3")},
        "overall": _metrics(expected, actual),
        "required_c0_retention": (len(selected_required) / len(required)) if required else None,
        "required_missing": sorted(required - selected_required),
        "omissions": sorted(set(omissions)),
        "truncated_paths": sorted(set(truncated_paths)),
        "incomplete": bool(incomplete or omissions or truncated_paths),
    }


def evaluate_cases(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    results = []
    for case in cases:
        score = score_bundle(case["expected_paths"], case["actual_items"], case.get("required_paths", []), case.get("omissions", []), case.get("truncated_paths", []), case.get("budget"), case.get("incomplete", False))
        results.append({"name": case["name"], **score})
    return {
        "schema_version": 1,
        "benchmark_type": "synthetic_regression",
        "case_count": len(results),
        "cases": results,
        "limitations": [
            "当前 cases.json 是人工构造的合成回归集，不是独立真实相关性标注集。",
            "指标不能用于宣称上下文质量、Token 成本收益或方法效果。",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate ContextBundle source selection")
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.cases.read_text(encoding="utf-8"))
    encoded = json.dumps(evaluate_cases(payload["cases"]), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
