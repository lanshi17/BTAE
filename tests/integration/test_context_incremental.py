import json
from types import SimpleNamespace

from epe.context.resolver import load_cached_context, resolve_context, store_cached_context
from epe.core.registry import Registry
from epe.graph.builder import plan_incremental, build_graph, build_graph_incremental
from epe.parsers.python import parse_python


def config():
    return {"managed": {"design_roots": ["docs"], "code_roots": ["src"], "test_roots": [], "contract_roots": []}, "exclude": [], "storage": {"derived": ".engineering"}}


def test_context_cache_invalidates_on_design_and_evidence(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "engineering/policies").mkdir(parents=True); (tmp_path / "engineering/policies/p.yaml").write_text("policy")
    (tmp_path / "engineering/evidence").mkdir(parents=True)
    cfg = config(); (tmp_path / "engineering/epe.yaml").write_text("schema_version: 1\n")
    task = SimpleNamespace(id="TASK-1", target_entities=[], objective="")
    bundle = resolve_context(tmp_path, cfg, task, Registry(), None, 4)
    store_cached_context(tmp_path, cfg, task, None, 4, bundle)
    assert load_cached_context(tmp_path, cfg, task, None, 4) is not None
    (tmp_path / "docs/index.md").write_text("changed")
    assert load_cached_context(tmp_path, cfg, task, None, 4) is None
    bundle = resolve_context(tmp_path, cfg, task, Registry(), None, 4)
    store_cached_context(tmp_path, cfg, task, None, 4, bundle)
    (tmp_path / "engineering/evidence/run.json").write_text("evidence")
    assert load_cached_context(tmp_path, cfg, task, None, 4) is None


