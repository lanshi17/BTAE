from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalIdentityAdapter:
    """Conservative local identity fact; it deliberately cannot authorize approvals."""

    subject: str | None = None

    def current_identity(self) -> dict[str, Any]:
        return {
            "trusted": False,
            "id": self.subject,
            "kind": "unknown",
            "source": "local-process",
            "risk_scope": [],
            "reason": "本地 CLI 没有受信身份通道",
        }
