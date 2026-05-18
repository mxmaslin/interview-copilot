"""Очередь скриншотов: захват из буфера сразу, обработка по одному."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from .clipboard_image import (
    clear_clipboard,
    pasteboard_change_count,
    read_clipboard_image,
)
from .config import screenshot_clear_clipboard
from .clipboard_watcher import notify_clipboard_cleared
from .interview_quiet import log

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class ScreenshotJob:
    job_id: int
    png_bytes: bytes
    mime: str


class ScreenshotQueue:
    def __init__(
        self,
        process: Callable[[ScreenshotJob], dict[str, Any]],
        *,
        on_busy_change: Callable[[bool], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        self._process = process
        self._on_busy_change = on_busy_change
        self._on_status = on_status
        self._q: queue.Queue[ScreenshotJob | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._next_id = 0
        self._lock = threading.Lock()
        self._processing = False

    @property
    def processing(self) -> bool:
        return self._processing

    def pending_count(self) -> int:
        return self._q.qsize()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._worker, name="screenshot-queue", daemon=True
        )
        self._thread.start()
        log("[copilot] очередь скриншотов: worker запущен")

    def stop(self) -> None:
        if self._thread is None:
            return
        self._q.put(None)
        self._thread.join(timeout=3.0)
        self._thread = None

    def enqueue_clipboard(self) -> bool:
        """Сразу читает PNG из буфера и ставит в очередь (можно снимать следующий кадр)."""
        item = read_clipboard_image()
        if item is None:
            return False
        data, mime = item
        if not data:
            return False
        paste_at_capture = pasteboard_change_count()
        with self._lock:
            self._next_id += 1
            job_id = self._next_id
        job = ScreenshotJob(job_id=job_id, png_bytes=data, mime=mime)
        self._q.put(job)
        pending = self.pending_count()
        if pending > 1:
            log(f"[copilot] скриншот #{job_id} в очереди (ожидают: {pending - 1})")
        else:
            log(f"[copilot] скриншот #{job_id} принят")
        self._clear_clipboard_after_capture(paste_at_capture)
        return True

    def _clear_clipboard_after_capture(self, paste_count_at_capture: int) -> None:
        if not screenshot_clear_clipboard():
            return
        try:
            if pasteboard_change_count() != paste_count_at_capture:
                log(
                    "[copilot] буфер не очищаем — changeCount изменился при захвате"
                )
                return
            if clear_clipboard():
                notify_clipboard_cleared()
                log("[copilot] буфер очищен (кадр сохранён в очереди)")
        except Exception as e:
            log("[copilot] WARN: не удалось очистить буфер:", e)

    def _worker(self) -> None:
        while True:
            job = self._q.get()
            try:
                if job is None:
                    break
                self._run_job(job)
            finally:
                self._q.task_done()

    def _run_job(self, job: ScreenshotJob) -> None:
        self._processing = True
        if self._on_busy_change:
            self._on_busy_change(True)
        if self._on_status:
            self._on_status(f"скриншот #{job.job_id}…")
        rest = self.pending_count()
        if rest:
            log(f"[copilot] скриншот #{job.job_id}: обработка ({rest} в очереди)")
        else:
            log(f"[copilot] скриншот #{job.job_id}: обработка")
        try:
            self._process(job)
        except Exception as e:
            log(f"[copilot] скриншот #{job.job_id} ERROR:", e)
            if interview_active_import():
                import sys

                sys.stdout.write(f"\n[copilot] скриншот #{job.job_id}: {e}\n\n")
                sys.stdout.flush()
        finally:
            self._processing = False
            still_busy = self.pending_count() > 0
            if self._on_busy_change:
                self._on_busy_change(still_busy)
            if self._on_status and not still_busy:
                self._on_status("интервью")


def interview_active_import() -> bool:
    from .interview_quiet import interview_active

    return interview_active()
