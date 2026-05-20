from __future__ import annotations

import copilot.config as cfg
from copilot.endpointing import (
    is_duplicate_final,
    is_semantically_complete,
    note_final_committed,
    reset_final_debounce_for_tests,
)


def test_semantic_complete_self_question() -> None:
    assert is_semantically_complete("Что такое GIL в Python?", speaker="self")
    assert not is_semantically_complete("Расскажи про", speaker="self")
    assert is_semantically_complete("seg3", speaker="interviewer")


def test_semantic_rejects_prompt_echo() -> None:
    assert not is_semantically_complete(
        "Техническое интервью, русская речь.", speaker="interviewer"
    )


def test_duplicate_final_debounce(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_FINAL_DEBOUNCE_SEC", "10")
    reset_final_debounce_for_tests()
    note_final_committed("self", "Привет, слышишь меня?")
    assert is_duplicate_final("self", "Привет, слышишь меня?")
    assert not is_duplicate_final("self", "Расскажи про Kafka")
