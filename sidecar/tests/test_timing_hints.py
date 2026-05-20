from __future__ import annotations

import copilot.config as config
from copilot.timing_hints import suggest_tuning_hints


def test_hint_slow_stt(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("COPILOT_STT_SLOW_MS", "500")
    hints = suggest_tuning_hints({"stt_ms": 900, "llm_ttft_ms": 400})
    assert any("STT" in h for h in hints)


def test_hint_slow_llm(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("COPILOT_LLM_SLOW_MS", "1000")
    hints = suggest_tuning_hints({"stt_ms": 100, "llm_ttft_ms": 2000})
    assert any("LLM" in h for h in hints)


def test_hint_hotkey_no_stt(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    hints = suggest_tuning_hints(
        {"source": "hotkey", "stt_ms": None, "llm_ttft_ms": 800}
    )
    assert any("live" in h.lower() for h in hints)
