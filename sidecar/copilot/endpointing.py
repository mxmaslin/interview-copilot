"""Turn detection / endpointing для copilot (VAD + semantic-lite + debounce).

Соответствует практикам voice agents (LiveKit, NVIDIA, Twilio):
- не финализировать реплику только по тишине, если фраза семантически не завершена;
- не дублировать почти одинаковые финалы подряд (ложный EOU / эхо STT).
"""

from __future__ import annotations

import re
import time
from difflib import SequenceMatcher

from .config import stt_final_debounce_sec, stt_min_words_final_self
from .stt_filter import is_stt_hallucination
from .stt_segment import (
    is_incomplete_self_utterance,
    is_prompt_echo_hallucination,
    is_whisper_tech_prompt_echo,
)

_last_final: dict[str, tuple[str, str, float]] = {}  # speaker -> (norm, raw, mono)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_duplicate_final(speaker: str, text: str) -> bool:
    """Debounce: повтор того же финала в коротком окне (best practice: false EOU)."""
    raw = (text or "").strip()
    if not raw:
        return True
    norm = _normalize(raw)
    prev = _last_final.get(speaker)
    if not prev:
        return False
    prev_norm, prev_raw, ts = prev
    if time.monotonic() - ts > stt_final_debounce_sec():
        return False
    if norm == prev_norm:
        return True
    ratio = SequenceMatcher(None, prev_norm, norm).ratio()
    return ratio >= 0.88 and abs(len(norm) - len(prev_norm)) < 24


def note_final_committed(speaker: str, text: str) -> None:
    raw = (text or "").strip()
    if raw:
        _last_final[speaker] = (_normalize(raw), raw, time.monotonic())


def reset_final_debounce_for_tests() -> None:
    _last_final.clear()


def is_semantically_complete(text: str, *, speaker: str = "self") -> bool:
    """Semantic-lite endpointing: не писать в transcript «обрубок» или мусор."""
    t = (text or "").strip()
    if not t or is_stt_hallucination(t):
        return False
    if is_prompt_echo_hallucination(t) or is_whisper_tech_prompt_echo(t):
        return False

    words = t.split()
    n = len(words)

    if speaker == "self":
        if is_incomplete_self_utterance(t):
            return False
        if "?" in t:
            return n >= 2
        return n >= stt_min_words_final_self()

    if len(t) < 2:
        return False
    if is_whisper_tech_prompt_echo(t):
        return False
    return True
