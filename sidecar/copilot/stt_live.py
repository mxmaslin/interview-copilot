from __future__ import annotations

import re
from difflib import SequenceMatcher

from .stt_filter import is_stt_hallucination, strip_laughter_artifacts
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
        r"техническ\w*[^.?!]{0,120}интервью[^.?!]{0,120}русск\w*\s+реч[^.?!]{0,200}",
        r"\bсмеш\w*\.?\b",
        r"\bдюм\w*!?\b",
    )
)


def dedupe_repeated_live(text: str) -> str:
    """«Привет как дела? Привет как дела» → одна фраза."""
    t = (text or "").strip()
    if len(t) < 12:
        return t
    words = t.split()
    n = len(words)
    if n >= 6 and n % 2 == 0:
        half = n // 2
        a = " ".join(words[:half])
        b = " ".join(words[half:])
        if SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.88:
            return a
    if "?" in t and t.count("?") >= 2:
        parts = [p.strip() for p in re.split(r"\?+", t) if p.strip()]
        if len(parts) >= 2:
            a, b = parts[-2], parts[-1]
            if SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.88:
                return f"{b}?"
    return t


def focus_live_question(text: str) -> str:
    """Из склеенного rolling взять последний осмысленный вопрос (⌘↩ / live)."""
    t = (text or "").strip()
    if not t:
        return t
    had_q = t.endswith("?")
    base = t[:-1].strip() if had_q else t

    clauses = re.split(r"(?<=[а-яё,])\s+(?=[А-ЯЁA-Z])", base)
    if len(clauses) >= 2:
        tail = clauses[-1].strip()
        head = " ".join(clauses[:-1]).strip()
        if head and len(head.split()) >= 4 and len(tail.split()) >= 2:
            return f"{tail}?" if had_q else tail

    if t.count("?") >= 2:
        end = t.rfind("?")
        start = t.rfind("?", 0, end)
        chunk = t[(start + 1 if start >= 0 else 0) : end + 1].strip()
        if len(chunk.split()) >= 2:
            return chunk
    return t


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
    cleaned = strip_laughter_artifacts((text or "").strip())
    if not cleaned:
        return ""
    for pat in _STRIP_FROM_LIVE:
        cleaned = pat.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.…")
    cleaned = dedupe_repeated_live(cleaned)
    cleaned = focus_live_question(cleaned)
    cleaned = apply_glossary_fixes(cleaned)
    if is_stt_hallucination(cleaned):
        return ""
    return cleaned


def live_question_supersedes_file(file_question: str | None, live: str) -> bool:
    """Live rolling важнее последней строки в RAM-диалоге."""
    from difflib import SequenceMatcher

    live = sanitize_live_transcript(live)
    if not live or is_stt_hallucination(live):
        return False
    if not file_question:
        return True
    f = file_question.strip()
    if live == f:
        return False
    if f in live and len(live) > len(f) + 8:
        return True
    if live in f:
        return False
    live_words = len(live.split())
    if "?" in live and live_words >= 2:
        return True
    if live_words >= 2 and SequenceMatcher(None, f.lower(), live.lower()).ratio() < 0.52:
        return True
    if f not in live and live_words >= 2:
        return True
    return False


def live_differs_from_file(file_question: str | None, live: str) -> bool:
    """Есть осмысленный live-текст, отличный от последней строки в файле."""
    live = sanitize_live_transcript(live)
    if not live or is_stt_hallucination(live):
        return False
    if not file_question:
        return True
    return live.strip() != file_question.strip()
