from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np

from .stt import STTError, transcribe_pcm16_mono

_SttJob = tuple[np.ndarray, int, bool, int, Callable[[str], None]]
_queue: queue.PriorityQueue[tuple[int, int, _SttJob] | None] | None = None
_seq = 0
_seq_lock = threading.Lock()
_final_epoch = 0
_epoch_lock = threading.Lock()
_thread: threading.Thread | None = None
_lock = threading.Lock()


def _next_seq() -> int:
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq


def _worker_loop() -> None:
    assert _queue is not None
    while True:
        item = _queue.get()
        if item is None:
            break
        _prio, _n, job = item
        pcm, sr, live, epoch, on_done = job
        if live:
            with _epoch_lock:
                if epoch < _final_epoch:
                    continue
        try:
            text = transcribe_pcm16_mono(pcm, sr, live=live)
        except STTError:
            continue
        if live:
            with _epoch_lock:
                if epoch < _final_epoch:
                    continue
        if text and len(text) >= 2:
            on_done(text)


def ensure_stt_worker() -> None:
    global _queue, _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _queue = queue.PriorityQueue(maxsize=16)
        _thread = threading.Thread(
            target=_worker_loop, daemon=True, name="stt-worker"
        )
        _thread.start()


def transcribe_async(
    pcm: np.ndarray,
    sample_rate: int,
    on_done: Callable[[str], None],
    *,
    live: bool = False,
) -> bool:
    """Очередь STT: финал (live=False) впереди rolling (live=True).

    Rolling с устаревшим epoch пропускается после постановки финала — иначе
    длинная речь блокирует финальный decode в очереди.
    """
    global _final_epoch
    ensure_stt_worker()
    assert _queue is not None
    with _epoch_lock:
        if not live:
            _final_epoch += 1
        epoch = _final_epoch
    prio = 1 if live else 0
    job: _SttJob = (pcm, sample_rate, live, epoch, on_done)
    try:
        _queue.put_nowait((prio, _next_seq(), job))
        return True
    except queue.Full:
        return False


def reset_stt_epoch_for_tests() -> None:
    global _final_epoch
    with _epoch_lock:
        _final_epoch = 0


def shutdown_stt_worker() -> None:
    global _queue, _thread, _final_epoch
    with _lock:
        q = _queue
        t = _thread
    if q is not None:
        try:
            q.put_nowait(None)
        except queue.Full:
            pass
    if t is not None:
        t.join(timeout=3.0)
    with _lock:
        _queue = None
        _thread = None
    with _epoch_lock:
        _final_epoch = 0
