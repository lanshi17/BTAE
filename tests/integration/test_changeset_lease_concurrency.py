import json
import os
import subprocess
import sys
import time
from pathlib import Path

from epe.cli import main


def _lease_project(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "init"]) == 0
    capsys.readouterr()
    tasks = tmp_path / "engineering/tasks"; tasks.mkdir(parents=True, exist_ok=True)
    changes = tmp_path / "engineering/changesets"; changes.mkdir(parents=True, exist_ok=True)
    (tasks / "TASK-001.json").write_text(json.dumps({
        "schema_version": 1, "id": "TASK-001", "type": "feature", "objective": "lease",
        "acceptance": ["one winner"], "risk": "low", "target_entities": ["MOD-001"],
        "changeset": "CHANGE-001", "status": "active", "revision": 1,
    }))
    (changes / "CHANGE-001.json").write_text(json.dumps({
        "schema_version": 1, "id": "CHANGE-001", "task": "TASK-001", "owner": "alice",
        "affected_entities": ["MOD-001"], "write_scope": ["src/**"], "protected": [],
        "dependencies": [], "status": "active", "revision": 1,
    }))


def test_two_cli_processes_only_one_acquires_the_same_lease(tmp_path, capsys):
    _lease_project(tmp_path, capsys)
    command = [sys.executable, "-m", "epe.cli", "--root", str(tmp_path), "--format", "json",
               "changeset", "lease", "acquire", "CHANGE-001", "--owner", "alice", "--ttl", "30"]
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[2] / "src"))
    first = subprocess.Popen(command, cwd=Path(__file__).parents[2], env=environment, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    second = subprocess.Popen(command, cwd=Path(__file__).parents[2], env=environment, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    first_out, first_err = first.communicate(timeout=10)
    second_out, second_err = second.communicate(timeout=10)
    results = [json.loads(first_out), json.loads(second_out)]
    statuses = sorted(result["status"] for result in results)
    assert statuses == ["blocked", "passed"], (results, first_err, second_err)
    assert sum(result["status"] == "passed" for result in results) == 1


def test_lease_can_be_recovered_after_owner_process_is_killed(tmp_path, capsys):
    _lease_project(tmp_path, capsys)
    repo = Path(__file__).parents[2]
    code = """
import os, signal, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from epe.adapters.repository import load_config
from epe.governance.leases import acquire_lease
root = Path(sys.argv[2]); config, diagnostics = load_config(root)
assert config and not diagnostics
change = {'id':'CHANGE-001','status':'active','owner':'alice','revision':1}
acquire_lease(root, config, change, 'alice', 0.25)
os.kill(os.getpid(), signal.SIGKILL)
"""
    environment = dict(os.environ, PYTHONPATH=str(repo / "src"))
    crashed = subprocess.run([sys.executable, "-c", code, str(repo / "src"), str(tmp_path)],
                             cwd=repo, env=environment, text=True, capture_output=True)
    assert crashed.returncode < 0
    time.sleep(0.4)
    result = subprocess.run([
        sys.executable, "-m", "epe.cli", "--root", str(tmp_path), "--format", "json",
        "changeset", "lease", "acquire", "CHANGE-001", "--owner", "alice", "--ttl", "30",
    ], cwd=repo, env=environment, text=True, capture_output=True, check=False)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["status"] == "passed"
