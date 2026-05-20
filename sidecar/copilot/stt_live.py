from __future__ import annotations

import re

from .stt_filter import is_stt_hallucination
from .stt_glossary import apply_glossary_fixes

# Короткие куски Whisper на шуме/тишине (не целая реплика).
_NOISE_CHUNK_RE = re.compile(
    r"^(?:"
    r"взрыв\.?"
    r"|субтитр"
    r"|смотрите\s+на\s+видео"
    r"|алло\b"
    r"|хорошо,?\s+я\s+дома"
    r"|где\??"
    r"|ванная"
    r")\s*\.?\s*$",
    re.IGNORECASE,
)

_STRIP_FROM_LIVE: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"Субтитры[^\n.?]{0,120}",
        r"Смотрите\s+на\s+видео[!?.]*",
        r"\bВзрыв\b\.?",
        r"Техническ\w*,?\s*интервью,?\s*русская\s+речь\.?",
        r"Технические\s+интервью,?\s*русская\s+речь\.?",
        r"Библиотеки,?\s+протоколы[^\n.?]{0,200}",
    )
)


def is_stt_noise_chunk(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if is_stt_hallucination(t):
        return True
    if _NOISE_CHUNK_RE.match(t):
        return True
    if len(t) <= 8 and "субтитр" in t.lower():
        return True
    return False


def sanitize_live_transcript(text: str) -> str:
    """Убрать типичный мусор из накопленной live-строки (терминал)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    for pat in _STRIP_FROM_LIVE:
        cleaned = pat.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.?…")
    cleaned = apply_glossary_fixes(cleaned)
    if is_stt_hallucination(cleaned):
        return ""
    return cleaned


def live_question_supersedes_file(file_question: str | None, live: str) -> bool:
    """Live rolling важнее последней строки в transcript.md."""
    live = sanitize_live_transcript(live)
    if not live or is_stt_hallucination(live):
        return False
    if not file_question:
        return True
    f = file_question.strip()
    if live == f:
        return False
    if f in live and len(live) > len(f) + 12:
        return True
    if f not in live and len(live.split()) >= 4:
        return True
    return False
