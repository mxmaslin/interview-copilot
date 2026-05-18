from __future__ import annotations

import copilot.cursor_model_resolve as cmr


def test_screenshot_cursor_model_defaults_to_interview(monkeypatch) -> None:
    import copilot.config as cfg

    noop = lambda: None
    monkeypatch.setattr(cfg, "load_dotenv", noop)
    monkeypatch.setattr(cmr, "load_dotenv", noop)
    monkeypatch.delenv("SCREENSHOT_CURSOR_MODEL", raising=False)
    monkeypatch.setenv("CURSOR_MODEL", "composer-2")
    monkeypatch.delenv("CURSOR_MODEL_PARAMS", raising=False)
    assert cmr.resolve_screenshot_cursor_model_selection() == {"id": "composer-2"}


def test_screenshot_cursor_model_override(monkeypatch) -> None:
    monkeypatch.setenv("SCREENSHOT_CURSOR_MODEL", "gpt-5.4")
    assert cmr.resolve_screenshot_cursor_model_selection() == {"id": "gpt-5.4"}
