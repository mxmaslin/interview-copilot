from __future__ import annotations

import copilot.config as config


def test_interview_fast_silence(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "fast")
    monkeypatch.setenv("AUDIO_PRESET", "interview")
    monkeypatch.delenv("AUDIO_SILENCE_SEC", raising=False)
    monkeypatch.delenv("AUDIO_SILENCE_SEC_SELF", raising=False)
    assert config.silence_seconds(speaker="interviewer") == 0.26
    assert config.silence_seconds(speaker="self") == 0.40
