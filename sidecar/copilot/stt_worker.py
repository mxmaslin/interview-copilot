from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np

from .stt import STTError, transcribe_pcm16_mono

_queue: queue.Queue[tuple[np.ndarray, int, Callable[[str], None]] | None] | None = None
_thread: threading.Thread | None = None
_lock = threading.Lock()


def _worker_loop() -> None:
    assert _queue is not None
    while True:
        item = _queue.get()
        if item is None:
            break
        pcm, sr, on_done = item
        try:
            text = transcribe_pcm16_mono(pcm, sr)
        except STTError:
            continue
        if text and len(text) >= 2:
            on_done(text)


def ensure_stt_worker() -> None:
    global _queue, _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _queue = queue.Queue(maxsize=8)
        _thread = threading.Thread(
            target=_worker_loop, daemon=True, name="stt-worker"
        )
        _thread.start()


def transcribe_async(
    pcm: np.ndarray,
    sample_rate: int,
    on_done: Callable[[str], None],
) -> bool:
    """Поставить сегмент в очередь STT. False если очередь переполнена."""
    ensure_stt_worker()
    assert _queue is not None
    try:
        _queue.put_nowait((pcm, sample_rate, on_done))
        return True
    except queue.Full:
        return False


def shutdown_stt_worker() -> None:
    global _queue, _thread
    with _lock:
        q = _queue
        t = _thread
        _queue = None
        _thread = None
    if q is not None:
        try:
            q.put_nowait(None)
        except queue.Full:
            pass
    if t is not None:
        t.join(timeout=3.0)
