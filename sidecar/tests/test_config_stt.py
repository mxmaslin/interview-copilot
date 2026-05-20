from __future__ import annotations

import copilot.config as config


def test_whisper_beam_balanced_preset(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "balanced")
    monkeypatch.setenv("STT_FAST_FINAL", "0")
    monkeypatch.delenv("WHISPER_BEAM_SIZE", raising=False)
    assert config.whisper_beam_size() == 3


def test_whisper_prompt_mode_general(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_PROMPT_MODE", "general")
    assert config.whisper_prompt_mode() == "general"


def test_terminal_show_self_default_on(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("TERMINAL_SHOW_SELF", raising=False)
    assert config.terminal_show_self_stt() is True
