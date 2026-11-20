from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


SOURCE = Path(__file__).resolve().parents[2] / "src"


def run_cli(root: Path, *args: str):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    process = subprocess.run(
        [sys.executable, "-m", "epe", "--root", str(root), "--format", "json", *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert process.stderr == "", process.stderr
    result = json.loads(process.stdout)
    assert result["command"] and isinstance(result["diagnostics"], list)
    assert "Traceback" not in process.stderr
    return process.returncode, result


def test_ac03_multi_file_mapping_passes_then_deleted_symbol_blocks(tmp_path):
    code, result = run_cli(tmp_path, "init")
    assert code == 0 and result["status"] == "passed"
    (tmp_path / "docs/classes").mkdir(parents=True)
    (tmp_path / "src/first").mkdir(parents=True)
    (tmp_path / "src/second").mkdir(parents=True)
    (tmp_path / "docs/classes/CLASS-001.md").write_text(
        "---\nid: CLASS-001\ntype: Class\nname: Composite\nimplementation_status: implemented\n"
        "implementation:\n  - path: src/first/one.py\n    symbol: One\n"
        "  - path: src/second/two.py\n    symbol: Two\n---\n",
        encoding="utf-8",
    )
    first = tmp_path / "src/first/one.py"
    second = tmp_path / "src/second/two.py"
    first.write_text("class One:\n    pass\n", encoding="utf-8")
    second.write_text("class Two:\n    pass\n", encoding="utf-8")
    code, result = run_cli(tmp_path, "mapping", "validate")
    assert code == 0 and result["status"] == "passed"
    assert result["data"]["checked"] == 1 and result["data"]["symbols"] == 2

    second.write_text("class Renamed:\n    pass\n", encoding="utf-8")
    code, result = run_cli(tmp_path, "mapping", "validate")
    assert code == 1 and result["status"] == "blocked"
    diagnostic = next(item for item in result["diagnostics"] if item["code"] == "EPE-MAPPING-SYMBOL")
    assert diagnostic["entity_id"] == "CLASS-001"
    assert diagnostic["path"] == "src/second/two.py"
