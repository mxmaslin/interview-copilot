from __future__ import annotations

from copilot.stt_segment import (
    is_incomplete_self_utterance,
    is_prompt_echo_hallucination,
    merge_self_continuation,
)


def test_incomplete_trailing_pro() -> None:
    assert is_incomplete_self_utterance("Расскажи, что знаешь про...")
    assert is_incomplete_self_utterance("Расскажи, что знаешь про")
    assert not is_incomplete_self_utterance("Расскажи, что знаешь про Python")


def test_prompt_echo_filtered() -> None:
    assert is_prompt_echo_hallucination("Дословная транскрипция русской разговорной речи")
    assert is_prompt_echo_hallucination("Продолжение в следующей части")


def test_merge_continuation_python() -> None:
    merged = merge_self_continuation(
        "Расскажи, что знаешь про...", "Python"
    )
    assert merged == "Расскажи, что знаешь про Python"


def test_new_question_replaces_pending_tail() -> None:
    merged = merge_self_continuation(
        "Расскажи, что знаешь про...", "Как твоё настроение?"
    )
    assert merged == "Как твоё настроение?"
