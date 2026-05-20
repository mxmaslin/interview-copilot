"""Промпты для ⌘↩: строго по вопросу и контексту беседы."""

from __future__ import annotations

from .config import REPO_ROOT

_RESUME_PATH = REPO_ROOT / "context" / "resume.md"
_RESUME_MAX_CHARS = 6000

_ANSWER_SYSTEM = (
    "Ты помогаешь кандидату на собеседовании (HR, менеджер, техлид, live coding — любой формат). "
    "Отвечай СТРОГО на последний заданный вопрос: не подменяй его другой темой и не уходи в смежные лекции. "
    "Опирайся на «Краткий контекст диалога», если он есть — это ход беседы, а не повод сменить тему. "
    "Про опыт, проекты, компании — только факты из блока «Резюме»; не выдумывай. "
    "Если спросили про технологию — ответь по сути; если про карьеру — про карьеру. "
    "5–10 предложений, русский язык, EN-термины где уместно, формулировки для озвучивания вслух."
)


def load_resume_excerpt(*, max_chars: int = _RESUME_MAX_CHARS) -> str:
    if not _RESUME_PATH.is_file():
        return ""
    raw = _RESUME_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return ""
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 20].rstrip() + "\n\n[…обрезано]"


def build_system_prompt(*, include_resume: bool = True) -> str:
    base = _ANSWER_SYSTEM
    if include_resume:
        resume = load_resume_excerpt()
        if resume:
            base += f"\n\n## Резюме (только эти факты)\n\n{resume}"
    return base


def build_user_message(
    question: str,
    *,
    speaker: str,
    dialogue_context: str = "",
) -> str:
    if speaker == "self":
        header = (
            "Мой вопрос (соло на созвоне, звук интервьюера отключён "
            "или микрофон на созвоне выключен):\n"
            f"{question.strip()}"
        )
    else:
        header = f"Вопрос интервьюера:\n{question.strip()}"

    user = (
        f"{header}\n\n"
        "Дай ответ, который кандидат может сказать вслух. "
        "Только по этому вопросу, с учётом контекста ниже."
    )
    if dialogue_context.strip():
        user += f"\n\nКраткий контекст диалога:\n{dialogue_context.strip()}"
    return user
