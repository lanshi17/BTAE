from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_ac02_registry_failures_are_separate_cli_diagnostics(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        result = json.loads(process.stdout)
        assert process.returncode != 0
        assert result["status"] == "error"
        assert "Traceback" not in process.stderr
        return result

    init = subprocess.run(base + ["init"], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert init.returncode == 0 and json.loads(init.stdout)["status"] == "passed"
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)

    # Two independent declarations with one stable identity.
    (docs / "one.md").write_text("---\nid: CLASS-DUP\ntype: Class\nname: One\n---\n", encoding="utf-8")
    (docs / "two.md").write_text("---\nid: CLASS-DUP\ntype: Class\nname: Two\n---\n", encoding="utf-8")
    result = run("graph", "build")
    duplicate = next(item for item in result["diagnostics"] if item["code"] == "EPE-ENTITY-DUPLICATE")
    assert duplicate["entity_id"] == "CLASS-DUP" and duplicate["path"] == "docs/two.md"
    assert result["data"]["published"] is False
    (docs / "one.md").unlink(); (docs / "two.md").unlink()

    # YAML syntax errors keep source coordinates and do not become candidates.
    (docs / "bad.md").write_text("---\nid: CLASS-BAD\ntype: Class\ntype: Module\nname: Bad\n---\n", encoding="utf-8")
    result = run("graph", "build")
    duplicate_key = next(item for item in result["diagnostics"] if item["code"] == "EPE-YAML-PARSE")
    assert duplicate_key["path"] == "docs/bad.md" and duplicate_key["line"] == 4
    assert result["data"]["published"] is False
    (docs / "bad.md").unlink()

    # The relation remains explicit and is rejected after entity registration.
    (docs / "source.md").write_text(
        "---\nid: MOD-A\ntype: Module\nname: A\nrelations:\n"
        "  - to: CLASS-MISSING\n    relation: contains\n---\n",
        encoding="utf-8",
    )
    result = run("graph", "build")
    dangling = next(item for item in result["diagnostics"] if item["code"] == "EPE-RELATION-DANGLING")
    assert dangling["path"] == "docs/source.md"
    assert dangling["message"].endswith("MOD-A -> CLASS-MISSING")
    assert result["data"]["published"] is False
    assert not (tmp_path / ".engineering/current.json").exists()
