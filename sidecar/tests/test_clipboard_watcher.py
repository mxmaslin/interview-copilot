from __future__ import annotations

from copilot.clipboard_watcher import ClipboardScreenshotWatcher


def test_can_process_gate_blocks_ack() -> None:
    busy = {"v": True}
    w = ClipboardScreenshotWatcher(
        on_image=lambda: None,
        can_process=lambda: not busy["v"],
    )
    w._last_count = 10
    assert w._can_process() is False
    # Watcher must not advance _last_count while busy (loop uses continue).
    assert w._last_count == 10


def test_can_process_allows_when_idle() -> None:
    w = ClipboardScreenshotWatcher(
        on_image=lambda: None,
        can_process=lambda: True,
    )
    assert w._can_process() is True
