from __future__ import annotations

import re

# Хвосты, когда сегмент обрезан до конца фразы (пауза STT раньше последнего слова).
_INCOMPLETE_TAIL_RE = re.compile(
    r"(?:\.\.\.|…)\s*$"
    r"|(?:\s+)(?:про|о|об|в|на|и|что|как|где|когда|или|а|но)\s*\.?\s*$",
    re.IGNORECASE,
)

# Типичный эхо-prompt / субтитры Whisper на тишине.
_PROMPT_ECHO_RE = re.compile(
    r"дословн\w*\s+транскрипц"
    r"|разговорн\w*\s+реч"
    r"|продолжен\w*\s+в\s+следующ"
    r"|расскажите\s+в\s+комментар"
    r"|подписывайтесь\s+на\s+канал",
    re.IGNORECASE,
)


def is_prompt_echo_hallucination(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return bool(_PROMPT_ECHO_RE.search(t))


def is_incomplete_self_utterance(text: str) -> bool:
    """Реплика обрезана — ждём продолжение с микрофона."""
    t = (text or "").strip()
    if not t or is_prompt_echo_hallucination(t):
        return False
    if _INCOMPLETE_TAIL_RE.search(t):
        return True
    if re.search(
        r"(?:знаешь|расскаж\w*|расскаж\w*те)\s+(?:что\s+)?(?:знаешь\s+)?про\s*\.?\s*$",
        t,
        re.I,
    ):
        return True
    return False


def _looks_like_tail_continuation(text: str) -> bool:
    """Короткое продолление обрезанной фразы («Python»), не новый вопрос."""
    t = (text or "").strip()
    if not t or "?" in t:
        return False
    if re.match(r"^(?:как|что|где|когда|почему|зачем|расскаж|объясни|привет)\b", t, re.I):
        return False
    return len(t.split()) <= 3


def merge_self_continuation(previous: str, new: str) -> str:
    """Склеить обрезанный сегмент и продолжение с микрофона."""
    prev = (previous or "").strip()
    nxt = (new or "").strip()
    if not prev:
        return nxt
    if not nxt:
        return prev
    if is_prompt_echo_hallucination(nxt):
        return prev
    if nxt.lower().startswith(prev.lower()[: min(12, len(prev))]):
        return nxt if len(nxt) >= len(prev) else prev
    if is_incomplete_self_utterance(prev) and not _looks_like_tail_continuation(nxt):
        return nxt
    p = prev.rstrip(".… ")
    if p.endswith("..."):
        p = p[:-3].rstrip()
    return f"{p} {nxt}".strip()
