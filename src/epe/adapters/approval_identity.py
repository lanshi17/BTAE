"""Verify signed approval records against explicitly configured SSH keys."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def approval_payload(record: dict[str, Any]) -> bytes:
    """Canonical UTF-8 JSON bytes signed by the approver; no trailing newline."""
    return json.dumps({k: v for k, v in record.items() if k != "signature"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_approval_identity(record: dict[str, Any], config: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(record, dict):
        return None, "审批记录不是对象"
    identity = record.get("identity")
    if not isinstance(identity, dict) or not isinstance(identity.get("id"), str):
        return None, "审批身份缺失"
    principal = identity["id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}", principal):
        return None, "审批身份格式非法"
    trust = config.get("approval_trust", {})
    identities = trust.get("identities", {}) if isinstance(trust, dict) else {}
    trusted = identities.get(principal) if isinstance(identities, dict) else None
    if not isinstance(trusted, dict):
        return None, "审批身份没有受信公钥配置"
    public_key = trusted.get("public_key")
    if not isinstance(public_key, str) or not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [^\r\n]*)?", public_key):
        return None, "审批公钥格式无效或不受支持"
    if trusted.get("kind") not in ("human", "service") or not isinstance(trusted.get("risk_scope"), list) or any(not isinstance(x, str) or x not in {"low", "medium", "high"} for x in trusted["risk_scope"]):
        return None, "审批身份缺少类型或允许风险配置"
    signature = record.get("signature")
    if not isinstance(signature, str) or not signature.startswith("-----BEGIN SSH SIGNATURE-----\n") or len(signature) > 16384:
        return None, "审批记录缺少 SSH 签名"
    try:
        with tempfile.TemporaryDirectory(prefix="epe-approval-") as directory:
            allowed = Path(directory) / "allowed_signers"
            signed = Path(directory) / "record.sig"
            allowed.write_text(f'{principal} namespaces="epe-approval" {public_key}\n', encoding="utf-8")
            signed.write_text(signature, encoding="ascii")
            result = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", principal,
                                     "-n", "epe-approval", "-s", str(signed)],
                                    input=approval_payload(record), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return None, "SSH 签名验证器不可用或执行失败"
    if result.returncode != 0:
        return None, "审批签名无效"
    return {"trusted": True, "id": principal, "kind": trusted["kind"], "risk_scope": trusted["risk_scope"], "source": "ssh-signature"}, None
