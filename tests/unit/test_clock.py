from datetime import datetime, timezone

from epe.adapters.clock import SystemClock


def test_system_clock_returns_utc_z_timestamp_and_monotonic_number():
    clock = SystemClock()
    timestamp = clock.now_utc()
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert timestamp.endswith("Z") and parsed.tzinfo == timezone.utc
    before = clock.monotonic()
    after = clock.monotonic()
    assert isinstance(before, float) and after >= before
