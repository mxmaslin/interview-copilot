from __future__ import annotations

from copilot.stt_filter import is_stt_hallucination


def test_subtitle_editor_hallucination() -> None:
    assert is_stt_hallucination("Редактор субтитров И.Бойкова Корректор А.Егорова")


def test_prompt_echo_hallucination() -> None:
    assert is_stt_hallucination("Дословная транскрипция русской разговорной речи")
    assert is_stt_hallucination("Продолжение в следующей части")


def test_real_speech_passes() -> None:
    assert not is_stt_hallucination("Что такое GIL в Python?")
