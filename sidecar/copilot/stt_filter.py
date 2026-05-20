from __future__ import annotations

import re

from .stt_segment import is_prompt_echo_hallucination, is_whisper_tech_prompt_echo

# Типичные галлюцинации faster-whisper на тишине/шуме (RU YouTube-субтитры).
_HALLUCINATION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"редактор\s+субтитр",
        r"корректор\s+",
        r"субтитр(?:ы|ов)?\s+(?:создал|добавил|сделал)",
        r"продолжение\s+следует",
        r"продолжен\w*\s+в\s+следующ",
        r"расскажите\s+в\s+комментар",
        r"подписывайтесь\s+на\s+канал",
        r"спасибо\s+за\s+внимание",
        r"полицейск\w*\s+музык",
        r"amara\.org",
        r"^\s*(?:музыка|аплодисменты)\s*\.?\s*$",
        r"^\s*да\.?\s*$",
        r"^\s*ага\.?\s*$",
        r"^\s*uh-?huh\.?\s*$",
        r"\bвзрыв\b",
        r"субтитр(?:ы|ов)?\s+субтитр",
        r"смотрите\s+на\s+видео",
        r"^\s*смеш\w*\.?\s*$",
        r"(?:^|\s)смеш\w*(?:\s+смеш\w*){2,}",
    )
)

_LAUGHTER_PREFIX_RE = re.compile(r"^(?:\s*смеш\w*\.?\s*)+", re.IGNORECASE)


def strip_laughter_artifacts(text: str) -> str:
    """Убрать «Смешка» и повторы — типичный мусор Whisper на Brio/тишине."""
    t = (text or "").strip()
    if not t:
        return ""
    t = _LAUGHTER_PREFIX_RE.sub("", t)
    t = re.sub(r"\bсмеш\w*\.?\b", " ", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip(" ,.?…")


def is_stt_hallucination(text: str) -> bool:
    """Отсечь мусор STT, не писать в транскрипт и терминал."""
    t = strip_laughter_artifacts((text or "").strip())
    if not t:
        return True
    if len(t) < 3:
        return True
    words = t.split()
    if words and sum(1 for w in words if re.match(r"смеш\w*", w, re.I)) >= max(
        2, len(words) // 2
    ):
        return True
    if is_prompt_echo_hallucination(t):
        return True
    if is_whisper_tech_prompt_echo(t):
        return True
    for pat in _HALLUCINATION_PATTERNS:
        if pat.search(t):
            return True
    return False
