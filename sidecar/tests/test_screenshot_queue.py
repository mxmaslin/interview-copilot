from __future__ import annotations

import threading
import time

from copilot.screenshot_queue import ScreenshotJob, ScreenshotQueue


def test_queue_processes_jobs_in_order(monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.screenshot_queue.read_clipboard_image",
        lambda: (b"png-a", "image/png"),
    )
    monkeypatch.setattr(
        "copilot.screenshot_queue.pasteboard_change_count", lambda: 1
    )
    monkeypatch.setattr(
        "copilot.screenshot_queue.screenshot_clear_clipboard", lambda: False
    )

    order: list[int] = []
    done = threading.Event()

    def process(job: ScreenshotJob) -> dict:
        order.append(job.job_id)
        time.sleep(0.05)
        if job.job_id == 2:
            done.set()
        return {"text": "ok"}

    q = ScreenshotQueue(process=process)
    q.start()
    assert q.enqueue_clipboard()
    monkeypatch.setattr(
        "copilot.screenshot_queue.read_clipboard_image",
        lambda: (b"png-b", "image/png"),
    )
    assert q.enqueue_clipboard()
    assert done.wait(timeout=2.0)
    q.stop()
    assert order == [1, 2]


def test_enqueue_returns_false_without_image(monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.screenshot_queue.read_clipboard_image", lambda: None
    )
    q = ScreenshotQueue(process=lambda _j: {})
    assert q.enqueue_clipboard() is False
