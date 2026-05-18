from __future__ import annotations

import copilot.config as config
from copilot.telegram_input import parse_telegram_updates


def test_telegram_input_enabled(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("TELEGRAM_INPUT_ENABLED", raising=False)
    assert config.telegram_input_enabled() is False
    monkeypatch.setenv("TELEGRAM_INPUT_ENABLED", "1")
    assert config.telegram_input_enabled() is True


def test_telegram_chat_id_alias(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("TELEGRAM_CHAT_IDS", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    assert config.telegram_allowed_chat_ids() == {42}


def test_telegram_chat_ids_parse(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "12345, 67890")
    assert config.telegram_allowed_chat_ids() == {12345, 67890}


def test_parse_telegram_updates() -> None:
    raw = [
        {
            "update_id": 10,
            "message": {
                "chat": {"id": 111},
                "text": "Что такое GIL?",
            },
        },
        {
            "update_id": 11,
            "message": {
                "chat": {"id": 222},
                "text": "ignored",
            },
        },
    ]
    parsed = parse_telegram_updates(raw)
    assert parsed == [
        (10, 111, "Что такое GIL?", None),
        (11, 222, "ignored", None),
    ]


def test_parse_telegram_voice() -> None:
    raw = [
        {
            "update_id": 12,
            "message": {
                "chat": {"id": 111},
                "voice": {"file_id": "voice_abc", "duration": 3},
            },
        },
    ]
    assert parse_telegram_updates(raw) == [(12, 111, None, "voice_abc")]
