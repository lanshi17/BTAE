from pathlib import Path


def test_runtime_schema_validator_is_declared_in_project_metadata():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "jsonschema>=4.20" in text
