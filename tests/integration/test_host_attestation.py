import json
import shutil
import subprocess

import pytest

from epe.adapters.host_attestation import capability_payload, verify_capability_attestation


pytestmark = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen unavailable")


def signed_capabilities(tmp_path, key, nonce="nonce-1", operations=None):
    capabilities = {
        "protocol_version": "1", "trusted_identity": True, "write_isolation": True,
        "process_group_control": True, "cancellation": True,
        "operations": operations if operations is not None else ["verify"],
    }
    payload = tmp_path / "capability-payload"
    payload.write_bytes(capability_payload(capabilities, nonce))
    subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-n", "epe-host-capability",
                    "-f", str(key), str(payload)], check=True, capture_output=True)
    capabilities["attestation"] = {
        "identity": "runner", "nonce": nonce,
        "signature": payload.with_name(payload.name + ".sig").read_text(),
    }
    return capabilities


def config_for(key):
    return {"host_trust": {"identities": {"runner": {
        "public_key": key.with_suffix(".pub").read_text().strip(), "operations": ["verify"]}}}}


def test_valid_attestation_is_bound_to_nonce_and_capabilities(tmp_path):
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    capabilities = signed_capabilities(tmp_path, key)
    fact, error = verify_capability_attestation(capabilities, "nonce-1", config_for(key))
    assert error is None and fact == {"trusted": True, "id": "runner", "source": "ssh-signature", "operations": ("verify",)}


@pytest.mark.parametrize("change", ["nonce", "field", "signature"])
def test_attestation_tampering_fails_closed(tmp_path, change):
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    capabilities = signed_capabilities(tmp_path, key)
    if change == "nonce":
        capabilities["attestation"]["nonce"] = "other"
    elif change == "field":
        capabilities["write_isolation"] = False
    else:
        capabilities["attestation"]["signature"] = capabilities["attestation"]["signature"].replace("A", "B", 1)
    fact, error = verify_capability_attestation(capabilities, "nonce-1", config_for(key))
    assert fact is None and error


def test_missing_trust_root_and_operation_scope_are_rejected(tmp_path):
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    capabilities = signed_capabilities(tmp_path, key)
    assert verify_capability_attestation(capabilities, "nonce-1", {})[0] is None
    config = config_for(key)
    config["host_trust"]["identities"]["runner"]["operations"] = []
    assert verify_capability_attestation(capabilities, "nonce-1", config)[0] is None


def test_attestation_cannot_escalate_operations_beyond_trust_root(tmp_path):
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    capabilities = signed_capabilities(tmp_path, key, operations=["verify", "start_implementation"])
    fact, error = verify_capability_attestation(capabilities, "nonce-1", config_for(key))
    assert fact is None and error == "能力证明操作超出受信范围"


def test_attestation_rejects_non_finite_capability_payload_without_raising(tmp_path):
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
    capabilities = signed_capabilities(tmp_path, key)
    capabilities["nonfinite"] = float("nan")
    fact, error = verify_capability_attestation(capabilities, "nonce-1", config_for(key))
    assert fact is None and error == "能力证明载荷无效"
