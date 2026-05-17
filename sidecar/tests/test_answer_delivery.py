from __future__ import annotations

from copilot.answer_delivery import write_last_answer


def test_write_last_answer(tmp_path, monkeypatch) -> None:
    import copilot.answer_delivery as delivery

    monkeypatch.setattr(delivery, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        delivery,
        "LAST_ANSWER_PATH",
        tmp_path / "last-answer.md",
    )

    path = write_last_answer(
        "Что такое GIL?",
        "GIL — mutex в CPython.",
        provider="deepseek",
        model="deepseek-chat",
    )
    text = path.read_text(encoding="utf-8")
    assert "Что такое GIL?" in text
    assert "mutex в CPython" in text
    assert "deepseek-chat" in text
