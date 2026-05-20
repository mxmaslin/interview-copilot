from __future__ import annotations

import threading
import time
from unittest.mock import patch

import numpy as np

from copilot import stt_worker


def test_final_job_priority_before_rolling() -> None:
    stt_worker.shutdown_stt_worker()
    order: list[bool] = []
    done = threading.Event()

    def fake_transcribe(pcm: np.ndarray, sr: int, *, live: bool = False) -> str:
        time.sleep(0.05 if live else 0.01)
        return "live" if live else "final"

    with patch.object(stt_worker, "transcribe_pcm16_mono", side_effect=fake_transcribe):
        stt_worker.ensure_stt_worker()
        pcm = np.zeros(1600, dtype=np.int16)
        def on_final(_t: str) -> None:
            order.append(False)
            done.set()

        stt_worker.transcribe_async(pcm, 16000, on_final, live=False)
        stt_worker.transcribe_async(
            pcm, 16000, lambda _t: order.append(True), live=True
        )
        assert done.wait(timeout=2.0)

    stt_worker.shutdown_stt_worker()
    time.sleep(0.05)
    assert order[:1] == [False]
    if len(order) > 1:
        assert order[1] is True
