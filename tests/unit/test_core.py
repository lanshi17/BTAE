from epe.core.fingerprint import build_manifest, sha256_json
from epe.core.registry import build_registry


def test_registry_rejects_duplicate_and_dangling_relation():
    result = build_registry([
        ({"id": "MOD-001", "type": "Module", "name": "one"}, "one.md", 1),
        ({"id": "MOD-001", "type": "Module", "name": "two"}, "two.md", 1),
    ], [({"from": "MOD-001", "to": "MOD-404", "relation": "contains"}, "relations.yaml")])
    codes = {d.code for d in result.diagnostics}
    assert "EPE-ENTITY-DUPLICATE" in codes
    assert "EPE-RELATION-DANGLING" in codes
    assert not result.complete


def test_manifest_is_order_independent(tmp_path):
    (tmp_path / "a.txt").write_bytes("a".encode())
    (tmp_path / "b.txt").write_bytes("b".encode())
    first = build_manifest(tmp_path)
    second = build_manifest(tmp_path)
    assert first == second
    assert sha256_json([{"path": p, "sha256": h} for p, h in first.entries]) == first.digest


def test_manifest_rejects_nested_symlink_directory(tmp_path):
    real = tmp_path / "real"; real.mkdir()
    (real / "file.txt").write_text("value", encoding="utf-8")
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)
    import pytest
    with pytest.raises(ValueError, match="符号链接目录"):
        build_manifest(tmp_path)


def test_entity_schema_rejects_invalid_source_mappings_and_unknown_fields():
    from epe.core.registry import validate_entity_dict
    base = {"id": "CLASS-1", "type": "Class", "name": "Class", "source": {"path": "docs/class.md"}}
    for value in ({**base, "unknown": True}, {**base, "name": ""}, {**base, "source": {"path": "../outside"}}, {**base, "implementation": ["src/x.py"]}, {**base, "contracts": [None]}, {**base, "extensions": []}):
        entity, diagnostics = validate_entity_dict(value, "docs/class.md", 1)
        assert entity is None and diagnostics


def test_entity_schema_accepts_valid_mapping_and_source_location():
    from epe.core.registry import validate_entity_dict
    entity, diagnostics = validate_entity_dict({"schema_version": 1, "id": "CLASS-1", "type": "Class", "name": "Class", "source": {"path": "docs/class.md", "line": 2}, "implementation": [{"path": "src/class.py", "symbol": "Class"}], "verification": [{"path": "tests/test_class.py"}], "contracts": ["CONTRACT-1"], "extensions": {"owner": "team"}}, "docs/class.md", 1)
    assert entity is not None and not diagnostics


def test_repository_port_reads_only_regular_in_root_files(tmp_path):
    from epe.adapters.repository import Repository
    repo = Repository(tmp_path)
    (tmp_path / "file.txt").write_bytes(b"bytes")
    assert repo.read_bytes("file.txt") == b"bytes"
    assert repo.exists("file.txt")
    import pytest
    with pytest.raises(ValueError): repo.safe_path("../outside")
    outside = tmp_path.parent / "outside-file"; outside.write_bytes(b"secret")
    (tmp_path / "link").symlink_to(outside)
    with pytest.raises(ValueError): repo.read_bytes("link")
    assert not repo.exists("link")


def test_repository_rejects_symlinked_parent_directory(tmp_path):
    from epe.adapters.repository import Repository
    outside = tmp_path.parent / "outside-parent"; outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    with __import__("pytest").raises(ValueError):
        Repository(tmp_path).safe_path("linked/file.txt")


def test_invalid_unhashable_entity_fields_do_not_crash():
    from epe.core.registry import validate_entity_dict
    base = {"id": "CLASS-1", "type": "Class", "name": "Example"}
    for patch in ({"type": []}, {"design_status": {}}, {"implementation": False}, {"contracts": {}}, {3: "bad"}):
        entity, diagnostics = validate_entity_dict({**base, **patch}, "bad.md", 2)
        assert entity is None and diagnostics
        assert all(d.path == "bad.md" for d in diagnostics)


def test_invalid_relation_metadata_and_explicit_array_values():
    from epe.core.registry import build_registry, validate_entity_dict

    for field in ("implementation", "verification", "contracts", "relations"):
        for value in (False, {}, None):
            entity, diagnostics = validate_entity_dict({"id": "CLASS-A", "type": "Class", "name": "A", field: value}, "a.md")
            assert entity is None and diagnostics
    candidates = [({"id": "MOD-A", "type": "Module", "name": "A"}, "a.md", 1),
                  ({"id": "CLASS-B", "type": "Class", "name": "B"}, "b.md", 1)]
    base = {"from": "MOD-A", "to": "CLASS-B", "relation": "contains"}
    for extra, code in (({"origin": {"type": [], "source": "a.md"}}, "EPE-RELATION-ORIGIN"),
                        ({"origin": {}}, "EPE-RELATION-ORIGIN"),
                        ({"confidence": True}, "EPE-RELATION-CONFIDENCE")):
        result = build_registry(candidates, [(base | extra, "a.md")])
        assert not result.complete and any(d.code == code for d in result.diagnostics)
