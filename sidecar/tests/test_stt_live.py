from __future__ import annotations

import pytest

from copilot.stt_live import (
    dedupe_repeated_live,
    focus_live_question,
    live_differs_from_file,
    live_question_supersedes_file,
    sanitize_live_transcript,
)


def test_supersedes_short_new_question() -> None:
    old = "Расскажешь, что знаешь про Kafka"
    live = "Что такое партийция в карте"
    assert live_question_supersedes_file(old, live)
    assert live_differs_from_file(old, live)


def test_supersedes_three_words() -> None:
    assert live_question_supersedes_file(
        "Расскажи про Kafka", "Что такое партиция"
    )


def test_same_question_not_supersedes() -> None:
    q = "Расскажи про Kafka"
    assert not live_question_supersedes_file(q, q)
    assert not live_differs_from_file(q, q)


def test_dedupe_repeated_greeting() -> None:
    raw = "Привет как дела? Привет как дела"
    assert dedupe_repeated_live(raw) in (raw, "Привет как дела?")


def test_focus_tail_question_from_rolling() -> None:
    merged = "у меня нормально, что расскажем нового Какая сейчас погода"
    assert focus_live_question(merged) == "Какая сейчас погода"


def test_sanitize_strips_duma_and_fixes_kafka(monkeypatch: pytest.MonkeyPatch) -> None:
    import copilot.config as config

    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_GLOSSARY_FIXES", "1")
    assert sanitize_live_transcript("Дюма!") == ""
    assert sanitize_live_transcript(
        "у меня нормально, что расскажем нового Какая сейчас погода?"
    ) == "Какая сейчас погода?"
    assert "Kafka" in sanitize_live_transcript("Расскажи, что знаешь про кахо")
