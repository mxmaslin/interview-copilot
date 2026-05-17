from __future__ import annotations

from unittest.mock import MagicMock

import copilot.answer_provider as ap


def test_publish_with_stream(tmp_path, monkeypatch) -> None:
    import copilot.answer_delivery as delivery

    monkeypatch.setattr(delivery, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        delivery,
        "LAST_ANSWER_PATH",
        tmp_path / "last-answer.md",
    )
    monkeypatch.setattr(delivery, "reveal_in_cursor", lambda _p=None: None)
    monkeypatch.setattr(ap, "cursor_agent_mirror", lambda: False)

    chunks: list[str] = []

    def collect(on_delta) -> str:
        for part in ("One ", "two."):
            on_delta(part)
            chunks.append(part)
        return "One two."

    meta = ap._publish_with_stream(
        "Q?",
        provider="deepseek",
        model="m",
        collect=collect,
    )
    assert meta["terminal"] is True
    assert meta["text"] == "One two."
    assert (tmp_path / "last-answer.md").exists()
    assert "two." in (tmp_path / "last-answer.md").read_text(encoding="utf-8")


def test_chat_complete_stream(monkeypatch) -> None:
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
    mock_client.chat.completions.create.return_value = [
        Chunk("Hel"),
        Chunk("lo"),
    ]
    mock_openai = MagicMock()
    mock_openai.return_value = mock_client
    monkeypatch.setitem(__import__("sys").modules, "openai", MagicMock(OpenAI=mock_openai))
    monkeypatch.setattr(ap, "_build_user_message", lambda: "user msg")

    seen: list[str] = []

    text = ap._chat_complete_stream(
        provider="openai",
        api_key="k",
        model="gpt",
        base_url=None,
        on_delta=seen.append,
    )
    assert text == "Hello"
    assert seen == ["Hel", "lo"]
