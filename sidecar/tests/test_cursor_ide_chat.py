from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from copilot.cursor_ide_chat import (
    bind_chat_id,
    chat_is_bound,
    load_agent_state,
    normalize_chat_id,
    resolve_bound_chat_id,
    session_id,
)


def test_session_id_prefers_chat_id() -> None:
    assert session_id({"chatId": "a", "agentId": "b"}) == "a"


def test_normalize_uuid() -> None:
    uid = "00000000-0000-4000-8000-000000000001"
    assert normalize_chat_id(uid) == uid


def test_bind_chat_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.cursor_ide_chat.AGENT_STATE_PATH",
        tmp_path / "agent-state.json",
    )
    monkeypatch.setattr("copilot.cursor_ide_chat.REPO_ROOT", tmp_path)
    out = bind_chat_id("00000000-0000-4000-8000-000000000001")
    assert out["chatId"] == "00000000-0000-4000-8000-000000000001"
    data = json.loads((tmp_path / "agent-state.json").read_text())
    assert data["kind"] == "user-bound"
    assert chat_is_bound()


def test_resolve_from_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "copilot.cursor_ide_chat.AGENT_STATE_PATH",
        tmp_path / "agent-state.json",
    )
    monkeypatch.setattr(
        "copilot.cursor_ide_chat.cursor_agent_chat_id_env",
        lambda: "00000000-0000-4000-8000-000000000001",
    )
    assert resolve_bound_chat_id() == "00000000-0000-4000-8000-000000000001"
