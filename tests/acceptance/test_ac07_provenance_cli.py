from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_ac07_uncommitted_git_facts_and_input_changes_stale_old_evidence(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]

    def run(*args: str, expected: int = 0):
        process = subprocess.run(base + list(args), cwd=tmp_path, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        result = json.loads(process.stdout)
        assert process.returncode == expected, result
        assert result["command"] and isinstance(result["diagnostics"], list)
        return result

    assert run("init")["status"] == "passed"
    (tmp_path / "docs/classes").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "engineering/contracts").mkdir(parents=True)
    (tmp_path / "engineering/contracts/CONTRACT-001.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "CONTRACT-001", "type": "Contract", "name": "Value contract",
        "version": 1, "schema": {"type": "object"},
    }, sort_keys=False), encoding="utf-8")
    (tmp_path / "docs/classes/CLASS-001.md").write_text(
        "---\nid: CLASS-001\ntype: Class\nname: Example\ndesign_status: reviewed\n"
        "implementation_status: implemented\ncontracts: [CONTRACT-001]\n"
        "implementation:\n  - path: src/item.py\n    symbol: Example\n---\n# Example\n",
        encoding="utf-8",
    )
    source = tmp_path / "src/item.py"
    source.write_text("class Example:\n    def value(self):\n        return 1\n", encoding="utf-8")
    test_file = tmp_path / "tests/test_value.py"
    test_file.write_text("def test_value():\n    assert 1 == 1\n", encoding="utf-8")
    config_path = tmp_path / "engineering/epe.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["managed"].setdefault("contract_roots", ["engineering/contracts"])
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    (tmp_path / "engineering/policies/verification.yaml").write_text(yaml.safe_dump({
        "schema_version": 1,
        "checks": [{"id": "pytest", "kind": "test", "result_parser": "pytest",
                    "command": [sys.executable, "-m", "pytest", "-q", "tests"], "timeout": 30}],
    }, sort_keys=False), encoding="utf-8")

    git = subprocess.run(["git", "init", "-q"], cwd=tmp_path, capture_output=True, text=True)
    assert git.returncode == 0, git.stderr
    (tmp_path / "task.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "AC-07 provenance",
        "acceptance": ["evidence freshness reflects source inputs"], "risk": "low",
        "target_entities": ["CLASS-001"], "changeset": "CHANGE-001",
    }, sort_keys=False), encoding="utf-8")
    (tmp_path / "change.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "id": "CHANGE-001", "task": "TASK-001", "owner": "fixture",
        "affected_entities": ["CLASS-001"], "write_scope": ["**"], "protected": [],
        "dependencies": [], "status": "planned",
    }, sort_keys=False), encoding="utf-8")
    run("task", "create", "--file", "task.yaml")
    run("task", "transition", "TASK-001", "activate")
    run("changeset", "create", "--file", "change.yaml")
    run("changeset", "transition", "CHANGE-001", "activate")
    run("graph", "build")
    verified = run("verify", "TASK-001")
    assert verified["status"] == "passed"
    run("check", "--task", "TASK-001")
    first = json.loads(next((tmp_path / "engineering/evidence").glob("*/evidence.json")).read_text(encoding="utf-8"))
    assert first["validity"] == "valid"
    provenance = first["provenance"]["git"]
    assert provenance["git_available"] is True and provenance["commit"] is None
    assert provenance["dirty"] is True and any(path.rstrip("/") == "src" for path in provenance["untracked"])

    mutations = [
        ("source", source, "class Example:\n    def value(self):\n        return 2\n"),
        ("contract", tmp_path / "engineering/contracts/CONTRACT-001.yaml",
         (tmp_path / "engineering/contracts/CONTRACT-001.yaml").read_text(encoding="utf-8") + "# revised contract source\n"),
        ("test", test_file, "def test_value():\n    assert 2 == 2\n"),
    ]
    evidence_path = tmp_path / "engineering/evidence" / first["run_id"] / "evidence.json"
    for name, path, content in mutations:
        path.write_text(content, encoding="utf-8")
        run("graph", "build")
        checked = run("check", "--task", "TASK-001", expected=1)
        stale = next(item for item in checked["data"]["evidence"] if item["run_id"] == first["run_id"])
        assert stale["validity"] == "stale", name
        assert json.loads(evidence_path.read_text(encoding="utf-8"))["validity"] == "valid"
