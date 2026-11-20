from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


SOURCE = Path(__file__).resolve().parents[2] / "src"


def test_ac11_four_task_types_register_and_required_activation_facts_block(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(SOURCE))
    def run(root: Path, *args: str, expected: int = 0):
        process = subprocess.run([sys.executable, "-m", "epe", "--root", str(root), "--format", "json", *args], cwd=root, env=env, capture_output=True, text=True)
        assert process.stderr == "", process.stderr
        lines = [line for line in process.stdout.splitlines() if line.strip()]
        assert len(lines) == 1
        result = json.loads(lines[0])
        assert process.returncode == expected, result
        return result

    workflows = {
        "feature": {},
        "bugfix": {"reproduction": "reproduced in fixture"},
        "refactor": {"baseline_manifest": "baseline-fixture"},
        "exploration": {"hypothesis": "hypothesis-fixture"},
    }
    for index, (kind, extra) in enumerate(workflows.items(), start=1):
        root = tmp_path / kind; root.mkdir()
        run(root, "init")
        data = {"schema_version": 1, "id": f"TASK-{index:03d}", "type": kind,
                "objective": f"{kind} objective", "acceptance": ["activation is explicit"],
                "risk": "low", "target_entities": ["MOD-001"], **extra}
        path = root / "task.yaml"; path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        created = run(root, "task", "create", "--file", "task.yaml")
        assert created["status"] == "passed" and created["data"]["type"] == kind
        active = run(root, "task", "transition", data["id"], "activate")
        assert active["status"] == "passed" and active["data"]["status"] == "active"

    missing_cases = {
        "bugfix": ("reproduction", "EPE-TASK-REPRODUCTION"),
        "refactor": ("baseline_manifest", "EPE-TASK-BASELINE"),
        "exploration": ("hypothesis", "EPE-TASK-HYPOTHESIS"),
    }
    for index, (kind, (field, expected_code)) in enumerate(missing_cases.items(), start=10):
        root = tmp_path / f"missing-{kind}"; root.mkdir()
        run(root, "init")
        data = {"schema_version": 1, "id": f"TASK-{index:03d}", "type": kind,
                "objective": "missing required workflow evidence", "acceptance": ["required evidence"],
                "risk": "low", "target_entities": ["MOD-001"]}
        path = root / "task.yaml"; path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        run(root, "task", "create", "--file", "task.yaml")
        blocked = run(root, "task", "transition", data["id"], "activate", expected=1)
        assert blocked["status"] == "blocked"
        assert any(item["code"] == expected_code for item in blocked["diagnostics"])
        stored = json.loads((root / "engineering/tasks" / f"{data['id']}.json").read_text(encoding="utf-8"))
        assert stored["status"] == "planned"

    root = tmp_path / "missing-acceptance"; root.mkdir()
    run(root, "init")
    data = {"schema_version": 1, "id": "TASK-020", "type": "feature", "objective": "missing acceptance", "acceptance": [], "risk": "low", "target_entities": ["MOD-001"]}
    path = root / "task.yaml"; path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    created = run(root, "task", "create", "--file", "task.yaml", expected=2)
    assert created["status"] == "error" and any(item["code"] == "EPE-TASK-ACCEPTANCE" for item in created["diagnostics"])