def test_incremental_plan_handles_changes_deletions_and_fallback(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src/a.py"; old_file = tmp_path / "src/old.py"
    a.write_text("value = 1\n"); old_file.write_text("old = 1\n")
    cfg = config()
    old = build_graph(tmp_path, Registry(), [parse_python(p.read_bytes(), f"src/{p.name}") for p in (a, old_file)], cfg).snapshot
    a.write_text("value = 2\n"); old_file.unlink()
    new_file = tmp_path / "src/new.py"; new_file.write_text("new = 1\n")
    current = build_graph(tmp_path, Registry(), [parse_python(p.read_bytes(), f"src/{p.name}") for p in (a, new_file)], cfg).snapshot
    plan = plan_incremental(old, current)
    assert plan["full_rebuild"] is False
    assert plan["paths"] == ["src/a.py", "src/new.py", "src/old.py"]
    assert plan_incremental(old, current, "2", "1")["full_rebuild"] is True
    assert plan_incremental(None, current)["full_rebuild"] is True


def test_incremental_plan_rejects_damaged_and_incompatible_snapshots(tmp_path):
    import copy
    from epe.core.fingerprint import sha256_json
    (tmp_path / "src").mkdir(); a = tmp_path / "src/a.py"; a.write_text("class A: pass\n")
    current = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/a.py")], config()).snapshot
    damaged = copy.deepcopy(current); damaged["nodes"] = []
    assert plan_incremental(damaged, current)["full_rebuild"]
    missing = copy.deepcopy(current); missing["code_facts"] = []
    missing["content_digest"] = sha256_json({k: v for k, v in missing.items() if k != "content_digest"})
    assert plan_incremental(missing, current)["full_rebuild"]
    incompatible = copy.deepcopy(current); incompatible["parser_config"]["code_roots"] = ["other"]
    incompatible["content_digest"] = sha256_json({k: v for k, v in incompatible.items() if k != "content_digest"})
    assert plan_incremental(incompatible, current)["full_rebuild"]
    assert plan_incremental({"complete": True}, current)["full_rebuild"]


def test_incremental_graph_reuses_unchanged_facts_and_matches_full_build(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src/a.py"; b = tmp_path / "src/b.py"
    a.write_text("from b import B\n")
    b.write_text("class B: pass\n")
    cfg = config()
    first = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/a.py"), parse_python(b.read_bytes(), "src/b.py")], cfg)
    a.write_text("from b import B\nvalue = 1\n")
    incremental = build_graph_incremental(tmp_path, Registry(), first.snapshot, cfg)
    full = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/a.py"), parse_python(b.read_bytes(), "src/b.py")], cfg)
    assert incremental.published and full.published
    assert incremental.snapshot["content_digest"] == full.snapshot["content_digest"]


def test_incremental_preserves_dynamic_gaps_and_matches_full(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src/a.py"; b = tmp_path / "src/b.py"
    a.write_text("__import__('something')\n")
    b.write_text("value = 1\n")
    cfg = config()
    first = build_graph(tmp_path, Registry(), [parse_python(p.read_bytes(), f"src/{p.name}") for p in (a, b)], cfg)
    b.write_text("value = 2\n")
    incremental = build_graph_incremental(tmp_path, Registry(), first.snapshot, cfg)
    full = build_graph(tmp_path, Registry(), [parse_python(p.read_bytes(), f"src/{p.name}") for p in (a, b)], cfg)
    assert incremental.snapshot["content_digest"] == full.snapshot["content_digest"]
    assert any(d.code == "EPE-AST-DYNAMIC" for d in incremental.diagnostics)


def test_incremental_rebuilds_invalid_and_incomplete_cache(tmp_path):
    import copy
    from epe.core.fingerprint import sha256_json
    (tmp_path / "src").mkdir()
    a = tmp_path / "src/a.py"; a.write_text("class A: pass\n")
    cfg = config()
    original = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/a.py")], cfg).snapshot
    for recompute in (False, True):
        bad = copy.deepcopy(original); bad["code_facts"] = []
        if recompute:
            bad["content_digest"] = sha256_json({k: v for k, v in bad.items() if k != "content_digest"})
        result = build_graph_incremental(tmp_path, Registry(), bad, cfg)
        assert result.published
        assert result.snapshot["content_digest"] == original["content_digest"]
        assert any(node["id"] == "SYM-src/a.py:A" for node in result.snapshot["nodes"])


def test_build_rejects_outdated_or_incomplete_facts(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src/a.py"; a.write_text("value = 1\n")
    fact = parse_python(a.read_bytes(), "src/a.py")
    a.write_text("value = 2\n")
    assert not build_graph(tmp_path, Registry(), [fact], config()).published
    fact = parse_python(a.read_bytes(), "src/a.py"); fact.complete = False
    assert not build_graph(tmp_path, Registry(), [fact], config()).published


def test_incremental_add_remove_matches_full(tmp_path):
    (tmp_path / "src").mkdir()
    a = tmp_path / "src/a.py"; a.write_text("class A: pass\n")
    cfg = config()
    old = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/a.py")], cfg).snapshot
    a.unlink(); b = tmp_path / "src/b.py"; b.write_text("class B: pass\n")
    inc = build_graph_incremental(tmp_path, Registry(), old, cfg)
    full = build_graph(tmp_path, Registry(), [parse_python(b.read_bytes(), "src/b.py")], cfg)
    assert inc.published and inc.snapshot["content_digest"] == full.snapshot["content_digest"]


def test_context_cache_tracks_rules_contracts_tests_archive_and_mapped_sources(tmp_path):
    from epe.core.models import Entity, SourceLocation
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    (tmp_path / "docs/design.md").write_text("design")
    (tmp_path / "tests").mkdir(); (tmp_path / "tests/test_a.py").write_text("test")
    (tmp_path / "contracts").mkdir(); (tmp_path / "contracts/api.json").write_text("contract")
    (tmp_path / "archive").mkdir(); (tmp_path / "archive/old.md").write_text("old")
    (tmp_path / "special.py").write_text("implementation")
    cfg = config(); cfg["managed"]["test_roots"] = ["tests"]; cfg["managed"]["contract_roots"] = ["contracts"]
    entity = Entity(1, "CLASS-1", "Class", "A", SourceLocation("docs/design.md"), implementation=[{"path": "special.py"}])
    registry = Registry(entities={entity.id: entity})
    task = SimpleNamespace(id="TASK-1", target_entities=[entity.id], objective="")
    for path in ("AGENTS.md", "tests/test_a.py", "contracts/api.json", "archive/old.md", "special.py"):
        bundle = resolve_context(tmp_path, cfg, task, registry, None, 20)
        assert not bundle["incomplete"]
        store_cached_context(tmp_path, cfg, task, None, 20, bundle)
        assert load_cached_context(tmp_path, cfg, task, None, 20) is not None
        with (tmp_path / path).open("a") as handle: handle.write(" changed")
        assert load_cached_context(tmp_path, cfg, task, None, 20) is None


def test_context_marks_truncation_and_never_reads_outside_root(tmp_path):
    from epe.core.models import Entity, SourceLocation
    (tmp_path / "AGENTS.md").write_text("x" * 4001)
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.write_text("secret")
    (tmp_path / "outside-link").symlink_to(outside)
    entity = Entity(1, "CLASS-1", "Class", "A", SourceLocation("outside-link"))
    task = SimpleNamespace(id="TASK-1", target_entities=[entity.id], objective="")
    bundle = resolve_context(tmp_path, config(), task, Registry(entities={entity.id: entity}), None, 10)
    assert bundle["incomplete"] and bundle["truncated_paths"] == ["AGENTS.md"]
    assert "outside-link" in bundle["omissions"]
    assert all("secret" not in item["content"] for item in bundle["items"])
    store_cached_context(tmp_path, config(), task, None, 10, bundle)
    assert load_cached_context(tmp_path, config(), task, None, 10) is None


def test_context_cache_tracks_custom_evidence_under_reports(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules")
    (tmp_path / "docs").mkdir(); (tmp_path / "docs/index.md").write_text("index")
    evidence = tmp_path / "reports/runs/RUN-1/evidence.json"; evidence.parent.mkdir(parents=True)
    evidence.write_text('{"task_id":"TASK-1","result":"passed"}')
    cfg = config(); cfg["storage"]["evidence"] = "reports/runs"
    task = SimpleNamespace(id="TASK-1", target_entities=[], objective="")
    bundle = resolve_context(tmp_path, cfg, task, Registry(), None, 10)
    store_cached_context(tmp_path, cfg, task, None, 10, bundle)
    assert load_cached_context(tmp_path, cfg, task, None, 10) is not None
    evidence.write_text('{"task_id":"TASK-1","result":"failed"}')
    assert load_cached_context(tmp_path, cfg, task, None, 10) is None
