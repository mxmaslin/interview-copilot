from __future__ import annotations

import copilot.config as config


def test_answer_auto_enabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("ANSWER_AUTO", raising=False)
    assert config.answer_auto_enabled() is True


def test_answer_auto_delay(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_AUTO_DELAY_SEC", "0")
    assert config.answer_auto_delay_sec() == 0.0
