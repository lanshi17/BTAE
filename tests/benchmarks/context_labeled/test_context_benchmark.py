import json
from pathlib import Path

from .evaluate import evaluate_cases, score_bundle


def test_synthetic_context_cases_report_retention_and_omissions():
    cases = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))["cases"]
    result = evaluate_cases(cases)
    assert result["benchmark_type"] == "synthetic_regression"
    assert result["case_count"] == 2
    assert result["cases"][0]["required_c0_retention"] == 1.0
    assert result["cases"][1]["required_c0_retention"] == 1.0
    assert result["cases"][1]["omissions"] == ["docs/spec.md"]


def test_context_score_exposes_false_positive_and_truncation():
    result = score_bundle(
        ["AGENTS.md", "docs/index.md"],
        [{"path": "AGENTS.md", "level": "C0", "content": "rules"}, {"path": "extra.md", "level": "C3", "content": "old"}],
        required_paths=["AGENTS.md", "docs/index.md"],
        truncated_paths=["extra.md"],
        budget=2,
    )
    assert result["overall"]["false_positive"] == 1
    assert result["overall"]["false_negative"] == 1
    assert result["required_c0_retention"] == 0.5
    assert result["incomplete"] is True


def test_required_source_selected_at_lower_level_is_not_c0_retained():
    result = score_bundle(
        ["AGENTS.md"],
        [{"path": "AGENTS.md", "level": "C3", "content": "rules"}],
        required_paths=["AGENTS.md"],
    )
    assert result["required_c0_retention"] == 0.0
    assert result["required_missing"] == ["AGENTS.md"]


def test_zero_hits_has_zero_f1_when_errors_exist():
    result = score_bundle(["expected.md"], [{"path": "other.md", "level": "C1", "content": ""}])
    assert result["overall"]["precision"] == 0.0
    assert result["overall"]["recall"] == 0.0
    assert result["overall"]["f1"] == 0.0
