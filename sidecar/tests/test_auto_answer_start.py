from __future__ import annotations

from unittest.mock import MagicMock

import copilot.transcript as transcript
from copilot.app import CopilotApp


def _bare_app(monkeypatch) -> CopilotApp:
    monkeypatch.setattr(CopilotApp, "__init__", lambda self, lock: None)
    app = CopilotApp(MagicMock())  # type: ignore[arg-type]
    app.session_active = True
    app._answer_busy = False
    app._auto_answer_speaker = None
    app._screenshot_active = lambda: False
    app._auto_answer_timer_lock = __import__("threading").Lock()
    return app


def test_question_for_auto_uses_interviewer_with_mic_muted(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(transcript, "call_mic_muted_effective", lambda: True)

    transcript.append_line("interviewer", "Что такое GIL?")
    transcript.append_line("self", "угу")

    app = _bare_app(monkeypatch)
    app._auto_answer_speaker = "interviewer"
    assert app._question_for_answer(source="auto") == "Что такое GIL?"
