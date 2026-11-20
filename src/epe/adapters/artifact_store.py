from __future__ import annotations

import errno
import hashlib
import os
import secrets
import shutil
from pathlib import Path, PurePosixPath


class ArtifactStore:
    """POSIX repository-local store for immutable, atomically published artifacts."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

    @staticmethod
    def _parts(relative_path: str) -> tuple[str, ...]:
        if (not isinstance(relative_path, str) or not relative_path or "\\" in relative_path):
            raise ValueError("artifact path must be a normalized repository-relative path")
        path = PurePosixPath(relative_path)
        if path.is_absolute() or ".." in path.parts or "." in path.parts or path.as_posix() != relative_path:
            raise ValueError("artifact path must be a normalized repository-relative path")
        parts = path.parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("artifact path must not contain empty or traversal components")
        return parts

    def _open_parent(self, components: tuple[str, ...]) -> int:
        directory_flag = getattr(os, "O_DIRECTORY", 0)
        nofollow_flag = getattr(os, "O_NOFOLLOW", 0)
        if os.name != "posix" or not directory_flag or not nofollow_flag or os.open not in os.supports_dir_fd or os.mkdir not in os.supports_dir_fd or os.link not in os.supports_dir_fd or os.unlink not in os.supports_dir_fd:
            raise NotImplementedError("ArtifactStore requires POSIX dir_fd, O_DIRECTORY, and O_NOFOLLOW support")
        fd = os.open(self.root, os.O_RDONLY | directory_flag | nofollow_flag)
        try:
            for component in components:
                try:
                    child_fd = os.open(component, os.O_RDONLY | directory_flag | nofollow_flag, dir_fd=fd)
                except FileNotFoundError:
                    try:
                        os.mkdir(component, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                    try:
                        child_fd = os.open(component, os.O_RDONLY | directory_flag | nofollow_flag, dir_fd=fd)
                    except OSError as exc:
                        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                            raise ValueError(f"artifact parent must be a real directory, not a symlink: {component}") from exc
                        raise
                except OSError as exc:
                    if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                        raise ValueError(f"artifact parent must be a real directory, not a symlink: {component}") from exc
                    raise
                os.close(fd)
                fd = child_fd
            return fd
        except BaseException:
            os.close(fd)
            raise

    def ensure_directory(self, relative_path: str) -> None:
        """Create a repository-relative directory tree without following links."""
        components = self._parts(relative_path)
        fd = self._open_parent(components)
        os.close(fd)

    def write(self, relative_path: str, data: bytes) -> str:
        if not isinstance(data, bytes):
            raise TypeError("artifact data must be bytes")
        parts = self._parts(relative_path)
        parent_fd = self._open_parent(parts[:-1])
        temporary = f".epe-tmp-{secrets.token_hex(16)}"
        temp_created = False
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(temporary, flags, 0o600, dir_fd=parent_fd)
            temp_created = True
            try:
                view = memoryview(data)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError("artifact write made no progress")
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            # Hard-link publication is atomic and fails if the destination exists.
            os.link(temporary, parts[-1], src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
            os.unlink(temporary, dir_fd=parent_fd)
            temp_created = False
            os.fsync(parent_fd)
            return hashlib.sha256(data).hexdigest()
        finally:
            if temp_created:
                try:
                    os.unlink(temporary, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)

    def publish_bundle(self, relative_directory: str, files: dict[str, bytes]) -> dict[str, str]:
        """Publish a fresh directory of immutable files in one rename operation.

        Files are first written below a private sibling staging directory.  A
        failed write removes that staging directory and never exposes a partial
        run directory.  The final directory must not already exist.
        """
        directory = self._parts(relative_directory)
        if not isinstance(files, dict) or not files:
            raise ValueError("artifact bundle must contain files")
        names: list[str] = []
        for name, data in files.items():
            if not isinstance(name, str) or not name or "/" in name or "\\" in name or name in {".", ".."}:
                raise ValueError("bundle file names must be simple relative names")
            self._parts(f"{relative_directory}/{name}")
            if not isinstance(data, bytes):
                raise TypeError("artifact data must be bytes")
            names.append(name)
        parent_fd = self._open_parent(directory[:-1])
        final_name = directory[-1]
        staging_name = f".epe-bundle-{secrets.token_hex(16)}"
        staging_relative = "/".join((*directory[:-1], staging_name))
        try:
            os.mkdir(staging_name, 0o700, dir_fd=parent_fd)
            published = False
            try:
                digests: dict[str, str] = {}
                for name in names:
                    digests[name] = self.write(f"{staging_relative}/{name}", files[name])
                staging_fd = os.open(staging_name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
                try:
                    os.fsync(staging_fd)
                finally:
                    os.close(staging_fd)
                try:
                    os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise FileExistsError(final_name)
                os.rename(staging_name, final_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                published = True
                os.fsync(parent_fd)
                return digests
            finally:
                if not published:
                    shutil.rmtree(self.root / staging_relative, ignore_errors=True)
        finally:
            os.close(parent_fd)
