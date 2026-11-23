import json

from epe.core.registry import build_registry
from epe.graph.builder import build_graph, build_graph_incremental, dependency_cycles, load_graph
from epe.parsers.python import parse_python
from epe.verification.architecture import validate_architecture


def fixture(tmp_path):
    for path, content in {"src/a/x.py": "import b.y\nimport a.w\n", "src/a/w.py": "value = 1\n", "src/b/z.py": "import a.w\n", "src/b/y.py": "value = 1\n"}.items():
        file = tmp_path / path; file.parent.mkdir(parents=True, exist_ok=True); file.write_text(content)
    registry = build_registry([({"id": "MOD-A", "type": "Module", "name": "A"}, "a.md", 1), ({"id": "MOD-B", "type": "Module", "name": "B"}, "b.md", 1)]).registry
    config = {"managed": {"design_roots": [], "code_roots": ["src"], "test_roots": [], "contract_roots": [], "module_roots": {"MOD-A": ["src/a"], "MOD-B": ["src/b"]}}, "storage": {"derived": ".engineering"}}
    facts = [parse_python(p.read_bytes(), p.relative_to(tmp_path).as_posix()) for p in sorted((tmp_path / "src").rglob("*.py"))]
    return registry, config, facts


def test_module_cycle_detected_without_source_cycle_and_preserves_origin(tmp_path):
    registry, config, facts = fixture(tmp_path)
    result = build_graph(tmp_path, registry, facts, config)
    assert result.published and result.snapshot["module_coverage"] == "configured"
    cycles = dependency_cycles(result.snapshot)
    assert ["MOD-A", "MOD-B", "MOD-A"] in cycles
    assert not any(c[0].startswith("SRC-") for c in cycles)
    edge = next(e for e in result.snapshot["edges"] if e["from"] == "MOD-A" and e["to"] == "MOD-B")
    assert edge["origin"]["source"] == "src/a/x.py" and edge["origin"]["line"] == 1
    assert edge["origin"]["to_source"] == "SRC-src/b/y.py"
    assert not any(e["from"] == e["to"] and e["from"].startswith("MOD-") for e in result.snapshot["edges"])
    report, _ = validate_architecture(result.snapshot, {})
    assert report["status"] == "fail" and report["module_coverage"] == "configured"
    incremental = build_graph_incremental(tmp_path, registry, result.snapshot, config)
    assert incremental.published and incremental.snapshot == result.snapshot
    changed = {**config, "managed": {**config["managed"], "module_roots": {"MOD-A": ["src"]}}}
    assert load_graph(tmp_path, changed)[1][0].code == "EPE-GRAPH-STALE"


def test_ambiguous_invalid_and_unassigned_module_ownership(tmp_path):
    registry, config, facts = fixture(tmp_path)
    config["managed"]["module_roots"]["MOD-B"].append("src/a")
    ambiguous = build_graph(tmp_path, registry, facts, config)
    assert not ambiguous.published and any(d.code == "EPE-MODULE-AMBIGUOUS" for d in ambiguous.diagnostics)
    config["managed"]["module_roots"] = {"MOD-UNKNOWN": ["src/a"]}
    invalid = build_graph(tmp_path, registry, facts, config)
    assert not invalid.published and any(d.code == "EPE-MODULE-CONFIG" for d in invalid.diagnostics)
    config["managed"]["module_roots"] = {"MOD-A": ["src/a"]}
    partial = build_graph(tmp_path, registry, facts, config)
    assert partial.published and partial.snapshot["module_coverage"] == "partial"
    report, diagnostics = validate_architecture(partial.snapshot, {})
    assert report["status"] == "fail" and any(d.code == "EPE-ARCH-UNKNOWN" for d in diagnostics)


def test_cli_reports_module_cycle_with_source_evidence(tmp_path):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import yaml

    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]
    def run(*args):
        result = subprocess.run(base + list(args), env=env, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)
    assert run("init")[0] == 0
    _, config, _ = fixture(tmp_path)
    project_config = tmp_path / "engineering/epe.yaml"
    data = yaml.safe_load(project_config.read_text())
    data["managed"]["module_roots"] = config["managed"]["module_roots"]
    project_config.write_text(yaml.safe_dump(data))
    docs = tmp_path / "docs"; docs.mkdir(exist_ok=True)
    for module in ("A", "B"):
        (docs / f"{module}.md").write_text(f"---\nid: MOD-{module}\ntype: Module\nname: {module}\n---\n")
    assert run("graph", "build")[0] == 0
    code, result = run("architecture", "validate")
    assert code != 0 and result["data"]["module_coverage"] == "configured"
    cycle = next(v for v in result["data"]["violations"] if v["rule"] == "ARCH-CYCLE" and v["path"][0] == "MOD-A")
    assert cycle["edge_evidence"][0][0]["origin"]["source"] == "src/a/x.py"


def test_cli_architecture_exception_requires_approved_adr_and_review_deadline(tmp_path, capsys):
    from epe.cli import main
    import yaml

    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "src/b.py").write_text("value = 1\n", encoding="utf-8")
    adr_dir = tmp_path / "docs/architecture/decisions"; adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-1.md").write_text("---\nid: ADR-1\ntype: ADR\nname: exception\ndesign_status: approved\n---\n", encoding="utf-8")
    policy = tmp_path / "engineering/policies/architecture.yaml"
    policy.write_text(yaml.safe_dump({"schema_version": 1, "forbidden_dependencies": [{"id": "R1", "from": "SRC-src/a.py", "to": "SRC-src/b.py"}], "exceptions": [{"id": "EX-1", "rule_id": "R1", "adr": "ADR-1", "from": "SRC-src/a.py", "to": "SRC-src/b.py", "review_until": "2099-01-01T00:00:00Z"}]}), encoding="utf-8")
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "architecture", "validate"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "passed"


def test_cli_unknown_module_coverage_and_explicit_policy(tmp_path):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import yaml

    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]
    def run(*args):
        result = subprocess.run(base + list(args), env=env, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)
    assert run("init")[0] == 0
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs/module.md").write_text("---\nid: MOD-A\ntype: Module\nname: A\n---\n")
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src/a.py").write_text("value = 1\n")
    assert run("graph", "build")[0] == 0
    code, blocked = run("architecture", "validate")
    assert code != 0 and blocked["data"]["status"] == "fail"
    assert any(u["code"] == "EPE-ARCH-MODULE-COVERAGE" for u in blocked["data"]["unknowns"])
    policy = tmp_path / "engineering/policies/architecture.yaml"
    policy.write_text(yaml.safe_dump({"schema_version": 1, "forbidden_dependencies": [], "unknown_is_blocking": False}))
    code, allowed = run("architecture", "validate")
    assert code == 0 and allowed["data"]["status"] == "unknown"
    assert any(d["severity"] == "warning" for d in allowed["diagnostics"])
    policy.write_text(yaml.safe_dump({"schema_version": 1, "forbidden_dependencies": [], "unknown_is_blocking": ""}))
    code, invalid = run("architecture", "validate")
    assert code != 0 and any(d["code"] == "EPE-ARCH-POLICY" for d in invalid["diagnostics"])
