from epe.verification.import_boundaries import validate_import_boundaries


def test_core_cannot_import_cli(tmp_path):
    src = tmp_path / "src/epe/core"; src.mkdir(parents=True)
    (src / "bad.py").write_text("from epe.cli import main\n")
    config = {"managed": {"code_roots": ["src"]}}
    report, diagnostics = validate_import_boundaries(tmp_path, config, {})
    assert report["status"] == "fail"
    assert any(d.code == "EPE-ARCH-IMPORT" for d in diagnostics)


def test_allowed_imports_can_be_configured(tmp_path):
    src = tmp_path / "src/epe/core"; src.mkdir(parents=True)
    (src / "ok.py").write_text("from epe.cli import main\n")
    config = {"managed": {"code_roots": ["src"]}}
    report, diagnostics = validate_import_boundaries(tmp_path, config, {"allowed_imports": {"core": ["cli"]}})
    assert report["status"] == "pass"
    assert not any(d.code == "EPE-ARCH-IMPORT" for d in diagnostics)
