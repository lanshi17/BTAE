from pathlib import Path

from epe.design.manager import validate_contract
from epe.core.models import Entity, SourceLocation


def entity(path):
    return Entity(1, "CONTRACT-001", "Contract", "Contract", SourceLocation(path))


def test_contract_schema_is_checked(tmp_path):
    path = tmp_path / "contract.yaml"
    path.write_text("schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: C\nversion: 1\nschema:\n  type: string\n")
    data, diagnostics = validate_contract(entity("contract.yaml"), tmp_path)
    assert not diagnostics and data["supported"]


def test_invalid_contract_schema_blocks_design(tmp_path):
    path = tmp_path / "contract.yaml"
    path.write_text("schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: C\nversion: 1\nschema:\n  type: nope\n")
    _, diagnostics = validate_contract(entity("contract.yaml"), tmp_path)
    assert diagnostics and diagnostics[0].code == "EPE-CONTRACT-SCHEMA"


def test_contract_rejects_unresolved_external_reference(tmp_path):
    path = tmp_path / "contract.yaml"
    path.write_text("schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: C\nversion: 1\nschema:\n  $ref: refs/missing.json\n")
    _, diagnostics = validate_contract(entity("contract.yaml"), tmp_path)
    assert diagnostics and diagnostics[0].code == "EPE-CONTRACT-REF"


def test_contract_resolves_repository_relative_reference_and_pointer(tmp_path):
    refs = tmp_path / "refs.json"
    refs.write_text('{"$defs": {"Value": {"type": "string"}}}', encoding="utf-8")
    path = tmp_path / "contract.yaml"
    path.write_text("schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: C\nversion: 1\nschema:\n  $ref: refs.json#/$defs/Value\n", encoding="utf-8")
    data, diagnostics = validate_contract(entity("contract.yaml"), tmp_path)
    assert not diagnostics and data["supported"]


def test_contract_rejects_remote_reference(tmp_path):
    path = tmp_path / "contract.yaml"
    path.write_text("schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: C\nversion: 1\nschema:\n  $ref: https://example.invalid/schema.json\n", encoding="utf-8")
    _, diagnostics = validate_contract(entity("contract.yaml"), tmp_path)
    assert diagnostics and diagnostics[0].code == "EPE-CONTRACT-REF"


def test_contract_rejects_external_document_that_is_not_a_schema(tmp_path):
    (tmp_path / "refs.json").write_text('{"type": "not-a-schema-type"}', encoding="utf-8")
    path = tmp_path / "contract.yaml"
    path.write_text("schema_version: 1\nid: CONTRACT-001\ntype: Contract\nname: C\nversion: 1\nschema:\n  $ref: refs.json\n", encoding="utf-8")
    _, diagnostics = validate_contract(entity("contract.yaml"), tmp_path)
    assert diagnostics and diagnostics[0].code == "EPE-CONTRACT-REF"
