from __future__ import annotations

import copilot.config as config
from copilot.stt import _whisper_transcribe_kwargs
from copilot.transcript import merge_rolling_transcript


def test_merge_rolling_transcript_unrelated_partials_use_final() -> None:
    """Rolling «расскажи про» + финал на другую тему — не склеивать (см. test_merge_rolling)."""
    merged = merge_rolling_transcript(
        ["расскажи про"],
        "Python и Kafka",
    )
    assert merged == "Python и Kafka"


def test_merge_rolling_transcript_combines_related_chunks() -> None:
    merged = merge_rolling_transcript(
        ["расскажи про"],
        "расскажи про Python и Kafka",
    )
    assert merged == "расскажи про Python и Kafka"


def test_merge_rolling_prefers_final_when_superset() -> None:
    merged = merge_rolling_transcript(
        ["что такое Kafka"],
        "что такое Kafka в микросервисах",
    )
    assert merged == "что такое Kafka в микросервисах"


def test_live_whisper_decode_is_fast() -> None:
    kwargs = _whisper_transcribe_kwargs(live=True)
    assert kwargs["beam_size"] == 1
    assert kwargs["condition_on_previous_text"] is False
    assert kwargs["temperature"] == 0.0
    assert "patience" not in kwargs


def test_balanced_rolling_segment_cap(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_LATENCY", "balanced")
    monkeypatch.delenv("AUDIO_MAX_SEGMENT_SEC", raising=False)
    monkeypatch.delenv("AUDIO_ROLLING_SEC", raising=False)
    monkeypatch.setenv("STT_ROLLING", "1")
    assert config.max_segment_seconds() == 2.0


def test_rolling_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("STT_ROLLING", "0")
    monkeypatch.setenv("STT_LATENCY", "balanced")
    monkeypatch.delenv("AUDIO_MAX_SEGMENT_SEC", raising=False)
    assert config.max_segment_seconds() == 5.0
