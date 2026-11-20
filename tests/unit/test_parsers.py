from epe.parsers.documents import parse_markdown, parse_yaml_bytes
from epe.parsers.python import parse_python


def test_duplicate_yaml_key_is_diagnostic():
    _, diagnostics = parse_yaml_bytes(b"id: A\nid: B\n", "x.yaml")
    assert diagnostics and diagnostics[0].code == "EPE-YAML-PARSE"


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
