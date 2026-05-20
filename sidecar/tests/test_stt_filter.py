from __future__ import annotations

from copilot.stt_filter import is_stt_hallucination


def test_subtitle_editor_hallucination() -> None:
    assert is_stt_hallucination("Редактор субтитров И.Бойкова Корректор А.Егорова")


def test_prompt_echo_hallucination() -> None:
    assert is_stt_hallucination("Дословная транскрипция русской разговорной речи")
    assert is_stt_hallucination("Продолжение в следующей части")


def test_tech_prompt_echo_hallucination() -> None:
    assert is_stt_hallucination(
        "Техническое интервью, русская речь. Технический интервью, русская речь."
    )
    assert is_stt_hallucination(
        "Технические интервью, русская речь. Библиотеки, протоколы, биджет."
    )


def test_smeshka_stripped_and_filtered() -> None:
    from copilot.stt_filter import strip_laughter_artifacts

    assert strip_laughter_artifacts("Смешка Привет") == "Привет"
    assert is_stt_hallucination("Смешка")
    assert is_stt_hallucination("Смешка Смешка Смешка")
    assert not is_stt_hallucination("Смешка Привет")


def test_real_speech_passes() -> None:
    assert not is_stt_hallucination("Что такое GIL в Python?")
