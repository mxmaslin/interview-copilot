from __future__ import annotations

import copilot.config as config


def test_balanced_whisper_decode_tuned_for_terms(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "balanced")
    monkeypatch.delenv("WHISPER_BEAM_SIZE", raising=False)
    monkeypatch.delenv("WHISPER_CONDITION_PREVIOUS", raising=False)
    monkeypatch.delenv("WHISPER_PATIENCE", raising=False)
    monkeypatch.delenv("WHISPER_TEMPERATURE", raising=False)

    assert config.whisper_beam_size() == 5
    assert config.whisper_condition_on_previous() is True
    assert config.whisper_patience() == 1.0
    assert config.whisper_temperature() == (0.0, 0.2)
    assert config.whisper_prompt_mode() == "tech"
