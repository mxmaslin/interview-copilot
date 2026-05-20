from __future__ import annotations

import copilot.config as config
from copilot.stt_prompt import interview_whisper_prompt


def test_custom_whisper_prompt(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_INITIAL_PROMPT", "Custom GIL asyncio")
    assert interview_whisper_prompt() == "Custom GIL asyncio"


def test_interview_prompt_has_english_terms(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("WHISPER_INITIAL_PROMPT", raising=False)
    monkeypatch.setenv("WHISPER_PROMPT_MODE", "interview")
    p = interview_whisper_prompt()
    assert "GIL" in p
    assert "PostgreSQL" in p
    assert "asyncio" in p


def test_general_prompt_no_it_hallucination_bias(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("WHISPER_INITIAL_PROMPT", raising=False)
    monkeypatch.setenv("WHISPER_PROMPT_MODE", "general")
    p = interview_whisper_prompt()
    assert "GIL" not in p
    assert "Kafka" not in p
    assert "латиниц" in p.lower()
    assert "дословн" not in p.lower()


def test_tech_prompt_latin_bias_without_word_list(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("WHISPER_INITIAL_PROMPT", raising=False)
    monkeypatch.setenv("WHISPER_PROMPT_MODE", "tech")
    p = interview_whisper_prompt()
    assert "латиниц" in p.lower()
    assert "Kafka" not in p
    assert "Redis" not in p
