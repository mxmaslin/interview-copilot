from __future__ import annotations

import io
import logging
import tempfile
import threading
import wave
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .config import (
    openai_api_key,
    stt_provider,
    whisper_api_model,
    whisper_compute_type,
    whisper_device,
    whisper_local_size,
)

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_local_model: WhisperModel | None = None
_local_model_lock = threading.Lock()

INTERVIEW_PROMPT = (
    "Техническое интервью, Python backend, PostgreSQL, Redis, "
    "asyncio, Docker, англоязычные IT-термины."
)


class STTError(RuntimeError):
    pass


def transcribe_pcm16_mono(pcm: np.ndarray, sample_rate: int) -> str:
    """pcm: int16 mono numpy array."""
    if pcm.size == 0:
        return ""
    provider = stt_provider()
    if provider == "local":
        return _transcribe_local(pcm, sample_rate)
    if provider == "openai":
        return _transcribe_openai(pcm, sample_rate)
    raise STTError(f"Неизвестный STT_PROVIDER={provider!r}. Используй local или openai.")


def warmup_local_model() -> None:
    """Предзагрузка модели в фоне (первый запуск может занять минуту)."""
    if stt_provider() != "local":
        return

    def _load() -> None:
        try:
            _get_local_model()
            logger.info("Local Whisper model ready (%s)", whisper_local_size())
        except Exception as e:
            logger.warning("Whisper warmup failed: %s", e)

    threading.Thread(target=_load, daemon=True, name="whisper-warmup").start()


def _get_local_model() -> WhisperModel:
    global _local_model
    with _local_model_lock:
        if _local_model is not None:
            return _local_model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise STTError(
                "Установи локальный Whisper: pip install -e '.[audio]'"
            ) from e

        size = whisper_local_size()
        logger.info(
            "Loading faster-whisper %s (device=%s, compute=%s)…",
            size,
            whisper_device(),
            whisper_compute_type(),
        )
        _local_model = WhisperModel(
            size,
            device=whisper_device(),
            compute_type=whisper_compute_type(),
            num_workers=1,
        )
        return _local_model


def _pcm_to_float32(pcm: np.ndarray) -> np.ndarray:
    return pcm.astype(np.float32) / 32768.0


def _transcribe_local(pcm: np.ndarray, sample_rate: int) -> str:
    model = _get_local_model()
    audio = _pcm_to_float32(pcm)
    if sample_rate != 16000:
        audio = _resample_to_16k(audio, sample_rate)

    segments, _ = model.transcribe(
        audio,
        language="ru",
        task="transcribe",
        initial_prompt=INTERVIEW_PROMPT,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    return " ".join(parts).strip()


def _resample_to_16k(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    if sample_rate == 16000:
        return audio
    duration = len(audio) / sample_rate
    n = max(1, int(duration * 16000))
    x_old = np.linspace(0.0, 1.0, num=len(audio), dtype=np.float64)
    x_new = np.linspace(0.0, 1.0, num=n, dtype=np.float64)
    return np.interp(x_new, x_old, audio.astype(np.float64)).astype(np.float32)


def _pcm_to_wav_bytes(pcm: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.astype(np.int16).tobytes())
    return buf.getvalue()


def _transcribe_openai(pcm: np.ndarray, sample_rate: int) -> str:
    key = openai_api_key()
    if not key:
        raise STTError("OPENAI_API_KEY не задан (STT_PROVIDER=openai).")

    try:
        from openai import OpenAI
    except ImportError as e:
        raise STTError("Установи: pip install -e '.[openai]'") from e

    wav_bytes = _pcm_to_wav_bytes(pcm, sample_rate)
    client = OpenAI(api_key=key)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)
        path.write_bytes(wav_bytes)

    try:
        with path.open("rb") as audio_file:
            resp = client.audio.transcriptions.create(
                model=whisper_api_model(),
                file=audio_file,
                language="ru",
                prompt=INTERVIEW_PROMPT,
            )
        return (resp.text or "").strip()
    finally:
        path.unlink(missing_ok=True)
