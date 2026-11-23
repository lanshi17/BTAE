from epe.parsers.documents import parse_markdown, parse_yaml_bytes
from epe.parsers.python import parse_python


def test_duplicate_yaml_key_is_diagnostic():
    _, diagnostics = parse_yaml_bytes(b"id: A\nid: B\n", "x.yaml")
    assert diagnostics and diagnostics[0].code == "EPE-YAML-PARSE"


def test_strict_json_parser_rejects_duplicate_keys_nonfinite_and_yaml_syntax():
    from epe.parsers.documents import parse_json_bytes
    valid, diagnostics = parse_json_bytes(b'{"id":"CLASS-1","value":[1,true,null]}', "x.json")
    assert diagnostics == [] and valid == {"id": "CLASS-1", "value": [1, True, None]}
    for payload in (b'{"id":"first","id":"second"}', b'{"value":NaN}', b'{id: unquoted}'):
        value, diagnostics = parse_json_bytes(payload, "x.json")
        assert value is None and diagnostics[0].code == "EPE-JSON-PARSE"
        assert diagnostics[0].path == "x.json"


def test_ast_does_not_execute_module_and_extracts_symbols():
    result = parse_python(b"raise RuntimeError('must not run')\nclass A:\n    async def f(self, x: int = 1):\n        return x\n", "src/a.py")
    assert result.complete
    assert {s.qualified_name for s in result.symbols} == {"A", "A.f"}


def test_unclosed_frontmatter_is_error():
    result = parse_markdown(b"---\nid: MOD-001\n", "docs/x.md")
    assert result.diagnostics[0].code == "EPE-DOC-FRONTMATTER"


def test_parse_batch_is_deterministic_and_tracks_incomplete_inputs():
    from epe.parsers.coordinator import parse_batch
    sources = [("b.py", b"class B: pass\n"), ("a.md", b"---\nid: MOD-001\n---\n# A\n")]
    first = parse_batch(sources)
    second = parse_batch(list(reversed(sources)))
    assert first.complete and first.input_manifest == second.input_manifest
    assert [getattr(item, "path", item["path"]) if isinstance(item, dict) else item.path for item in first.results] == ["a.md", "b.py"]
    bad = parse_batch(sources + [("x.bin", b"bytes")])
    assert not bad.complete and bad.counts["unsupported"] == 1


def test_parse_batch_structured_documents_expose_common_source_field():
    from epe.parsers.coordinator import parse_batch
    result = parse_batch([("contract.yaml", b"version: 1\n")])
    item = result.results[0]
    assert item["path"] == item["source"] == "contract.yaml"
    assert item["digest"]


def test_parse_batch_uses_strict_json_syntax():
    from epe.parsers.coordinator import parse_batch
    valid = parse_batch([("manifest.json", b'{"id":"CLASS-1"}')])
    invalid = parse_batch([("manifest.json", b"{id: CLASS-1}")])
    assert valid.complete and valid.results[0]["value"] == {"id": "CLASS-1"}
    assert not invalid.complete
    assert invalid.diagnostics[0].code == "EPE-JSON-PARSE"


def test_strict_json_codec_is_reusable_for_authority_records():
    import pytest
    from epe.core.json_codec import strict_json_loads
    assert strict_json_loads('{"a":1,"nested":{"b":true}}') == {"a": 1, "nested": {"b": True}}
    with pytest.raises(ValueError):
        strict_json_loads('{"a":1,"a":2}')


def test_parse_batch_rejects_duplicates_and_path_escape():
    from epe.parsers.coordinator import parse_batch
    result = parse_batch([("a.py", b"x = 1"), ("a.py", b"x = 2"), ("../outside.py", b"x = 3")])
    assert not result.complete
    assert result.counts["failed"] == 2
    assert {diagnostic.code for diagnostic in result.diagnostics} >= {"EPE-PARSE-DUPLICATE", "EPE-PARSE-SOURCE"}


def test_parse_batch_does_not_publish_syntax_errors_as_complete():
    from epe.parsers.coordinator import parse_batch
    result = parse_batch([("valid.py", b"class A: pass"), ("bad.py", b"def broken(:")])
    assert not result.complete and result.counts["failed"] == 1
    assert any(d.code == "EPE-AST-SYNTAX" for d in result.diagnostics)


def test_unhashable_yaml_key_is_a_located_diagnostic():
    _, diagnostics = parse_yaml_bytes(b"? [a, b]\n: value\n", "docs/bad.yaml")
    assert diagnostics and diagnostics[0].code == "EPE-YAML-PARSE"
    assert diagnostics[0].path == "docs/bad.yaml" and diagnostics[0].line == 1


def test_recursive_parsers_reject_nested_symlink_paths(tmp_path):
    from epe.parsers.documents import discover_documents
    from epe.parsers.python import parse_python_tree
    real_docs = tmp_path / "real-docs"; real_docs.mkdir()
    (real_docs / "design.md").write_text("---\nid: MOD-1\n---\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "linked").symlink_to(real_docs, target_is_directory=True)
    documents = discover_documents(tmp_path, ["docs"])
    assert any(item.diagnostics and item.diagnostics[0].code == "EPE-PATH-SYMLINK" for item in documents)

    real_src = tmp_path / "real-src"; real_src.mkdir()
    (real_src / "module.py").write_text("class Module: pass\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "linked").symlink_to(real_src, target_is_directory=True)
    _, diagnostics = parse_python_tree(tmp_path, ["src"])
    assert any(item.code == "EPE-PATH-SYMLINK" for item in diagnostics)


def test_recursive_parser_read_failures_are_structured(monkeypatch, tmp_path):
    from pathlib import Path
    from epe.parsers.documents import discover_documents
    from epe.parsers.python import parse_python_tree

    docs = tmp_path / "docs"; docs.mkdir()
    (docs / "broken.md").write_text("# broken", encoding="utf-8")
    src = tmp_path / "src"; src.mkdir()
    (src / "broken.py").write_text("value = 1", encoding="utf-8")
    original = Path.read_bytes

    def fail_broken(path):
        if path.name == "broken.md":
            raise OSError("document unavailable")
        if path.name == "broken.py":
            raise OSError("source unavailable")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fail_broken)
    documents = discover_documents(tmp_path, ["docs"])
    assert any(item.diagnostics and item.diagnostics[0].code == "EPE-DOC-READ" for item in documents)
    _, diagnostics = parse_python_tree(tmp_path, ["src"])
    assert any(item.code == "EPE-AST-READ" for item in diagnostics)
