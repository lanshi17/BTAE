import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

from epe.adapters.repository import default_config, load_config


def test_default_schema_and_invalid_config_diagnostics(tmp_path):
    path = tmp_path / "engineering/epe.yaml"; path.parent.mkdir()
    def check(config):
        path.write_text(yaml.safe_dump(config))
        return load_config(tmp_path)
    assert check(default_config())[0] == default_config()
    for change in ({"managed": []}, {"managed": {"module_roots": {"MOD-A": "src/a"}}},
                   {"storage": {"tasks": "../outside"}}, {"policies": {"architecture": "/tmp/a"}},
                   {"unknown_field": True}, {"schema_version": True}, {"exclude": [3]}):
        config = default_config() | change
        result, diagnostics = check(config)
        assert result is None and diagnostics and diagnostics[0].code.startswith("EPE-CONFIG-")
    outside = tmp_path.parent / (tmp_path.name + "-outside"); outside.mkdir()
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    config = default_config() | {"storage": {"tasks": "escape/tasks"}}
    assert check(config)[1][0].code == "EPE-CONFIG-PATH"
    path.write_text("schema_version: 1\nfoo: 2020-01-01\n")
    assert load_config(tmp_path)[1][0].code == "EPE-CONFIG-INVALID"
    path.write_text("schema_version: 1\nmanaged: &managed\n  code_roots: [*managed]\n")
    assert load_config(tmp_path)[1][0].code == "EPE-CONFIG-INVALID"
    path.write_text("")
    assert load_config(tmp_path)[1][0].code == "EPE-CONFIG-TYPE"


def test_config_failure_is_structured_for_real_cli(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    base = [sys.executable, "-m", "epe", "--root", str(tmp_path), "--format", "json"]
    assert subprocess.run(base + ["init"], env=env, capture_output=True).returncode == 0
    (tmp_path / "engineering/epe.yaml").write_text("schema_version: 1\nmanaged: []\n")
    for command in (["inspect"], ["graph", "build"], ["task", "classify", "TASK-1"]):
        result = subprocess.run(base + command, env=env, capture_output=True, text=True)
        assert result.returncode == 2 and "Traceback" not in result.stderr
        assert json.loads(result.stdout)["diagnostics"][0]["code"] == "EPE-CONFIG-INVALID"


def test_config_rejects_symlinked_parent_directory(tmp_path):
    outside = tmp_path.parent / "config-parent-outside"; outside.mkdir()
    (tmp_path / "engineering").symlink_to(outside, target_is_directory=True)
    result, diagnostics = load_config(tmp_path)
    assert result is None and diagnostics[0].code == "EPE-PATH-SYMLINK"


def test_config_rejects_internal_symlinked_managed_root(tmp_path):
    engineering = tmp_path / "engineering"; engineering.mkdir()
    outside = tmp_path / "real-src"; outside.mkdir()
    (tmp_path / "src").symlink_to(outside, target_is_directory=True)
    config = default_config(); config["managed"]["code_roots"] = ["src"]
    (engineering / "epe.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    result, diagnostics = load_config(tmp_path)
    assert result is None and diagnostics[0].code == "EPE-PATH-SYMLINK"


def test_packaged_schema_matches_repository_schema():
    root = Path(__file__).resolve().parents[2]
    assert (root / "engineering/schemas/project-config.schema.json").read_bytes() == (root / "src/epe/data/schemas/project-config.schema.json").read_bytes()
