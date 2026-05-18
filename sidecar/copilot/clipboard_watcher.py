from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .clipboard_image import image_fingerprint, pasteboard_change_count, read_clipboard_image
from .config import screenshot_debounce_sec, screenshot_poll_sec
from .interview_quiet import log

_active_watcher: "ClipboardScreenshotWatcher | None" = None


def register_clipboard_watcher(watcher: ClipboardScreenshotWatcher | None) -> None:
    global _active_watcher
    _active_watcher = watcher


def notify_clipboard_cleared() -> None:
    if _active_watcher is not None:
        _active_watcher.note_pasteboard_cleared()


class ClipboardScreenshotWatcher:
    """Следит за changeCount pasteboard; при новом изображении вызывает on_image."""

    def __init__(self, on_image: Callable[[], None]) -> None:
        self._on_image = on_image
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_count = 0
        self._last_fingerprint = ""

    def start(self) -> None:
        self.stop()
        self._stop.clear()
        self._last_count = pasteboard_change_count()
        self._thread = threading.Thread(
            target=self._loop, name="clipboard-watcher", daemon=True
        )
        self._thread.start()
        register_clipboard_watcher(self)
        log("[copilot] screenshot watcher: ⌘⌃⇧4 → буфер → vision API")

    def stop(self) -> None:
        register_clipboard_watcher(None)
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def _loop(self) -> None:
        poll = screenshot_poll_sec()
        debounce = screenshot_debounce_sec()
        while not self._stop.wait(poll):
            try:
                count = pasteboard_change_count()
            except Exception:
                continue
            if count == self._last_count:
                continue
            self._last_count = count
            if debounce > 0:
                if self._stop.wait(debounce):
                    break
            try:
                item = read_clipboard_image()
            except Exception as e:
                log("[copilot] clipboard read:", e)
                continue
            if item is None:
                continue
            data, _mime = item
            fp = image_fingerprint(data)
            if fp == self._last_fingerprint:
                continue
            self._last_fingerprint = fp
            try:
                self._on_image()
            except Exception:
                import traceback

                traceback.print_exc()

    def note_pasteboard_cleared(self) -> None:
        """После clearContents — не реагировать повторно на тот же скриншот."""
        try:
            self._last_count = pasteboard_change_count()
        except Exception:
            pass
        self._last_fingerprint = ""
