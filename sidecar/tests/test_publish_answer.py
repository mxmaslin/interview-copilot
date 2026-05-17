from __future__ import annotations

from unittest.mock import MagicMock

import copilot.answer_provider as ap


def test_publish_always_writes_file(tmp_path, monkeypatch) -> None:
    import copilot.answer_delivery as delivery

    monkeypatch.setattr(delivery, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        delivery,
        "LAST_ANSWER_PATH",
        tmp_path / "last-answer.md",
    )
    monkeypatch.setattr(delivery, "reveal_in_cursor", lambda _p=None: None)
    monkeypatch.setattr(ap, "cursor_agent_mirror", lambda: False)

    meta = ap._publish_answer("Q?", "A.", provider="deepseek", model="m")
    assert meta["terminal"] is True
    assert (tmp_path / "last-answer.md").exists()


def test_publish_agent_push_failure_still_delivers_file(
    tmp_path, monkeypatch
) -> None:
    import copilot.answer_delivery as delivery

    monkeypatch.setattr(delivery, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        delivery,
        "LAST_ANSWER_PATH",
        tmp_path / "last-answer.md",
    )
    monkeypatch.setattr(delivery, "reveal_in_cursor", lambda _p=None: None)
    monkeypatch.setattr(ap, "cursor_agent_mirror", lambda: True)
    monkeypatch.setattr(ap, "chat_is_bound", lambda: True)
    monkeypatch.setattr(ap, "load_bound_session", lambda: {"chatId": "c1"})
    monkeypatch.setattr(
        ap,
        "push_turn_to_agent",
        MagicMock(side_effect=ap.CursorBridgeError("fail")),
    )

    meta = ap._publish_answer("Q?", "A.", provider="deepseek")
    assert meta["terminal"] is True
    assert meta["cursor_agent_pushed"] is False
    assert "fail" in meta["cursor_agent_error"]


def test_publish_mirror_skips_file_open(tmp_path, monkeypatch) -> None:
    import copilot.answer_delivery as delivery

    monkeypatch.setattr(delivery, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        delivery,
        "LAST_ANSWER_PATH",
        tmp_path / "last-answer.md",
    )
    monkeypatch.setattr(ap, "cursor_agent_mirror", lambda: True)
    monkeypatch.setattr(ap, "chat_is_bound", lambda: True)
    monkeypatch.setattr(ap, "cursor_open_answer_file", lambda: False)
    monkeypatch.setattr(ap, "load_bound_session", lambda: {"chatId": "c1", "agentId": "c1"})
    monkeypatch.setattr(ap, "push_turn_to_agent", lambda *a, **k: {"mirrored": True})
    revealed: list[bool] = []
    monkeypatch.setattr(
        delivery,
        "reveal_in_cursor",
        lambda _p=None: revealed.append(True),
    )

    meta = ap._publish_answer("Q?", "A.", provider="deepseek")
    assert meta["cursor_agent_pushed"] is True
    assert meta["terminal"] is True
    assert revealed == []
