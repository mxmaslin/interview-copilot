"""Общие фикстуры pytest для sidecar."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _config_isolated_from_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Не подмешивать локальный .env в unit-тесты config."""
    import copilot.config as config

    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    for key in (
        "AUDIO_SILENCE_SEC",
        "AUDIO_SILENCE_SEC_SELF",
        "AUDIO_PRESET",
        "STT_LATENCY",
        "STT_FAST_FINAL",
        "STT_ROLLING",
        "AUDIO_ROLLING_SEC",
        "STT_PENDING_FLUSH_SEC",
        "STT_LIVE_MIN_WORDS",
        "AUDIO_BLOCK_MS",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _no_pending_stt_timer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Таймер обрезка [Я] в transcript-тестах не нужен — 0 отключает flush."""
    monkeypatch.setenv("STT_PENDING_FLUSH_SEC", "0")


@pytest.fixture(autouse=True)
def _ram_transcript_isolated() -> None:
    """Диалог в RAM — чистый старт каждого теста."""
    import copilot.transcript as transcript

    transcript.clear_dialogue()
    yield
    transcript.clear_dialogue()
