from __future__ import annotations

from io import StringIO

import copilot.terminal_display as td


def test_wrap_long_line(monkeypatch) -> None:
    monkeypatch.setattr(td, "_term_width", lambda: 60)
    lines = td._wrap_block("word " * 40)
    assert len(lines) >= 2


def test_print_writes_box(monkeypatch) -> None:
    buf = StringIO()
    monkeypatch.setattr(td.sys, "stdout", buf)
    monkeypatch.setattr(td, "_use_color", lambda: False)
    td.print_interview_answer("Что такое GIL?", "GIL — mutex в CPython.")
    out = buf.getvalue()
    assert "COPILOT" in out
    assert "Вопрос" in out
    assert "GIL" in out
    assert "mutex" in out


def test_interviewer_transcript(monkeypatch) -> None:
    buf = StringIO()
    monkeypatch.setattr(td.sys, "stdout", buf)
    monkeypatch.setattr(td, "_use_color", lambda: False)
    td.print_interviewer_transcript("Что такое asyncio?")
    out = buf.getvalue()
    assert "Интервьюер" in out
    assert "asyncio" in out
