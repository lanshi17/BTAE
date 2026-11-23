"""Cryptographic verification for host capability handshake claims."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


_PRINCIPAL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}\Z")
_PUBLIC_KEY = re.compile(r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [^\r\n]*)?\Z")


def capability_payload(capabilities: dict[str, Any], nonce: str) -> bytes:
    """Return the canonical bytes a host signs for one challenge."""
    if not isinstance(capabilities, dict) or not isinstance(nonce, str) or not nonce:
        raise ValueError("invalid capability attestation input")
    unsigned = {key: value for key, value in capabilities.items() if key != "attestation"}
    try:
        encoded = json.dumps({"protocol_version": "1", "nonce": nonce, "capabilities": unsigned},
                             ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("能力证明载荷必须是有限 JSON") from exc
    return encoded.encode("utf-8")


def verify_capability_attestation(capabilities: dict[str, Any], nonce: str,
                                  config: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    """Verify a host-provided SSH signature against a configured trust root."""
    if not isinstance(capabilities, dict) or not isinstance(nonce, str) or not nonce:
        return None, "能力证明输入无效"
    attestation = capabilities.get("attestation")
    if not isinstance(attestation, dict):
        return None, "能力证明缺失"
    principal = attestation.get("identity")
    if not isinstance(principal, str) or not _PRINCIPAL.fullmatch(principal):
        return None, "能力证明身份格式非法"
    if attestation.get("nonce") != nonce:
        return None, "能力证明 nonce 不匹配"
    operations = capabilities.get("operations")
    if (not isinstance(operations, list)
            or any(not isinstance(operation, str) or not operation for operation in operations)
            or len(set(operations)) != len(operations)):
        return None, "能力证明操作字段无效"
    signature = attestation.get("signature")
    if (not isinstance(signature, str)
            or not signature.startswith("-----BEGIN SSH SIGNATURE-----\n")
            or len(signature) > 16384):
        return None, "能力证明签名格式无效"
    trust = config.get("host_trust", {}) if isinstance(config, dict) else {}
    identities = trust.get("identities", {}) if isinstance(trust, dict) else {}
    trusted = identities.get(principal) if isinstance(identities, dict) else None
    if not isinstance(trusted, dict):
        return None, "能力证明身份没有受信公钥配置"
    public_key = trusted.get("public_key")
    if not isinstance(public_key, str) or not _PUBLIC_KEY.fullmatch(public_key):
        return None, "能力证明公钥格式无效"
    allowed_operations = trusted.get("operations", [])
    if (not isinstance(allowed_operations, list) or not allowed_operations
            or any(not isinstance(operation, str) or not operation for operation in allowed_operations)):
        return None, "能力证明身份缺少允许操作配置"
    if not set(operations).issubset(set(allowed_operations)):
        return None, "能力证明操作超出受信范围"
    try:
        payload = capability_payload(capabilities, nonce)
    except (TypeError, ValueError):
        return None, "能力证明载荷无效"
    try:
        with tempfile.TemporaryDirectory(prefix="epe-host-attestation-") as directory:
            allowed = Path(directory) / "allowed_signers"
            signed = Path(directory) / "capability.sig"
            allowed.write_text(f'{principal} namespaces="epe-host-capability" {public_key}\n', encoding="utf-8")
            signed.write_text(signature, encoding="ascii")
            result = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", principal,
                 "-n", "epe-host-capability", "-s", str(signed)],
                input=payload, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=10,
            )
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        return None, "能力证明验证器不可用或执行失败"
    if result.returncode != 0:
        return None, "能力证明签名无效"
    return {"trusted": True, "id": principal, "source": "ssh-signature",
            "operations": tuple(sorted(set(allowed_operations)))}, None
