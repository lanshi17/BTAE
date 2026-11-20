import json

from epe.adapters.audit import append_audit, verify_audit


def test_audit_chain_detects_tampering(tmp_path):
    path = tmp_path / "events.jsonl"
    append_audit(path, "one", {"id": 1})
    append_audit(path, "two", {"id": 2})
    assert verify_audit(path) == (True, None, 2)
    rows = path.read_text().splitlines(); row = json.loads(rows[0]); row["payload"]["id"] = 9; rows[0] = json.dumps(row); path.write_text("\n".join(rows) + "\n")
    valid, error, count = verify_audit(path)
    assert not valid and "摘要" in error and count == 0


def test_audit_rejects_extra_fields(tmp_path):
    path = tmp_path / "events.jsonl"
    append_audit(path, "one", {"id": 1})
    row = json.loads(path.read_text().splitlines()[0]); row["extra"] = True
    path.write_text(json.dumps(row) + "\n")
    valid, error, _ = verify_audit(path)
    assert not valid and "字段结构" in error


def _append_many(args):
    path, index = args
    for sequence in range(10):
        append_audit(path, "worker", {"worker": index, "index": sequence})


def test_audit_serializes_multiple_processes(tmp_path):
    from concurrent.futures import ProcessPoolExecutor
    path = tmp_path / "events.jsonl"
    with ProcessPoolExecutor(max_workers=4) as executor:
        list(executor.map(_append_many, [(path, i) for i in range(4)]))
    assert verify_audit(path) == (True, None, 40)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [record["sequence"] for record in records] == list(range(1, 41))
    assert len({(r["payload"]["worker"], r["payload"]["index"]) for r in records}) == 40


def test_audit_refuses_corrupt_or_unterminated_chain(tmp_path):
    import pytest
    path = tmp_path / "events.jsonl"
    append_audit(path, "one", {})
    valid_contents = path.read_bytes()
    for data in (valid_contents[:-1], b'{}\n', b'not-json\n', b'null\n'):
        path.write_bytes(data)
        assert verify_audit(path)[0] is False
        with pytest.raises(ValueError):
            append_audit(path, "two", {})
        assert path.read_bytes() == data


def test_audit_writes_complete_event_when_write_is_short(tmp_path, monkeypatch):
    import epe.adapters.audit as audit
    real_write = audit.os.write
    def short_write(fd, data):
        return real_write(fd, data[:max(1, len(data) // 3)])
    monkeypatch.setattr(audit.os, "write", short_write)
    path = tmp_path / "events.jsonl"
    audit.append_audit(path, "one", {"value": "abc"})
    assert audit.verify_audit(path) == (True, None, 1)


def test_audit_uses_injected_clock(tmp_path):
    class FixedClock:
        def now_utc(self): return "2026-01-02T03:04:05Z"
    event = append_audit(tmp_path / "events.jsonl", "fixed", {}, clock=FixedClock())
    assert event["timestamp"] == "2026-01-02T03:04:05Z"


def test_audit_rejects_invalid_field_types_and_payloads(tmp_path):
    import math
    import pytest
    path = tmp_path / "events.jsonl"
    with pytest.raises(ValueError): append_audit(path, "bad event", {})
    with pytest.raises(ValueError): append_audit(path, "event", {"value": math.nan})
    append_audit(path, "event", {"value": 1})
    rows = path.read_text().splitlines()
    for mutation in (
        lambda row: row.update(sequence=True),
        lambda row: row.update(timestamp="2026-01-02T03:04:05+01:00"),
        lambda row: row.update(event_type=""),
        lambda row: row.update(previous_hash="A" * 64),
        lambda row: row.update(hash="A" * 64),
        lambda row: row.update(payload={"value": float("nan")}),
    ):
        row = json.loads(rows[0]); mutation(row); path.write_text(json.dumps(row) + "\n")
        assert verify_audit(path)[0] is False
        path.write_text("\n".join(rows) + "\n")
