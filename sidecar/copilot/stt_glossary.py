from __future__ import annotations

import re

from .config import whisper_glossary_fixes
from .stt_glossary_terms import PHRASE_FIXES, WORD_FIXES


def _compile_patterns() -> list[tuple[re.Pattern[str], str]]:
    phrase_sorted = sorted(PHRASE_FIXES, key=lambda x: -len(x[0]))
    word_sorted = sorted(WORD_FIXES, key=lambda x: -len(x[0]))
    out: list[tuple[re.Pattern[str], str]] = []
    for pattern, repl in phrase_sorted:
        out.append((re.compile(pattern, re.IGNORECASE), repl))
    for word, repl in word_sorted:
        out.append((re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE), repl))
    return out


_COMPILED = _compile_patterns()


def apply_glossary_fixes(text: str) -> str:
    """Пост-обработка STT: русская транслитерация терминов → EN."""
    if not text or not whisper_glossary_fixes():
        return text
    out = text
    for pattern, repl in _COMPILED:
        out = pattern.sub(repl, out)
    return out


def normalize_question_text(text: str) -> str:
    """Вопрос для ⌘↩ / LLM — всегда через glossary (voice-agent normalization layer)."""
    return apply_glossary_fixes((text or "").strip())


def glossary_entry_count() -> int:
    """Число правил (слова + фразы) — для тестов и логов."""
    return len(WORD_FIXES) + len(PHRASE_FIXES)
