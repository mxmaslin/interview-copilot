from __future__ import annotations

import threading
import time

from copilot.screenshot_queue import ScreenshotJob, ScreenshotQueue


def test_start_watcher_after_stop_does_not_kill_worker(monkeypatch) -> None:
    """Регрессия: _stop_clipboard_watcher не должен останавливать очередь."""
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

    processed = threading.Event()

    def process(job: ScreenshotJob) -> dict:
        processed.set()
        return {"text": "ok"}

    q = ScreenshotQueue(process=process)
    q.start()
    # Симуляция старого бага: stop очереди при «перезапуске watcher»
    q.stop()
    q.start()
    assert q.enqueue_clipboard()
    assert processed.wait(timeout=2.0)
    q.stop()
