from __future__ import annotations

import re

# Типичные галлюцинации faster-whisper на тишине/шуме (RU YouTube-субтитры).
_HALLUCINATION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"редактор\s+субтитр",
        r"корректор\s+",
        r"субтитр(?:ы|ов)?\s+(?:создал|добавил|сделал)",
        r"продолжение\s+следует",
        r"спасибо\s+за\s+внимание",
        r"полицейск\w*\s+музык",
        r"amara\.org",
        r"^\s*(?:музыка|аплодисменты)\s*\.?\s*$",
        r"^\s*да\.?\s*$",
        r"^\s*ага\.?\s*$",
        r"^\s*uh-?huh\.?\s*$",
    )
)


def is_stt_hallucination(text: str) -> bool:
    """Отсечь мусор STT, не писать в транскрипт и терминал."""
    t = (text or "").strip()
    if not t:
        return True
    if len(t) < 3:
        return True
    for pat in _HALLUCINATION_PATTERNS:
        if pat.search(t):
            return True
    return False
