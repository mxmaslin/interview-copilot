from __future__ import annotations

import copilot.config as config


def test_answer_pause_audio_auto_deepseek(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "deepseek")
    monkeypatch.delenv("ANSWER_PAUSE_AUDIO", raising=False)
    assert config.answer_pause_audio() is False


def test_answer_pause_audio_auto_cursor(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "cursor")
    monkeypatch.delenv("ANSWER_PAUSE_AUDIO", raising=False)
    assert config.answer_pause_audio() is True


def test_answer_minimal_context_default_on(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("ANSWER_MINIMAL_CONTEXT", raising=False)
    monkeypatch.delenv("CURSOR_ANSWER_MINIMAL", raising=False)
    assert config.answer_minimal_context() is True
