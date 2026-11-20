from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, Sequence


class RepositoryPort(Protocol):
    root: Path
    def read_bytes(self, relative_path: str) -> bytes: ...


class ArtifactStorePort(Protocol):
    def write(self, relative_path: str, data: bytes) -> str: ...


class ProcessPort(Protocol):
    def run(self, argv: Sequence[str], cwd: Path, timeout: float | None = None, cancel_event: Any | None = None, input_data: bytes | None = None) -> Any: ...


class ClockPort(Protocol):
    def now_utc(self) -> str: ...
    def monotonic(self) -> float: ...


class IdentityPort(Protocol):
    def current_identity(self) -> dict[str, Any]: ...
