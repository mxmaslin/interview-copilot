from __future__ import annotations

from copilot.clipboard_watcher import ClipboardScreenshotWatcher


def test_watcher_starts_with_current_change_count(monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.clipboard_watcher.pasteboard_change_count", lambda: 7
    )
    w = ClipboardScreenshotWatcher(on_image=lambda: None)
    w.start()
    assert w._last_count == 7
    w.stop()


def test_note_pasteboard_cleared_syncs_count(monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.clipboard_watcher.pasteboard_change_count", lambda: 99
    )
    w = ClipboardScreenshotWatcher(on_image=lambda: None)
    w._last_count = 1
    w.note_pasteboard_cleared()
    assert w._last_count == 99
