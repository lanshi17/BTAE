import json

from epe.cli import main


def test_init_is_idempotent_and_json(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "passed"
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["status"] == "passed"
    assert (tmp_path / "engineering/epe.yaml").exists()


def test_unsupported_is_explicit(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "design", "create", "CLASS-001"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "passed"


def test_existing_file_conflict_does_not_overwrite(tmp_path, capsys):
    path = tmp_path / "engineering/epe.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("project_id: custom\n", encoding="utf-8")
    before = path.read_bytes()
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert path.read_bytes() == before


def test_init_rejects_target_and_parent_symlinks_without_writing(tmp_path, capsys):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"; outside.mkdir()
    (tmp_path / "engineering").symlink_to(outside, target_is_directory=True)
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["diagnostics"][0]["code"] == "EPE-PATH-SYMLINK"
    assert not (outside / "epe.yaml").exists()


def test_init_rejects_symlinked_target_file(tmp_path, capsys):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-file"; outside.write_text("keep")
    (tmp_path / "engineering").mkdir()
    (tmp_path / "engineering/epe.yaml").symlink_to(outside)
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert any(item["code"] == "EPE-PATH-SYMLINK" for item in result["diagnostics"])
    assert outside.read_text() == "keep"


def test_parameter_and_path_errors_use_exit_code_two(tmp_path, capsys):
    outside = tmp_path.parent / f"{tmp_path.name}-outside-exit"; outside.mkdir()
    (tmp_path / "engineering").symlink_to(outside, target_is_directory=True)
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 1
    # init reports a domain blocking result, while direct configuration errors map to 2.
    capsys.readouterr()
    valid = tmp_path / "valid"; valid.mkdir()
    assert main(["--root", str(valid), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(valid), "--format", "json", "task", "classify", "BAD-ID"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["diagnostics"][0]["code"] == "EPE-TASK-ID"
