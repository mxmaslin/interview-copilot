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


def test_kick_pending_force_ignores_last_count(monkeypatch) -> None:
    started: list[bool] = []

    def fake_read():
        return (b"\x89PNG\r\n\x1a\nx", "image/png")

    monkeypatch.setattr(
        "copilot.clipboard_watcher.read_clipboard_image", fake_read
    )
    monkeypatch.setattr(
        "copilot.clipboard_watcher.pasteboard_change_count", lambda: 42
    )
    monkeypatch.setattr(
        "copilot.clipboard_watcher.image_fingerprint", lambda _d: "fp2"
    )

    w = ClipboardScreenshotWatcher(
        on_image=lambda: started.append(True),
        can_process=lambda: True,
    )
    w._last_count = 42
    w._last_fingerprint = "fp1"

    w.kick_pending(force=True)
    assert started
