from __future__ import annotations

import copilot.config as config


def test_screenshot_solve_enabled_default_on(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("SCREENSHOT_SOLVE_ENABLED", raising=False)
    assert config.screenshot_solve_enabled() is True


def test_screenshot_answer_provider_uses_cursor_when_answer_cursor(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "cursor")
    monkeypatch.delenv("SCREENSHOT_ANSWER_PROVIDER", raising=False)
    assert config.screenshot_answer_provider() == "cursor"


def test_screenshot_deepseek_uses_cursor_when_key(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "deepseek")
    monkeypatch.delenv("SCREENSHOT_ANSWER_PROVIDER", raising=False)
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    assert config.screenshot_answer_provider() == "cursor"


def test_screenshot_clear_clipboard_default_on(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("SCREENSHOT_CLEAR_CLIPBOARD", raising=False)
    assert config.screenshot_clear_clipboard() is True


def test_screenshot_vision_model_override(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("SCREENSHOT_VISION_MODEL", "gpt-4o")
    assert config.screenshot_vision_model("openai") == "gpt-4o"


def test_screenshot_debounce_legacy_env(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("SCREENSHOT_DEBOUNCE_SEC", raising=False)
    monkeypatch.setenv("SCREENSHOT_SOLVE_DEBOUNCE_SEC", "0.5")
    assert config.screenshot_debounce_sec() == 0.5
