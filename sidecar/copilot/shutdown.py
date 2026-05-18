from __future__ import annotations

import warnings

from .stt import release_local_model
from .stt_worker import shutdown_stt_worker


def shutdown_resources() -> None:
    """Корректное завершение перед выходом (Whisper, PortAudio, hotkey)."""
    shutdown_stt_worker()
    release_local_model()
    try:
        import sounddevice as sd

        sd.stop()
    except Exception:
        pass


def suppress_resource_tracker_warning() -> None:
    """После shutdown_resources — убрать шумный warning при exit (Py3.11)."""
    warnings.filterwarnings(
        "ignore",
        message=r"resource_tracker: There appear to be .* leaked semaphore",
        category=UserWarning,
        module=r"multiprocessing\.resource_tracker",
    )
