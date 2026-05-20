from __future__ import annotations

import copilot.config as config


def test_stt_latency_fast_defaults(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "fast")
    monkeypatch.delenv("WHISPER_MODEL_SIZE", raising=False)
    monkeypatch.delenv("AUDIO_SILENCE_SEC", raising=False)
    monkeypatch.delenv("AUDIO_MAX_SEGMENT_SEC", raising=False)
    monkeypatch.delenv("WHISPER_VAD_FILTER", raising=False)
    monkeypatch.delenv("WHISPER_BEAM_SIZE", raising=False)
    monkeypatch.delenv("WHISPER_CONDITION_PREVIOUS", raising=False)
    monkeypatch.delenv("WHISPER_PATIENCE", raising=False)
    assert config.whisper_local_size() == "small"
    assert config.whisper_beam_size() == 3


def test_stt_latency_balanced_defaults(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "balanced")
    monkeypatch.delenv("WHISPER_MODEL_SIZE", raising=False)
    monkeypatch.delenv("WHISPER_BEAM_SIZE", raising=False)
    monkeypatch.delenv("WHISPER_CONDITION_PREVIOUS", raising=False)
    monkeypatch.delenv("WHISPER_PATIENCE", raising=False)
    assert config.whisper_local_size() == "small"
    assert config.silence_seconds() == 0.55
    assert config.max_segment_seconds() == 5.0
    assert config.whisper_vad_filter() is False
    assert config.whisper_beam_size() == 5
    assert config.whisper_condition_on_previous() is True


def test_stt_latency_quality(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "quality")
    monkeypatch.delenv("WHISPER_MODEL_SIZE", raising=False)
    monkeypatch.delenv("WHISPER_VAD_FILTER", raising=False)
    assert config.whisper_local_size() == "large-v3"
    assert config.silence_seconds() == 1.0
    assert config.max_segment_seconds() == 0.0
    assert config.whisper_vad_filter() is True
