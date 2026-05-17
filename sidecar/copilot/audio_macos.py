"""macOS PortAudio helpers (dual-input stability)."""

from __future__ import annotations

import threading
import time

# CoreAudio / AUHAL often logs err=-50 when two InputStreams open at once.
_stream_open_lock = threading.Lock()


def open_input_stream_locked(open_stream, *, stagger_sec: float = 0.0):
    """
    Serialize InputStream construction across channels.
    `open_stream` is a zero-arg callable returning the started stream.
    """
    if stagger_sec > 0:
        time.sleep(stagger_sec)
    with _stream_open_lock:
        stream = open_stream()
        time.sleep(0.15)
        return stream


def probe_input_stream(device_index: int | None, sample_rate: int) -> None:
    """Open/close once on the caller thread — surfaces -50 as Python error."""
    import sounddevice as sd

    block = max(1, int(sample_rate * 0.05))
    with _stream_open_lock:
        with sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=sample_rate,
            blocksize=block,
            dtype="float32",
        ):
            sd.sleep(80)
