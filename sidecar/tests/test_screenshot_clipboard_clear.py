from __future__ import annotations

import copilot.screenshot_solve as ss


def test_skip_clear_when_pasteboard_changed(monkeypatch) -> None:
    counts = {"n": 10}

    monkeypatch.setattr(ss, "screenshot_clear_clipboard", lambda: True)
    monkeypatch.setattr(ss, "pasteboard_change_count", lambda: counts["n"])
    monkeypatch.setattr(ss, "notify_clipboard_cleared", lambda: None)

    cleared: list[bool] = []

    def do_clear() -> bool:
        cleared.append(True)
        return True

    monkeypatch.setattr(ss, "clear_clipboard", do_clear)
    assert ss._maybe_clear_clipboard_after_screenshot(10) is True
    assert cleared

    counts["n"] = 11
    cleared.clear()
    assert ss._maybe_clear_clipboard_after_screenshot(10) is False
    assert not cleared
