from __future__ import annotations

from io import StringIO

import copilot.interview_quiet as iq
import copilot.terminal_display as td


def test_log_suppressed_during_interview(monkeypatch) -> None:
    buf = StringIO()
    monkeypatch.setattr(iq.sys, "stderr", buf)
    iq.set_interview_active(True)
    iq.log("[copilot]", "test")
    assert buf.getvalue() == ""
    iq.set_interview_active(False)
    iq.log("[copilot]", "visible")
    assert "visible" in buf.getvalue()


def test_minimal_answer_only(monkeypatch) -> None:
    out = StringIO()
    monkeypatch.setattr(td.sys, "stdout", out)
    monkeypatch.setattr(td, "_use_color", lambda: False)
    iq.set_interview_active(True)
    td.print_interview_answer("Что такое GIL?", "GIL — mutex в CPython.")
    text = out.getvalue()
    assert "COPILOT" not in text
    assert "Что такое GIL?" in text
    assert "mutex" in text
    assert "Вопрос" in text
    assert "Ответ" in text
    iq.set_interview_active(False)
