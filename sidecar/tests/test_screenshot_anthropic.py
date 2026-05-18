from __future__ import annotations

import copilot.config as config
import copilot.screenshot_solve as ss


def test_screenshot_anthropic_model_default(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("SCREENSHOT_VISION_MODEL", raising=False)
    monkeypatch.delenv("SCREENSHOT_SOLVE_MODEL", raising=False)
    assert config.screenshot_vision_model("anthropic") == "claude-3-5-haiku-latest"


def test_screenshot_provider_prefers_anthropic_when_key(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("ANSWER_PROVIDER", "deepseek")
    monkeypatch.delenv("SCREENSHOT_ANSWER_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
    assert config.screenshot_answer_provider() == "anthropic"


def test_solve_screenshot_anthropic_stream(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        ss,
        "write_last_screenshot_answer",
        lambda text, **kw: tmp_path / "out.md",
    )
    monkeypatch.setattr(ss, "write_last_answer", lambda *a, **k: tmp_path / "last.md")
    monkeypatch.setattr(ss, "screenshot_answer_provider", lambda: "anthropic")
    monkeypatch.setattr(ss, "screenshot_vision_model", lambda _p: "claude-3-5-haiku-latest")
    monkeypatch.setattr(ss, "screenshot_solve_also_last_answer", lambda: False)
    monkeypatch.setattr(ss, "screenshot_clear_clipboard", lambda: False)
    monkeypatch.setattr(ss, "terminal_answer_stream", lambda: True)
    monkeypatch.setattr(ss, "anthropic_api_key", lambda: "sk-ant-test")
    monkeypatch.setattr(ss, "answer_provider", lambda: "cursor")

    def fake_stream(**kwargs):
        kwargs["on_delta"]("42")
        return "42"

    monkeypatch.setattr(ss, "anthropic_vision_stream", fake_stream)
    monkeypatch.setattr(ss, "optimize_screenshot_image", lambda data, mime: (data, mime))

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc"
        b"\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = ss.solve_screenshot_png(png)
    assert result["text"] == "42"
    assert result["provider"] == "anthropic"
