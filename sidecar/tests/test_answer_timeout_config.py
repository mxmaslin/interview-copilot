from __future__ import annotations

import copilot.config as config


def test_answer_request_timeout_default(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("ANSWER_REQUEST_TIMEOUT", raising=False)
    assert config.answer_request_timeout() == 120.0


def test_answer_request_timeout_override(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_REQUEST_TIMEOUT", "90")
    assert config.answer_request_timeout() == 90.0
