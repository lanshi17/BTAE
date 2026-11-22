import subprocess
import sys


def test_runtime_schema_package_is_importable():
    result = subprocess.run([sys.executable, "-c", "from importlib.resources import files; names=('policy.schema.json','evidence.schema.json','agent-request.schema.json','agent-response.schema.json','command-result.schema.json'); print(all(files('epe.data.schemas').joinpath(name).is_file() for name in names))"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "True"
