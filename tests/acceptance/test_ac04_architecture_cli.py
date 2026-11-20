from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_ac04_forbidden_import_module_cycle_and_dynamic_gap_are_reported(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        result = json.loads(process.stdout)
        assert process.returncode == expected, result
        return result

    initialized = run("init")
    assert initialized["status"] == "passed"
    (tmp_path / "src/a").mkdir(parents=True)
    (tmp_path / "src/b").mkdir(parents=True)
    (tmp_path / "src/epe/core").mkdir(parents=True)
    (tmp_path / "docs/modules").mkdir(parents=True)
    for module, name in (("MOD-A", "A"), ("MOD-B", "B")):
        (tmp_path / f"docs/modules/{module}.md").write_text(
            f"---\nid: {module}\ntype: Module\nname: {name}\n---\n", encoding="utf-8"
        )
    (tmp_path / "src/a/a.py").write_text(
        "import b.b\n__import__('runtime_selected')\nclass A: pass\n", encoding="utf-8"
    )
    (tmp_path / "src/b/b.py").write_text("import a.a\nclass B: pass\n", encoding="utf-8")
    (tmp_path / "src/epe/core/bad.py").write_text("from epe.cli import main\n", encoding="utf-8")

    config_path = tmp_path / "engineering/epe.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["managed"]["module_roots"] = {"MOD-A": ["src/a", "src/epe/core"], "MOD-B": ["src/b"]}
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    architecture_path = tmp_path / "engineering/policies/architecture.yaml"
    architecture_path.write_text(yaml.safe_dump({
        "schema_version": 1,
        "forbidden_dependencies": [{
            "id": "NO-A-TO-B",
            "from": "SRC-src/a/a.py",
            "to": "SRC-src/b/b.py",
        }],
        "unknown_is_blocking": True,
        "allowed_imports": {},
    }, sort_keys=False), encoding="utf-8")

    graph = run("graph", "build")
    assert graph["data"]["published"] is True
    report = run("architecture", "validate", expected=1)
    assert report["status"] == "blocked"
    assert report["data"]["module_coverage"] == "configured"
    codes = {item["code"] for item in report["diagnostics"]}
    assert {"EPE-ARCH-CYCLE", "EPE-ARCH-FORBIDDEN", "EPE-ARCH-IMPORT", "EPE-ARCH-UNKNOWN"} <= codes
    cycle = next(item for item in report["data"]["violations"] if item["rule"] == "ARCH-CYCLE")
    assert cycle["path"][0].startswith("MOD-") and cycle["edge_evidence"]
    forbidden_import = next(item for item in report["data"]["import_boundaries"]["violations"])
    assert forbidden_import["path"] == "src/epe/core/bad.py" and forbidden_import["line"] == 1
    gap = next(item for item in report["data"]["unknowns"] if item["code"] == "EPE-AST-DYNAMIC")
    assert gap["path"] == "src/a/a.py" and gap["line"] == 2
