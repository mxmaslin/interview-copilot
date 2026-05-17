from __future__ import annotations

import atexit
import fcntl
import os
from pathlib import Path

from .config import DATA_DIR

LOCK_PATH = DATA_DIR / "sidecar.lock"


class SidecarLock:
    """Один sidecar на машину (flock на data/sidecar.lock)."""

    def __init__(self, path: Path = LOCK_PATH) -> None:
        self.path = path
        self._fd: int | None = None

    @staticmethod
    def holder_pid(path: Path = LOCK_PATH) -> int | None:
        if not path.exists():
            return None
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return False
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        self._fd = fd
        atexit.register(self.release)
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        fd = self._fd
        self._fd = None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass
