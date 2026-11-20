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
