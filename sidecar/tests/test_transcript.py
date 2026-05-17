from __future__ import annotations

import copilot.transcript as transcript


def test_append_line_interviewer(tmp_path, monkeypatch) -> None:
    path = tmp_path / "transcript.md"
    monkeypatch.setattr(transcript, "TRANSCRIPT_PATH", path)
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)

    line = transcript.append_line("interviewer", "Что такое GIL?")

    assert line == "[Интервьюер]: Что такое GIL?"
    assert "[Интервьюер]: Что такое GIL?" in path.read_text(encoding="utf-8")


def test_append_line_self(tmp_path, monkeypatch) -> None:
    path = tmp_path / "transcript.md"
    monkeypatch.setattr(transcript, "TRANSCRIPT_PATH", path)
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)

    line = transcript.append_line("self", "Отвечу про GIL")

    assert line == "[Я]: Отвечу про GIL"


def test_last_interviewer_line(tmp_path, monkeypatch) -> None:
    path = tmp_path / "transcript.md"
    monkeypatch.setattr(transcript, "TRANSCRIPT_PATH", path)
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)

    transcript.append_line("interviewer", "Первый вопрос")
    transcript.append_line("self", "Мой ответ")
    transcript.append_line("interviewer", "Второй вопрос")

    assert transcript.last_interviewer_line() == "Второй вопрос"


def test_last_interviewer_line_empty(tmp_path, monkeypatch) -> None:
    path = tmp_path / "transcript.md"
    monkeypatch.setattr(transcript, "TRANSCRIPT_PATH", path)
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)

    assert transcript.last_interviewer_line() is None
