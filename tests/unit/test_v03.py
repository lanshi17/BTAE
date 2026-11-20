from types import SimpleNamespace

from epe.context.resolver import resolve_context
from epe.core.registry import Registry
from epe.graph.builder import analyze_impact


def test_impact_budget_is_explicit():
    result = analyze_impact({"content_digest": "x", "nodes": [], "edges": []}, ["CLASS-1"], 0)
    assert result["truncated"] is True
    assert result["impacts"] == []


def test_context_reports_budget_omissions(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index", encoding="utf-8")
    task = SimpleNamespace(id="TASK-1", target_entities=[])
    config = {"managed": {"design_roots": ["docs"], "code_roots": []}, "exclude": []}
    result = resolve_context(tmp_path, config, task, Registry(), None, budget=1)
    assert result["items"]
    assert result["omissions"]
    assert result["incomplete"] is True


def test_context_marks_history_and_evidence_as_c3(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index", encoding="utf-8")
    (tmp_path / "docs/architecture/decisions").mkdir(parents=True)
    (tmp_path / "docs/architecture/decisions/ADR-1.md").write_text("history")
    evidence = tmp_path / "engineering/evidence/RUN-1"; evidence.mkdir(parents=True)
    (evidence / "evidence.json").write_text('{"task_id":"TASK-1","result":"failed"}')
    task = SimpleNamespace(id="TASK-1", target_entities=[], objective="")
    cfg = {"managed": {"design_roots": ["docs"], "code_roots": []}, "exclude": [], "storage": {"evidence": "engineering/evidence"}}
    result = resolve_context(tmp_path, cfg, task, Registry(), None, budget=10)
    assert any(item["level"] == "C3" and item["source_type"] == "historical" for item in result["items"])
    assert any(item["level"] == "C3" and item["source_type"] == "evidence" for item in result["items"])
