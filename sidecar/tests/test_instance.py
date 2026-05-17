from __future__ import annotations

import os
from multiprocessing import Process
from pathlib import Path

from copilot.instance import SidecarLock


def test_lock_single_holder(tmp_path) -> None:
    lock_path = tmp_path / "sidecar.lock"
    lock = SidecarLock(lock_path)

    assert lock.acquire() is True
    assert SidecarLock.holder_pid(lock_path) == os.getpid()
    lock.release()
    assert not lock_path.exists()


def test_lock_blocks_second_holder(tmp_path) -> None:
    lock_path = tmp_path / "sidecar.lock"
    first = SidecarLock(lock_path)
    second = SidecarLock(lock_path)

    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()


def _child_acquire(lock_path_str: str, result_path_str: str) -> None:
    lock = SidecarLock(Path(lock_path_str))
    ok = lock.acquire()
    Path(result_path_str).write_text("1" if ok else "0", encoding="utf-8")
    if ok:
        lock.release()


def test_lock_released_after_process_exit(tmp_path) -> None:
    lock_path = tmp_path / "sidecar.lock"
    result_path = tmp_path / "child.ok"

    holder = SidecarLock(lock_path)
    assert holder.acquire() is True

    child = Process(
        target=_child_acquire,
        args=(str(lock_path), str(result_path)),
    )
    child.start()
    child.join(timeout=5)
    assert child.exitcode == 0
    assert result_path.read_text(encoding="utf-8") == "0"

    holder.release()

    child2 = Process(
        target=_child_acquire,
        args=(str(lock_path), str(result_path)),
    )
    child2.start()
    child2.join(timeout=5)
    assert child2.exitcode == 0
    assert result_path.read_text(encoding="utf-8") == "1"
