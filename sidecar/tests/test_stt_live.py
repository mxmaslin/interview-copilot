from __future__ import annotations

from copilot.stt_live import (
    is_stt_noise_chunk,
    live_question_supersedes_file,
    sanitize_live_transcript,
)


def test_sanitize_strips_subtitles_and_explosion() -> None:
    raw = (
        "Расскажи, что знаешь про кавка Взрыв Субтитры субтитров А.Синецкая "
        "Смотрите на видео!"
    )
    clean = sanitize_live_transcript(raw)
    assert "kafka" in clean.lower()
    assert "субтитр" not in clean.lower()
    assert "взрыв" not in clean.lower()


def test_live_supersedes_old_file_question() -> None:
    assert live_question_supersedes_file(
        "Привет, слышишь меня?",
        "Расскажи, что знаешь про Kafka",
    )


def test_noise_chunk() -> None:
    assert is_stt_noise_chunk("Взрыв")
    assert not is_stt_noise_chunk("Расскажи про Kafka")
