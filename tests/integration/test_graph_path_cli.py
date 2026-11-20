import json
import os
from pathlib import Path
import subprocess
import sys


def test_graph_path_cli_queries_current_snapshot_and_rejects_stale(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]
    def run(*args):
        result = subprocess.run(base + list(args), env=env, capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)
    assert run("init")[0] == 0
    docs = tmp_path / "docs"; docs.mkdir(exist_ok=True)
    (docs / "module.md").write_text('---\nid: MOD-A\ntype: Module\nname: A\nrelations:\n  - relation: contains\n    to: CLASS-B\n---\n')
    (docs / "class.md").write_text('---\nid: CLASS-B\ntype: Class\nname: B\n---\n')
    assert run("graph", "build")[0] == 0
    code, response = run("graph", "path", "MOD-A", "CLASS-B")
    assert code == 0 and response["data"]["found"]
    assert response["data"]["path"][0]["edge"]["origin"]["source"] == "docs/module.md"
    code, response = run("graph", "path", "MOD-A", "CLASS-B", "--relation", "depends_on")
    assert code == 0 and not response["data"]["found"] and not response["data"]["truncated"]
    assert run("graph", "path", "MOD-A", "CLASS-MISSING")[0] != 0
    (docs / "class.md").write_text('---\nid: CLASS-B\ntype: Class\nname: Changed\n---\n')
    code, response = run("graph", "path", "MOD-A", "CLASS-B")
    assert code != 0 and any(d["code"] == "EPE-GRAPH-STALE" for d in response["diagnostics"])
