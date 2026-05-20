from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np

from .audio_devices import resolve_input_device
from .audio_macos import open_input_stream_locked, probe_input_stream
from .config import (
    audio_block_ms,
    audio_rms_threshold,
    max_segment_seconds,
    min_speech_seconds,
    silence_seconds,
    stt_rolling_enabled,
)
from .interview_quiet import log
from .pipeline_timing import note_speech_end
from .stt import STTError, transcribe_pcm16_mono
from .stt_filter import is_stt_hallucination
from .stt_worker import transcribe_async
from .transcript import append_line

logger = logging.getLogger(__name__)


class AudioListener:
    """Запись с одного входа, сегментация по паузе, STT → transcript."""

    def __init__(
        self,
        on_transcript: Callable[[str], None] | None = None,
        *,
        on_speech_start: Callable[[], None] | None = None,
        on_utterance_end: Callable[[], None] | None = None,
        speaker: str = "interviewer",
        device_hint: str = "",
        label: str = "",
    ) -> None:
        self._speaker = speaker
        self._device_hint = device_hint
        self._label = label or speaker
        self._on_transcript = on_transcript or self._default_on_transcript
        self._on_speech_start = on_speech_start
        self._on_utterance_end = on_utterance_end
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream = None
        self._device_name = ""
        self._sample_rate = 48000
        self._capture_lock = threading.Lock()
        self._buf: list[np.ndarray] = []
        self._silent_blocks = 0
        self._speech_blocks = 0
        self._in_utterance = False
        self._block_sec = 0.05

    def _default_on_transcript(self, text: str) -> None:
        append_line(self._speaker, text)

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> str:
        if self.running:
            return self._device_name
        self._stop.clear()
        idx, name, sr = resolve_input_device(self._device_hint or None)
        self._device_name = name
        self._sample_rate = sr
        probe_input_stream(idx, sr)
        self._thread = threading.Thread(
            target=self._run,
            args=(idx, sr),
            daemon=True,
            name=f"audio-{self._label or self._speaker}",
        )
        self._thread.start()
        return name

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def drain_speech_buffer_for_final(self) -> tuple[np.ndarray, int] | None:
        """⌘↩: срез текущей речи без ожидания паузы (синхронный STT в app)."""
        with self._capture_lock:
            if not self._buf:
                return None
            speech_sec = self._speech_blocks * self._block_sec
            if speech_sec < min_speech_seconds():
                return None
            pcm = np.concatenate(self._buf)
            sr = self._sample_rate
            self._buf.clear()
            self._silent_blocks = 0
            self._speech_blocks = 0
            self._in_utterance = False
            return pcm, sr

    def _run(self, device_index: int | None, sr: int) -> None:
        import sounddevice as sd

        block = max(1, int(sr * audio_block_ms() / 1000.0))
        self._block_sec = block / sr
        silence_limit = silence_seconds(speaker=self._speaker)
        min_speech = min_speech_seconds()
        max_seg = max_segment_seconds(speaker=self._speaker)
        rms_threshold = audio_rms_threshold(self._speaker)

        def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
            if self._stop.is_set():
                return
            mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            pcm = (mono * 32767).astype(np.int16)
            rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
            with self._capture_lock:
                if rms >= rms_threshold:
                    if not self._in_utterance and self._on_speech_start is not None:
                        self._in_utterance = True
                        try:
                            self._on_speech_start()
                        except Exception:
                            logger.exception("on_speech_start failed")
                    self._buf.append(pcm.copy())
                    self._speech_blocks += 1
                    self._silent_blocks = 0
                    if max_seg > 0 and self._speech_blocks * self._block_sec >= max_seg:
                        self._flush_locked(
                            sr,
                            rolling=stt_rolling_enabled(),
                        )
                elif self._buf:
                    self._silent_blocks += 1
                    if self._silent_blocks * self._block_sec >= silence_limit:
                        self._flush_locked(sr, rolling=False)

        try:

            def _open() -> sd.InputStream:
                stream = sd.InputStream(
                    device=device_index,
                    channels=1,
                    samplerate=sr,
                    blocksize=block,
                    dtype="float32",
                    callback=callback,
                )
                stream.start()
                return stream

            self._stream = open_input_stream_locked(_open)
            try:
                while not self._stop.is_set():
                    sd.sleep(50)
            finally:
                if self._stream is not None:
                    try:
                        self._stream.stop()
                        self._stream.close()
                    except Exception:
                        pass
                    self._stream = None
            with self._capture_lock:
                if self._buf:
                    self._flush_locked(sr, rolling=False)
        except Exception as e:
            logger.exception("Audio listener failed")
            msg = str(e)
            if "err='-50'" in msg or "-50" in msg:
                msg += (
                    "\n\nЧастая причина на macOS: неверная частота дискретизации или устройство. "
                    "Проверь AUDIO_INPUT_DEVICE в .env и docs/audio-setup.md (BlackHole)."
                )
            raise RuntimeError(msg) from e

    def _flush_locked(self, sr: int, *, rolling: bool) -> None:
        speech_sec = self._speech_blocks * self._block_sec
        chunks = list(self._buf)
        self._buf.clear()
        self._silent_blocks = 0
        self._speech_blocks = 0
        self._in_utterance = False
        self._enqueue_flush(chunks, speech_sec, sr, rolling=rolling)

    def _enqueue_flush(
        self,
        chunks: list[np.ndarray],
        speech_sec: float,
        sr: int,
        *,
        rolling: bool,
    ) -> None:
        if speech_sec < min_speech_seconds() or not chunks:
            return
        if not rolling:
            note_speech_end(self._speaker)
            if self._on_utterance_end is not None:
                try:
                    self._on_utterance_end()
                except Exception:
                    logger.exception("on_utterance_end failed")
        pcm = np.concatenate(chunks)
        on_done = self._on_transcript

        def deliver(text: str) -> None:
            if is_stt_hallucination(text):
                logger.debug("STT dropped (%s), len=%d", self._speaker, len(text))
                return
            try:
                on_done(text, final=not rolling)
            except TypeError:
                on_done(text)
            except Exception:
                logger.exception("on_transcript failed")

        if not transcribe_async(pcm, sr, deliver, live=rolling):
            if rolling:
                return
            log("[copilot] STT очередь переполнена, сегмент пропущен")
            try:
                text = transcribe_pcm16_mono(pcm, sr, live=False)
                if text:
                    deliver(text)
            except STTError as e:
                logger.warning("STT failed: %s", e)
