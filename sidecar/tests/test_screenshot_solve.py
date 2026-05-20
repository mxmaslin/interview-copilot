from __future__ import annotations

from unittest.mock import MagicMock

import copilot.config as config
import copilot.screenshot_solve as ss


def test_screenshot_answer_provider_follows_cursor(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "cursor")
    monkeypatch.delenv("SCREENSHOT_ANSWER_PROVIDER", raising=False)
    assert config.screenshot_answer_provider() == "cursor"


def test_screenshot_deepseek_falls_back_to_cursor(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "deepseek")
    monkeypatch.delenv("SCREENSHOT_ANSWER_PROVIDER", raising=False)
    monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert config.screenshot_answer_provider() == "cursor"


def test_screenshot_vision_model_override(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("SCREENSHOT_VISION_MODEL", "gpt-4o")
    assert config.screenshot_vision_model("openai") == "gpt-4o"


def test_solve_screenshot_from_clipboard_writes_file(
    tmp_path, monkeypatch
) -> None:
    import copilot.answer_delivery as delivery

    monkeypatch.setattr(delivery, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        delivery,
        "LAST_SCREENSHOT_ANSWER_PATH",
        tmp_path / "last-screenshot-answer.md",
    )
    png = b"\x89PNG\r\n\x1a\nx"
    monkeypatch.setattr(ss, "_resolve_provider", lambda: "openai")
    monkeypatch.setattr(config, "screenshot_vision_model", lambda _p: "gpt-4o-mini")
    monkeypatch.setattr(ss, "_api_credentials", lambda _p: ("key", None))
    monkeypatch.setattr(config, "terminal_answer_stream", lambda: True)
    monkeypatch.setattr(config, "screenshot_solve_also_last_answer", lambda: False)
    monkeypatch.setattr(config, "screenshot_clear_clipboard", lambda: False)

    class Delta:
        def __init__(self, content: str) -> None:
            self.content = content

    class Choice:
        def __init__(self, content: str) -> None:
            self.delta = Delta(content)

    class Chunk:
        def __init__(self, content: str) -> None:
            self.choices = [Choice(content)]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = [Chunk("42")]
    mock_openai = MagicMock()
    mock_openai.return_value = mock_client
    monkeypatch.setitem(__import__("sys").modules, "openai", MagicMock(OpenAI=mock_openai))

    result = ss.solve_screenshot_png(png)
    assert result["text"] == "42"
    assert (tmp_path / "last-screenshot-answer.md").exists()
    assert "42" in (tmp_path / "last-screenshot-answer.md").read_text(encoding="utf-8")
