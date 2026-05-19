from __future__ import annotations

from unittest.mock import MagicMock

import copilot.transcript as transcript
from copilot.app import CopilotApp
from copilot.interview_quiet import interview_active, set_interview_active


def _bare_app(monkeypatch) -> CopilotApp:
    monkeypatch.setattr(CopilotApp, "__init__", lambda self, lock: None)
    app = CopilotApp(MagicMock())  # type: ignore[arg-type]
    app.session_active = False
    app._hotkey_listener = None
    return app


def test_begin_interview_clears_transcript_and_enables_hotkeys(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "transcript.md"
    monkeypatch.setattr(transcript, "TRANSCRIPT_PATH", path)
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)
    set_interview_active(False)

    app = _bare_app(monkeypatch)
    hotkey_calls: list[int] = []
    statuses: list[str] = []

    monkeypatch.setattr(app, "_start_hotkey", lambda: hotkey_calls.append(1))
    monkeypatch.setattr(
        CopilotApp, "_set_status", lambda self, text: statuses.append(text)
    )

    transcript.append_line("interviewer", "старая реплика")
    app._begin_interview(silent=True)

    assert app.session_active is True
    assert interview_active() is True
    assert transcript.dialogue_lines() == []
    assert hotkey_calls == [1]
    assert statuses == ["интервью"]


def test_boot_bindings_starts_interview(monkeypatch) -> None:
    app = _bare_app(monkeypatch)
    begun: list[bool] = []

    monkeypatch.setattr(app, "_begin_interview", lambda *, silent=False: begun.append(silent))
    monkeypatch.setattr(
        "copilot.session_warmup.warmup_session", lambda: None
    )
    monkeypatch.setattr(app, "_start_clipboard_watcher", lambda: None)
    monkeypatch.setattr(app, "_start_telegram_input", lambda: "")
    monkeypatch.setattr(
        "copilot.app.screenshot_solve_enabled", lambda: False
    )
    monkeypatch.setattr(
        "copilot.config.cursor_agent_fresh_each_run", lambda: False
    )
    monkeypatch.setattr(
        "copilot.cursor_ide_chat.sync_env_chat_binding", lambda: None
    )

    timer = MagicMock()
    app._boot_bindings(timer)

    timer.stop.assert_called_once()
    assert begun == [True]


def test_menu_excludes_advanced_items() -> None:
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "copilot" / "app.py"
    block = src.read_text(encoding="utf-8").split("self.menu = [", 1)[1].split(
        "]", 1
    )[0]
    removed = (
        "Привязать chatId Agents",
        "Сбросить привязку chatId",
        "Добавить реплику интервьюера",
        "Добавить мою реплику",
        "Отменить SDK запрос",
        "Открыть Cursor-агента",
    )
    for label in removed:
        assert label not in block
    assert "Начать прослушивание (интервьюер + я)" in block
    assert "Выход" in block


def test_end_interview_session_stops_hotkeys(tmp_path, monkeypatch) -> None:
    app = _bare_app(monkeypatch)
    stopped: list[int] = []

    app.session_active = True
    app._listening_active = True
    app._answer_busy = False
    app._sdk_pause_depth = 0
    set_interview_active(True)
    monkeypatch.setattr(app, "_stop_hotkey", lambda: stopped.append(1))
    monkeypatch.setattr(app, "_stop_all_audio", lambda: None)
    monkeypatch.setattr(
        "copilot.app.cancel_active_sdk", lambda: False
    )
    monkeypatch.setattr(app, "_screenshot_active", lambda: False)

    app._end_interview_session()

    assert app.session_active is False
    assert interview_active() is False
    assert app._listening_active is False
    assert stopped == [1]
