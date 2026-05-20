"""Единый промпт: ответ строго по вопросу."""

from __future__ import annotations

from copilot.interview_prompt import build_system_prompt, build_user_message


def test_system_answers_on_question_not_template() -> None:
    sys_prompt = build_system_prompt(include_resume=False)
    assert "СТРОГО" in sys_prompt or "строго" in sys_prompt.lower()
    assert "контекст" in sys_prompt.lower()
    assert "определение → пример" not in sys_prompt


def test_user_message_includes_dialogue_context() -> None:
    user = build_user_message(
        "Расскажите про проект в Самолёте",
        speaker="interviewer",
        dialogue_context="[Интервьюер]: Как дела?\n[Я]: Хорошо.",
    )
    assert "Самолёте" in user
    assert "Краткий контекст диалога" in user
    assert "Тип вопроса" not in user


def test_self_speaker_label() -> None:
    user = build_user_message("Уточни про OAuth", speaker="self")
    assert "Мой вопрос" in user
