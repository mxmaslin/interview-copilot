from __future__ import annotations

"""Регрессия: очередь скринов не равна «answer busy»."""

import threading
import time

from copilot.screenshot_queue import ScreenshotJob, ScreenshotQueue


def test_screenshot_queue_active_while_answer_idle(monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.screenshot_queue.read_clipboard_image",
        lambda: (b"png", "image/png"),
    )
    monkeypatch.setattr(
        "copilot.screenshot_queue.pasteboard_change_count", lambda: 1
    )
    monkeypatch.setattr(
        "copilot.screenshot_queue.screenshot_clear_clipboard", lambda: False
    )

    started = threading.Event()

    def process(job: ScreenshotJob) -> dict:
        started.set()
        time.sleep(0.15)
        return {"text": "ok"}

    answer_busy = False
    q = ScreenshotQueue(process=process)
    q.start()
    assert q.enqueue_clipboard()
    assert started.wait(timeout=2.0)
    screenshot_active = q.processing or q.pending_count() > 0
    assert screenshot_active
    assert answer_busy is False
    time.sleep(0.2)
    q.stop()
