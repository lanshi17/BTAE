import subprocess
import sys


def test_runtime_schema_package_is_importable():
    result = subprocess.run([sys.executable, "-c", "from importlib.resources import files; print(files('epe.data.schemas').joinpath('policy.schema.json').is_file())"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "True"
