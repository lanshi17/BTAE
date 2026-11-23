import json

from epe.cli import main


def test_design_create_is_typed_safe_and_idempotent(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "design", "create", "CLASS-NEW-001"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["data"]["type"] == "Class"
    path = tmp_path / created["data"]["path"]
    original = path.read_bytes()
    assert b"type: Class" in original
    assert main(["--root", str(tmp_path), "--format", "json", "design", "create", "CLASS-NEW-001"]) == 1
    assert path.read_bytes() == original
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "design", "create", "UNKNOWN-001"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_created_design_is_discoverable_and_validation_reports_revision(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "design", "create", "MOD-NEW-001"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "inspect"]) == 0
    assert "MOD-NEW-001" in json.loads(capsys.readouterr().out)["data"]["entities"]
    assert main(["--root", str(tmp_path), "--format", "json", "design", "validate", "MOD-NEW-001"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["data"]["revision"]) == 64


def test_contract_entity_round_trips_and_validates_schema(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "--format", "json", "init"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "--format", "json", "design", "create", "CONTRACT-NEW-001"]) == 0
    created = json.loads(capsys.readouterr().out)
    contract_path = tmp_path / created["data"]["path"]
    raw = contract_path.read_text()
    assert "schema:" in raw
    assert main(["--root", str(tmp_path), "--format", "json", "inspect"]) == 0
    assert "CONTRACT-NEW-001" in json.loads(capsys.readouterr().out)["data"]["entities"]
    assert main(["--root", str(tmp_path), "--format", "json", "graph", "build"]) == 0
    built = json.loads(capsys.readouterr().out)
    assert built["data"]["published"] is True
    entities = json.loads((tmp_path / ".engineering/generations" / built["data"]["content_digest"] / "entities.json").read_text())
    stored = next(item for item in entities["entities"] if item["id"] == "CONTRACT-NEW-001")
    assert stored["version"] == 1 and stored["schema"] == {}
    assert main(["--root", str(tmp_path), "--format", "json", "design", "validate", "CONTRACT-NEW-001"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["revision"]

    (tmp_path / "docs/classes").mkdir(parents=True)
    (tmp_path / "docs/classes/CLASS-001.md").write_text(
        "---\nid: CLASS-001\ntype: Class\nname: Consumer\ndesign_status: reviewed\ncontracts: [CONTRACT-NEW-001]\n---\n",
        encoding="utf-8",
    )
    contract = __import__("yaml").safe_load(contract_path.read_text())
    contract["schema"] = {"type": "not-a-json-schema-type"}
    contract_path.write_text(__import__("yaml").safe_dump(contract, sort_keys=False))
    assert main(["--root", str(tmp_path), "--format", "json", "design", "validate", "CLASS-001"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "EPE-CONTRACT-SCHEMA" for d in result["diagnostics"])
