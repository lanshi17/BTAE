import json

from epe.core.registry import Registry
from epe.graph.builder import build_graph, build_graph_incremental, load_graph
from epe.parsers.python import parse_python


def cfg():
    return {"managed": {"design_roots": [], "code_roots": ["src"], "test_roots": [], "contract_roots": []}, "storage": {"derived": ".engineering"}}


def test_generation_pointer_publishes_complete_snapshot(tmp_path):
    (tmp_path / "src").mkdir(); source = tmp_path / "src/a.py"; source.write_text("class A: pass\n")
    result = build_graph(tmp_path, Registry(), [parse_python(source.read_bytes(), "src/a.py")], cfg())
    assert result.published
    pointer = json.loads((tmp_path / ".engineering/current.json").read_text())
    assert pointer["generation"] == result.snapshot["content_digest"]
    generation = tmp_path / ".engineering/generations" / pointer["generation"]
    assert (generation / "graph.json").exists() and (generation / "entities.json").exists()
    loaded, diagnostics = load_graph(tmp_path, cfg())
    assert not diagnostics and loaded["content_digest"] == pointer["generation"]


def test_tampered_pointer_is_rejected_and_legacy_view_is_not_authoritative(tmp_path):
    (tmp_path / "src").mkdir(); source = tmp_path / "src/a.py"; source.write_text("class A: pass\n")
    result = build_graph(tmp_path, Registry(), [parse_python(source.read_bytes(), "src/a.py")], cfg())
    pointer_path = tmp_path / ".engineering/current.json"
    pointer = json.loads(pointer_path.read_text()); pointer["generation"] = "bad"; pointer_path.write_text(json.dumps(pointer))
    assert load_graph(tmp_path, cfg())[1][0].code == "EPE-GRAPH-POINTER"
    pointer["generation"] = result.snapshot["content_digest"]; pointer_path.write_text(json.dumps(pointer))
    legacy = tmp_path / ".engineering/graph.json"; value = json.loads(legacy.read_text()); value["nodes"] = []; legacy.write_text(json.dumps(value))
    assert load_graph(tmp_path, cfg())[0]["content_digest"] == result.snapshot["content_digest"]


def test_interrupted_compatibility_write_leaves_old_generation_readable(tmp_path, monkeypatch):
    import epe.graph.builder as builder
    (tmp_path / "src").mkdir(); source = tmp_path / "src/a.py"; source.write_text("class A: pass\n")
    fact = parse_python(source.read_bytes(), "src/a.py")
    first = build_graph(tmp_path, Registry(), [fact], cfg())
    pointer = (tmp_path / ".engineering/current.json").read_bytes()
    write = builder.atomic_write_json
    def fail_pointer(path, value):
        if path.name == "current.json":
            raise OSError("injected interruption")
        return write(path, value)
    monkeypatch.setattr(builder, "atomic_write_json", fail_pointer)
    original_parser_config = builder._parser_config
    monkeypatch.setattr(builder, "_parser_config", lambda config: {**original_parser_config(config), "version": "test-next"})
    failed = build_graph(tmp_path, Registry(), [fact], cfg())
    assert not failed.published and failed.diagnostics[-1].code == "EPE-GRAPH-PUBLISH"
    assert (tmp_path / ".engineering/current.json").read_bytes() == pointer
    legacy = json.loads((tmp_path / ".engineering/graph.json").read_text())
    assert legacy["content_digest"] != first.snapshot["content_digest"]
    assert load_graph(tmp_path, cfg())[1][0].code == "EPE-GRAPH-STALE"
    monkeypatch.setattr(builder, "_parser_config", original_parser_config)
    assert load_graph(tmp_path, cfg())[0]["content_digest"] == first.snapshot["content_digest"]


def test_existing_corrupted_generation_cannot_be_published(tmp_path):
    (tmp_path / "src").mkdir(); source = tmp_path / "src/a.py"; source.write_text("class A: pass\n")
    fact = parse_python(source.read_bytes(), "src/a.py")
    first = build_graph(tmp_path, Registry(), [fact], cfg())
    path = tmp_path / ".engineering/generations" / first.snapshot["content_digest"] / "entities.json"
    path.write_text("{}")
    result = build_graph(tmp_path, Registry(), [fact], cfg())
    assert not result.published and result.diagnostics[-1].code == "EPE-GRAPH-PUBLISH"


def test_generation_graph_must_match_pointer_even_if_self_consistent(tmp_path):
    from epe.core.fingerprint import sha256_json
    (tmp_path / "src").mkdir(); source = tmp_path / "src/a.py"; source.write_text("class A: pass\n")
    result = build_graph(tmp_path, Registry(), [parse_python(source.read_bytes(), "src/a.py")], cfg())
    path = tmp_path / ".engineering/generations" / result.snapshot["content_digest"] / "graph.json"
    value = json.loads(path.read_text()); value["nodes"] = []
    value["content_digest"] = sha256_json({k: v for k, v in value.items() if k != "content_digest"})
    path.write_text(json.dumps(value))
    assert load_graph(tmp_path, cfg())[1][0].code == "EPE-GRAPH-INTEGRITY"


def test_pointer_rejects_path_traversal(tmp_path):
    derived = tmp_path / ".engineering"; derived.mkdir()
    (derived / "current.json").write_text(json.dumps({"schema_version": 1, "generation": "../outside", "content_digest": "../outside"}))
    assert load_graph(tmp_path, cfg())[1][0].code == "EPE-GRAPH-POINTER"


def test_incremental_parser_read_failure_is_structured(tmp_path, monkeypatch):
    from pathlib import Path

    (tmp_path / "src").mkdir()
    source = tmp_path / "src/a.py"
    source.write_text("value = 1\n")
    fact = parse_python(source.read_bytes(), "src/a.py")
    first = build_graph(tmp_path, Registry(), [fact], cfg())
    assert first.published
    source.write_text("value = 2\n")
    original = Path.read_bytes
    reads = {source: 0}

    def fail_on_reparse(path):
        if path == source:
            reads[source] += 1
            if reads[source] >= 2:
                raise OSError("source disappeared during incremental parse")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fail_on_reparse)
    result = build_graph_incremental(tmp_path, Registry(), first.snapshot, cfg())
    assert not result.published and result.snapshot is None
    assert result.diagnostics[0].code == "EPE-AST-READ"
