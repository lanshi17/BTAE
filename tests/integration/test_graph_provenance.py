import copy

from epe.core.fingerprint import sha256_json
from epe.core.registry import Registry, build_registry
from epe.graph.builder import build_graph, build_graph_incremental, graph_neighbors, load_graph
from epe.parsers.python import parse_python
from epe.verification.architecture import validate_architecture


def test_registry_preserves_distinct_relation_sources_and_rejects_exact_duplicates():
    candidates = [({"id": "MOD-A", "type": "Module", "name": "A"}, "a.md", 1),
                  ({"id": "CLASS-B", "type": "Class", "name": "B"}, "b.md", 1)]
    base = {"from": "MOD-A", "to": "CLASS-B", "relation": "contains"}
    relations = [(base | {"origin": {"type": "explicit", "source": "a.md"}}, "a.md"),
                 (base | {"origin": {"type": "inferred", "source": "b.md"}}, "b.md")]
    result = build_registry(candidates, relations)
    reverse = build_registry(candidates, list(reversed(relations)))
    assert result.complete and result.registry.to_dict() == reverse.registry.to_dict()
    assert len(result.registry.relations) == 2
    duplicate = build_registry(candidates, relations + [relations[0]])
    assert not duplicate.complete and any(d.code == "EPE-RELATION-DUPLICATE" for d in duplicate.diagnostics)


def test_distinct_import_locations_survive_build_incremental_and_queries(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    a, b = src / "a.py", src / "b.py"
    a.write_text("import b\nimport b\n")
    b.write_text("value = 1\n")
    config = {"managed": {"design_roots": [], "code_roots": ["src"], "test_roots": [], "contract_roots": []}, "storage": {"derived": ".engineering"}}
    facts = [parse_python(a.read_bytes(), "src/a.py"), parse_python(b.read_bytes(), "src/b.py")]
    full = build_graph(tmp_path, Registry(), facts, config)
    assert full.published
    edges = graph_neighbors(full.snapshot, "SRC-src/a.py", {"depends_on"}, "out")
    assert {e["origin"]["line"] for e in edges} == {1, 2}
    incremental = build_graph_incremental(tmp_path, Registry(), full.snapshot, config)
    assert incremental.published and incremental.snapshot == full.snapshot
    result, diagnostics = validate_architecture(full.snapshot, {"forbidden_dependencies": [{"id": "no-b", "from": "SRC-src/a.py", "to": "SRC-src/b.py"}]})
    assert len(result["violations"]) == 1 and len(diagnostics) == 1
    # A valid legacy snapshot cannot masquerade as a graph built by the current algorithm.
    old = copy.deepcopy(full.snapshot); old["parser_config"].pop("builder_version")
    old["content_digest"] = sha256_json({k: v for k, v in old.items() if k != "content_digest"})
    derived = tmp_path / ".engineering"
    (derived / "current.json").unlink()
    import json
    (derived / "graph.json").write_text(json.dumps(old))
    snapshot, diagnostics = load_graph(tmp_path, config)
    assert snapshot is None and diagnostics[0].code == "EPE-GRAPH-STALE"


def test_load_graph_rejects_malformed_edge_shape_before_query(tmp_path):
    import json

    src = tmp_path / "src"; src.mkdir()
    (src / "a.py").write_text("value = 1\n")
    config = {"managed": {"design_roots": [], "code_roots": ["src"], "test_roots": [], "contract_roots": []}, "storage": {"derived": ".engineering"}}
    full = build_graph(tmp_path, Registry(), [parse_python((src / "a.py").read_bytes(), "src/a.py")], config)
    assert full.published
    path = tmp_path / ".engineering/graph.json"
    snapshot = json.loads(path.read_text())
    snapshot["edges"] = [{"from": "A", "to": "B", "relation": "depends_on", "origin": "bad", "confidence": 1, "verified": False}]
    snapshot["content_digest"] = sha256_json({k: v for k, v in snapshot.items() if k != "content_digest"})
    path.write_text(json.dumps(snapshot))
    (tmp_path / ".engineering/current.json").unlink()
    loaded, diagnostics = load_graph(tmp_path, config)
    assert loaded is None and diagnostics[0].code == "EPE-GRAPH-SHAPE"
