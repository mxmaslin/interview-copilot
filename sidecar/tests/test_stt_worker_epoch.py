from __future__ import annotations

import time

import pytest

pytest.importorskip("numpy")
from copilot import stt_worker


@pytest.fixture(autouse=True)
def _reset_worker() -> None:
    stt_worker.shutdown_stt_worker()
    stt_worker.reset_stt_epoch_for_tests()
    yield
    stt_worker.shutdown_stt_worker()
    stt_worker.reset_stt_epoch_for_tests()


def test_stale_rolling_skipped_after_final(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[bool, str]] = []

    def fake_transcribe(pcm, sample_rate: int, *, live: bool = False) -> str:
        calls.append((live, "x"))
        time.sleep(0.05 if live else 0.01)
        return "rolling" if live else "final"

    monkeypatch.setattr(stt_worker, "transcribe_pcm16_mono", fake_transcribe)
    import numpy as np

    pcm = np.zeros(1600, dtype=np.int16)
    done_rolling: list[str] = []
    done_final: list[str] = []

    assert stt_worker.transcribe_async(
        pcm, 16000, done_rolling.append, live=True
    )
    assert stt_worker.transcribe_async(
        pcm, 16000, done_final.append, live=False
    )
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if done_final:
            break
        time.sleep(0.02)
    assert done_final == ["final"]
    assert done_rolling == []
