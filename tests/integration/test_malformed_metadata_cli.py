import json
import os
from pathlib import Path
import subprocess
import sys


def test_graph_build_reports_malformed_metadata_without_traceback(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]
    init = subprocess.run(base + ["init"], env=env, capture_output=True, text=True)
    assert init.returncode == 0, init.stderr
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    document = docs / "bad.md"
    for content, expected in (("id: CLASS-A\ntype: []\nname: A\n", "EPE-ENTITY-FIELD"),
                              ("? [a, b]\n: value\n", "EPE-YAML-PARSE")):
        document.write_text("---\n" + content + "---\n", encoding="utf-8")
        result = subprocess.run(base + ["graph", "build"], env=env, capture_output=True, text=True)
        assert result.returncode != 0
        assert "Traceback" not in result.stderr
        payload = json.loads(result.stdout)
        assert any(item["code"] == expected and item.get("path") == "docs/bad.md" for item in payload["diagnostics"])
