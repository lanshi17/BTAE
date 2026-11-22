from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib

import pytest

from epe.adapters.artifact_store import ArtifactStore


def test_artifact_store_writes_digest_and_refuses_overwrite(tmp_path):
    store = ArtifactStore(tmp_path)
    relative = "engineering/evidence/RUN-1/output.log"
    digest = store.write(relative, b"safe output")
    assert digest == hashlib.sha256(b"safe output").hexdigest()
    assert (tmp_path / relative).read_bytes() == b"safe output"
    with pytest.raises(FileExistsError):
        store.write(relative, b"replacement")
    assert (tmp_path / relative).read_bytes() == b"safe output"


def test_artifact_store_rejects_escape_and_symlink_parent(tmp_path):
    store = ArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.write("../outside", b"x")
    with pytest.raises(ValueError):
        store.write("/outside", b"x")
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        store.write("escape/secret", b"x")
    assert not (outside / "secret").exists()


def test_artifact_store_concurrent_writers_publish_exactly_one_complete_file(tmp_path):
    store = ArtifactStore(tmp_path)
    payloads = [bytes([index]) * (128 * 1024) for index in range(8)]
    def write(payload):
        try:
            return ("ok", store.write("runs/RUN-1/output.bin", payload))
        except FileExistsError:
            return ("exists", None)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(write, payloads))
    assert sum(status == "ok" for status, _ in results) == 1
    value = (tmp_path / "runs/RUN-1/output.bin").read_bytes()
    assert value in payloads
    assert hashlib.sha256(value).hexdigest() == next(digest for status, digest in results if status == "ok")


def test_artifact_store_refuses_symlink_at_destination(tmp_path):
    store = ArtifactStore(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-target"
    outside.write_bytes(b"original")
    (tmp_path / "linked").symlink_to(outside)
    with pytest.raises(FileExistsError):
        store.write("linked", b"overwrite")
    assert outside.read_bytes() == b"original"


def test_artifact_store_publishes_bundle_atomically_and_refuses_existing_directory(tmp_path):
    store = ArtifactStore(tmp_path)
    files = {"output.log": b"log", "evidence.json": b"{}"}
    digests = store.publish_bundle("engineering/evidence/RUN-BUNDLE", files)
    assert set(digests) == set(files)
    assert all((tmp_path / "engineering/evidence/RUN-BUNDLE" / name).read_bytes() == data for name, data in files.items())
    with pytest.raises(FileExistsError):
        store.publish_bundle("engineering/evidence/RUN-BUNDLE", {"output.log": b"changed"})
    assert not list((tmp_path / "engineering/evidence").glob(".epe-bundle-*"))


def test_artifact_store_bundle_failure_leaves_no_final_directory(tmp_path, monkeypatch):
    store = ArtifactStore(tmp_path)
    original = store.write
    calls = {"count": 0}
    def fail_once(path, data):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected")
        return original(path, data)
    monkeypatch.setattr(store, "write", fail_once)
    with pytest.raises(OSError):
        store.publish_bundle("runs/RUN-FAIL", {"a": b"a", "b": b"b"})
    assert not (tmp_path / "runs/RUN-FAIL").exists()
    assert not list((tmp_path / "runs").glob(".epe-bundle-*"))


def test_bundle_does_not_replace_directory_created_at_commit(tmp_path, monkeypatch):
    import os
    import epe.adapters.artifact_store as module
    real_publish = module._rename_directory_noreplace
    created_inode = []

    def concurrent_create(parent_fd, source, destination):
        os.mkdir(destination, dir_fd=parent_fd)
        created_inode.append(os.stat(destination, dir_fd=parent_fd).st_ino)
        real_publish(parent_fd, source, destination)

    monkeypatch.setattr(module, "_rename_directory_noreplace", concurrent_create)
    with pytest.raises(FileExistsError):
        ArtifactStore(tmp_path).publish_bundle("runs/RUN-RACE", {"evidence.json": b"{}"})
    final = tmp_path / "runs/RUN-RACE"
    assert final.stat().st_ino == created_inode[0]
    assert list(final.iterdir()) == []
    assert not list((tmp_path / "runs").glob(".epe-bundle-*"))


def test_bundle_concurrent_writers_publish_one_complete_bundle(tmp_path):
    store = ArtifactStore(tmp_path)
    def publish(index):
        try:
            store.publish_bundle("runs/RUN-SHARED", {"a": str(index).encode(), "b": str(index).encode()})
            return "ok"
        except FileExistsError:
            return "exists"
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(publish, range(8)))
    assert results.count("ok") == 1
    final = tmp_path / "runs/RUN-SHARED"
    assert (final / "a").read_bytes() == (final / "b").read_bytes()
    assert not list((tmp_path / "runs").glob(".epe-bundle-*"))


def test_bundle_fails_closed_if_atomic_rename_is_unavailable(tmp_path, monkeypatch):
    import epe.adapters.artifact_store as module

    monkeypatch.setattr(module.ctypes, "CDLL", lambda *args, **kwargs: object())
    with pytest.raises(NotImplementedError):
        ArtifactStore(tmp_path).publish_bundle("runs/RUN-UNSUPPORTED", {"evidence.json": b"{}"})
    assert not (tmp_path / "runs/RUN-UNSUPPORTED").exists()
    assert not list((tmp_path / "runs").glob(".epe-bundle-*"))
