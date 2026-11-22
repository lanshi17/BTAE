import json
import sys

from epe.cli import main


def test_host_capabilities_cli_is_machine_readable(capsys):
    assert main(["--format", "json", "host", "capabilities"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["protocol_version"] == "1"
    hermes = next(item for item in result["data"]["hosts"] if item["host_id"] == "hermes")
    assert hermes["status"] == "unsupported-unintegrated"


def test_host_request_local_verify_is_structured_and_writes_nothing(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "--format", "json", "host", "request",
                 "--host", "local-cli", "--operation", "verify", "--request-id", "REQ-1",
                 "--task-id", "TASK-1", "--target-entity", "CLASS-1",
                 "--identity-source", "local-process"])
    result = json.loads(capsys.readouterr().out)
    assert code == 0 and result["status"] == "passed"
    assert result["data"]["decision"] == "accepted"
    assert list(tmp_path.iterdir()) == []


def test_host_request_rejects_write_operation_on_local_host(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "--format", "json", "host", "request",
                 "--host", "local-cli", "--operation", "start_implementation", "--request-id", "REQ-2",
                 "--task-id", "TASK-1", "--target-entity", "CLASS-1", "--write-scope", "src/**",
                 "--identity-source", "local-process"])
    result = json.loads(capsys.readouterr().out)
    assert code == 4 and result["status"] == "unsupported"
    assert result["data"]["decision"] == "unsupported"


def test_host_request_rejects_non_object_parameters(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "--format", "json", "host", "request",
                 "--host", "local-cli", "--operation", "verify", "--request-id", "REQ-3",
                 "--task-id", "TASK-1", "--target-entity", "CLASS-1", "--identity-source", "local-process",
                 "--parameters", "[]"])
    result = json.loads(capsys.readouterr().out)
    assert code == 3 and result["status"] == "error"
    assert result["diagnostics"][0]["code"] == "EPE-HOST-PARAMETERS"


def test_host_request_unconfigured_hermes_is_explicitly_unsupported(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "--format", "json", "host", "request",
                 "--host", "hermes", "--operation", "verify", "--request-id", "REQ-4",
                 "--task-id", "TASK-1", "--target-entity", "CLASS-1", "--identity-source", "host"])
    result = json.loads(capsys.readouterr().out)
    assert code == 4 and result["status"] == "unsupported"
    assert result["data"]["decision"] == "unsupported"


def test_host_request_hermes_uses_explicit_argv_bridge(tmp_path, capsys):
    code_text = ("import json,sys; p=json.load(sys.stdin); "
                 "print(json.dumps({'status':'ok','capabilities':{'protocol_version':'1','operations':['verify']}} "
                 "if p['operation']=='capabilities' else {'status':'ok','response':{'decision':'accepted','reasons':['fixture']}}))")
    code = main(["--root", str(tmp_path), "--format", "json", "host", "request",
                 "--host", "hermes", "--operation", "verify", "--request-id", "REQ-5",
                 "--task-id", "TASK-1", "--target-entity", "CLASS-1", "--identity-source", "fixture",
                 "--command-json", json.dumps([sys.executable, "-c", code_text])])
    result = json.loads(capsys.readouterr().out)
    assert code == 0 and result["status"] == "passed"
    assert result["data"]["decision"] == "accepted"


def test_host_request_rejects_malformed_command_json(tmp_path, capsys):
    code = main(["--root", str(tmp_path), "--format", "json", "host", "request",
                 "--host", "hermes", "--operation", "verify", "--request-id", "REQ-6",
                 "--task-id", "TASK-1", "--target-entity", "CLASS-1", "--identity-source", "fixture",
                 "--command-json", "{not-json}"])
    result = json.loads(capsys.readouterr().out)
    assert code == 3 and result["diagnostics"][0]["code"] == "EPE-HOST-COMMAND"


def test_host_capabilities_can_measure_explicit_hermes_bridge(tmp_path, capsys):
    code_text = "import json; print(json.dumps({'status':'ok','capabilities':{'protocol_version':'1','operations':['verify']}}))"
    code = main(["--root", str(tmp_path), "--format", "json", "host", "capabilities", "--host", "hermes",
                 "--command-json", json.dumps([sys.executable, "-c", code_text])])
    result = json.loads(capsys.readouterr().out)
    assert code == 0 and result["status"] == "passed"
    assert result["data"]["hosts"][0]["status"] == "handshaken-untrusted"
