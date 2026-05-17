from __future__ import annotations

from io import StringIO

import copilot.terminal_display as td


def test_stream_chunks(monkeypatch) -> None:
    buf = StringIO()
    monkeypatch.setattr(td.sys, "stdout", buf)
    monkeypatch.setattr(td, "_use_color", lambda: False)
    monkeypatch.setattr(td, "interview_active", lambda: True)

    stream = td.InterviewAnswerStream("Что GIL?", provider="deepseek")
    stream.begin()
    stream.write_chunk("GIL — ")
    stream.write_chunk("mutex.")
    stream.end()

    out = buf.getvalue()
    assert "Вопрос" in out
    assert "Ответ" in out
    assert "GIL — mutex." in out
