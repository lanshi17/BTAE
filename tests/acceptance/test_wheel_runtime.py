import subprocess
import sys
from pathlib import Path


def test_runtime_schema_package_is_importable():
    result = subprocess.run([sys.executable, "-c", "from importlib.resources import files; names=('approval.schema.json','agent-request.schema.json','agent-response.schema.json','changeset-baseline.schema.json','changeset.schema.json','command-result.schema.json','contract.schema.json','entity.schema.json','evidence.schema.json','policy.schema.json','project-config.schema.json','relation.schema.json','task.schema.json','workflow.schema.json'); print(all(files('epe.data.schemas').joinpath(name).is_file() for name in names))"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "True"


def test_packaged_schemas_match_authoritative_schemas():
    import json
    from importlib.resources import files

    for source in sorted(Path("engineering/schemas").glob("*.json")):
        packaged = json.loads(files("epe.data.schemas").joinpath(source.name).read_text(encoding="utf-8"))
        assert packaged == json.loads(source.read_text(encoding="utf-8")), source.name


def test_all_authoritative_schemas_are_packaged():
    from importlib.resources import files
    names = {path.name for path in Path("engineering/schemas").glob("*.json")}
    packaged = {item.name for item in files("epe.data.schemas").iterdir() if item.name.endswith(".json")}
    assert names <= packaged
