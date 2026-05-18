from __future__ import annotations

import re

from .config import whisper_glossary_fixes

# Частые ошибки Whisper (RU-фонетика) → латиница. Порядок: длинные фразы первыми.
_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\bпостгрес(?:ql)?\b", "PostgreSQL"),
    (r"\bпостгре\b", "PostgreSQL"),
    (r"\bкубернет(?:ес|ис)\b", "Kubernetes"),
    (r"\bдокер\b", "Docker"),
    (r"\bредис\b", "Redis"),
    (r"\bасинкио\b", "asyncio"),
    (r"\bэй\s*пи\s*ай\b", "API"),
    (r"\bрест\b", "REST"),
    (r"\bгит\b", "Git"),
    (r"\bпайтон\b", "Python"),
    (r"\bпайтест\b", "pytest"),
    (r"\bфаст\s*апи\b", "FastAPI"),
    (r"\bджанго\b", "Django"),
    (r"\bсиквел\s*алхимия\b", "SQLAlchemy"),
    (r"\bкубернетис\b", "Kubernetes"),
    (r"\bжил\b", "GIL"),
    (r"\bгил\b", "GIL"),
    (r"\bгила\b", "GIL"),
    (r"\bэйсидай\b", "ACID"),
    (r"\bэй\s*си\s*дай\b", "ACID"),
    (r"\bси\s*и\s*си\s*ди\b", "CI/CD"),
    (r"\bджи\s*ар\s*писи\b", "gRPC"),
    (r"\bкэш\b", "cache"),
    (r"\bкеш\b", "cache"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), repl) for p, repl in _REPLACEMENTS]


def apply_glossary_fixes(text: str) -> str:
    """Пост-обработка STT: русская транслитерация терминов → EN."""
    if not text or not whisper_glossary_fixes():
        return text
    out = text
    for pattern, repl in _COMPILED:
        out = pattern.sub(repl, out)
    return out
