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


_TECH_PROMPT_ECHO_RE = re.compile(
    r"техническ\w*[^.?!]{0,80}интервью[^.?!]{0,80}русск\w*\s+реч"
    r"|техническ\w*[^.?!]{0,40}библиотек"
    r"|библиотек\w*[^.?!]{0,40}протокол",
    re.IGNORECASE,
)


def is_whisper_tech_prompt_echo(text: str) -> bool:
    """Эхо initial_prompt (режим tech/general) на тишине — Whisper повторяет подсказку."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) < 10:
        return False
    low = t.lower()
    if _TECH_PROMPT_ECHO_RE.search(low):
        return True
    if low.count("русская речь") >= 2:
        return True
    if low.count("техническ") >= 3 and "интервью" in low:
        return True
    markers = (
        "техническ" in low,
        "интервью" in low,
        "русск" in low,
        "библиотек" in low,
        "протокол" in low,
        "латиниц" in low,
    )
    if sum(markers) >= 3 and len(t) < 220:
        return True
    if re.search(r"техническ\w*", low) and "интервью" in low and re.search(r"русск", low):
        if len(t) < 160:
            rest = low
            for pat in (
                r"техническ\w*,?\s*",
                r"интервью,?\s*",
                r"русская\s+речь\.?\s*",
                r"технические\s+интервью,?\s*",
                r"библиотек\w*,?\s*",
                r"протокол\w*,?\s*",
                r"бд,?\s*",
                r"очеред\w*,?\s*",
                r"инфраструктур\w*,?\s*",
                r"латиниц\w*[^.?!]*",
            ):
                rest = re.sub(pat, " ", rest)
            rest = re.sub(r"\s+", " ", rest).strip(" ,.?…")
            if len(rest) < 16:
                return True
    if "библиотек" in low and "латиниц" in low and len(t) < 130:
        return True
    if "русская разговорная речь" in low and len(t) < 100:
        return True
    return False


def is_incomplete_self_utterance(text: str) -> bool:
    """Реплика обрезана — ждём продолжение с микрофона."""
    t = (text or "").strip()
    if not t or is_prompt_echo_hallucination(t) or is_whisper_tech_prompt_echo(t):
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
    if is_prompt_echo_hallucination(nxt) or is_whisper_tech_prompt_echo(nxt):
        return prev
    if nxt.lower().startswith(prev.lower()[: min(12, len(prev))]):
        return nxt if len(nxt) >= len(prev) else prev
    if is_incomplete_self_utterance(prev) and not _looks_like_tail_continuation(nxt):
        return nxt
    p = prev.rstrip(".… ")
    if p.endswith("..."):
        p = p[:-3].rstrip()
    return f"{p} {nxt}".strip()
