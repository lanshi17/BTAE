from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity | str
    message: str
    entity_id: str | None = None
    path: str | None = None
    line: int | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value if isinstance(self.severity, Severity) else self.severity
        return {k: v for k, v in d.items() if v is not None}

    @property
    def is_error(self) -> bool:
        return (self.severity.value if isinstance(self.severity, Severity) else self.severity) == "error"
