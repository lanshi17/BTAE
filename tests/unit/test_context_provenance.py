from types import SimpleNamespace

from epe.context.resolver import resolve_context
from epe.core.models import Entity, SourceLocation
from epe.core.registry import Registry


def test_inferred_neighbors_keep_origin_and_multiple_selection_reasons(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "docs/a.md").write_text("A")
    (tmp_path / "docs/shared.md").write_text("B and C")
    entities = {
        "CLASS-A": Entity(1, "CLASS-A", "Class", "Alpha", SourceLocation("docs/a.md")),
        "CLASS-B": Entity(1, "CLASS-B", "Class", "Beta", SourceLocation("docs/shared.md"), design_status="approved"),
        "CLASS-C": Entity(1, "CLASS-C", "Class", "Gamma", SourceLocation("docs/shared.md")),
    }
    edges = [{"from": "CLASS-A", "to": target, "relation": "depends_on", "origin": {"type": "inferred", "source": "model"}, "confidence": 1.0, "verified": False} for target in ("CLASS-B", "CLASS-C")]
    task = SimpleNamespace(id="TASK-1", target_entities=["CLASS-A"], objective="")
    result = resolve_context(tmp_path, {"managed": {"design_roots": ["docs"]}}, task, Registry(entities=entities), {"content_digest": "test", "edges": edges})
    item = next(item for item in result["items"] if item["path"] == "docs/shared.md")
    assert {s["entity_id"] for s in item["selections"]} == {"CLASS-B", "CLASS-C"}
    assert all(s["relation_origin"]["type"] == "inferred" and s["relation_verified"] is False for s in item["selections"])
    assert all(s["relation_confidence"] == 1.0 and s["approval_applicability"] == "unknown" for s in item["selections"])
    assert item["selections"][0]["declared_design_status"] == "approved"


def test_archived_entity_only_explicit_and_evidence_freshness_unknown(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "docs/archived.md").write_text("old design")
    evidence = tmp_path / "engineering/evidence/RUN-1/evidence.json"; evidence.parent.mkdir(parents=True)
    evidence.write_text('{"task_id":"TASK-1","validity":"valid"}')
    entity = Entity(1, "CLASS-A", "Class", "Archived", SourceLocation("docs/archived.md"), lifecycle="archived")
    registry = Registry(entities={entity.id: entity})
    cfg = {"managed": {"design_roots": ["docs"]}}
    task = SimpleNamespace(id="TASK-1", target_entities=[], objective="Archived")
    result = resolve_context(tmp_path, cfg, task, registry, None)
    assert not any(item["path"] == "docs/archived.md" for item in result["items"])
    ev = next(item for item in result["items"] if item["source_type"] == "evidence")
    assert ev["freshness"] == "unknown" and ev["selections"][0]["validity"] == "unknown"
    task.target_entities = [entity.id]
    result = resolve_context(tmp_path, cfg, task, registry, None)
    item = next(item for item in result["items"] if item["path"] == "docs/archived.md")
    assert item["freshness"] == "historical" and item["selections"][0]["lifecycle"] == "archived"


def test_external_provenance_assessments_are_explicit_and_cache_sensitive(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "docs/a.md").write_text("design")
    entity = Entity(1, "CLASS-A", "Class", "A", SourceLocation("docs/a.md"))
    task = SimpleNamespace(id="TASK-1", target_entities=["CLASS-A"], objective="")
    assessments = {"entities": {"CLASS-A": {"approval_applicability": "valid"}}, "evidence": {}}
    result = resolve_context(tmp_path, {"managed": {"design_roots": ["docs"]}}, task, Registry(entities={entity.id: entity}), None, 10, None, None, assessments)
    design = next(item for item in result["items"] if item["path"] == "docs/a.md")
    assert design["selections"][0]["approval_applicability"] == "valid"
    assert result["source_assessments"] == assessments


def test_evidence_assessment_controls_freshness_without_claiming_approval(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    evidence_path = tmp_path / "engineering/evidence/RUN-1/evidence.json"; evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text('{"task_id":"TASK-1","validity":"valid"}')
    task = SimpleNamespace(id="TASK-1", target_entities=[], objective="")
    cfg = {"managed": {"design_roots": ["docs"]}}
    path = "engineering/evidence/RUN-1/evidence.json"
    result = resolve_context(tmp_path, cfg, task, Registry(), None, 10, None, None, {"evidence": {path: {"validity": "valid"}}})
    item = next(item for item in result["items"] if item["path"] == path)
    assert item["freshness"] == "current" and item["selections"][0]["validity"] == "valid"
    assert all(selection.get("approval_applicability") is None for selection in item["selections"])
