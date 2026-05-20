from __future__ import annotations

import copilot.config as config


def test_stt_latency_fast_defaults(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "fast")
    monkeypatch.delenv("WHISPER_MODEL_SIZE", raising=False)
    monkeypatch.delenv("AUDIO_SILENCE_SEC", raising=False)
    monkeypatch.delenv("AUDIO_MAX_SEGMENT_SEC", raising=False)
    monkeypatch.delenv("WHISPER_VAD_FILTER", raising=False)
    assert config.whisper_local_size() == "medium"
    assert config.silence_seconds() == 0.42
    assert config.max_segment_seconds() == 3.5
    assert config.whisper_vad_filter() is False
    assert config.whisper_beam_size() == 1


def test_stt_latency_quality(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "quality")
    monkeypatch.delenv("WHISPER_MODEL_SIZE", raising=False)
    monkeypatch.delenv("WHISPER_VAD_FILTER", raising=False)
    assert config.whisper_local_size() == "large-v3"
    assert config.silence_seconds() == 1.0
    assert config.max_segment_seconds() == 0.0
    assert config.whisper_vad_filter() is True
