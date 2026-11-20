from epe.graph.builder import build_graph, dependency_cycles
from epe.parsers.python import parse_python
from epe.core.registry import Registry


def test_local_import_cycle_is_retained(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    a = src / "a.py"; b = src / "b.py"
    a.write_text("from b import B\nclass A: pass\n")
    b.write_text("from a import A\nclass B: pass\n")
    cfg = {"managed": {"design_roots": [], "code_roots": ["src"], "test_roots": [], "contract_roots": []}, "storage": {"derived": ".engineering"}}
    result = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/a.py"), parse_python(b.read_bytes(), "src/b.py")], cfg)
    assert result.published
    assert dependency_cycles(result.snapshot)


def test_relative_and_from_imports_resolve_without_prefix_guessing(tmp_path):
    src = tmp_path / "src" / "pkg"; src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    a = src / "a.py"; b = src / "b.py"
    a.write_text("from .b import B\n")
    b.write_text("class B: pass\n")
    cfg = {"managed": {"design_roots": [], "code_roots": ["src"], "test_roots": [], "contract_roots": []}, "storage": {"derived": ".engineering"}}
    result = build_graph(tmp_path, Registry(), [parse_python(a.read_bytes(), "src/pkg/a.py"), parse_python(b.read_bytes(), "src/pkg/b.py"), parse_python((src / "__init__.py").read_bytes(), "src/pkg/__init__.py")], cfg)
    assert result.published
    assert any(e["from"] == "SRC-src/pkg/a.py" and e["to"] == "SRC-src/pkg/b.py" for e in result.snapshot["edges"])
