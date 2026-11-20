from __future__ import annotations

import time
from datetime import datetime, timezone


class SystemClock:
    """System UTC clock for audit timestamps plus a monotonic duration source."""

    def now_utc(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def monotonic(self) -> float:
        return time.monotonic()
