from __future__ import annotations

import copilot.config as config


def test_deepseek_defaults(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    assert config.deepseek_answer_model() == "deepseek-chat"
    assert config.deepseek_api_base() == "https://api.deepseek.com"


def test_answer_provider_deepseek(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "deepseek")
    assert config.answer_provider() == "deepseek"


def test_cursor_agent_mirror_defaults(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("CURSOR_AGENT_MIRROR", raising=False)
    monkeypatch.delenv("CURSOR_AGENT_AUTO_START", raising=False)
    assert config.cursor_agent_mirror() is False
    assert config.cursor_agent_auto_start() is False
    assert config.cursor_open_answer_file() is False
