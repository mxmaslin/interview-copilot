from __future__ import annotations

import io
import sys
from unittest.mock import patch

import pytest

import copilot.config as config
from copilot.pipeline_timing import (
    TurnMarks,
    begin_answer,
    finish_answer,
    format_summary,
    note_speech_end,
    note_stt_final,
    reset_for_tests,
)


def test_format_summary_empty() -> None:
    assert format_summary(TurnMarks()) == ""


def test_finish_answer_prints_hints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("COPILOT_TIMING", "1")
    monkeypatch.setenv("COPILOT_TIMING_HINTS", "1")
    monkeypatch.setenv("COPILOT_LLM_SLOW_MS", "100")
    reset_for_tests()
    begin_answer(source="hotkey", provider="deepseek")
    from copilot.pipeline_timing import note_llm_first_token

    note_llm_first_token()
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf):
        finish_answer()
    assert "[copilot] hint:" in buf.getvalue()


def test_finish_answer_prints_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("COPILOT_TIMING", "1")
    monkeypatch.setenv("COPILOT_TIMING_HINTS", "0")
    reset_for_tests()
    note_speech_end("self")
    note_stt_final("self")
    begin_answer(source="hotkey", provider="deepseek", speaker="self")
    buf = io.StringIO()
    with patch.object(sys, "stdout", buf):
        finish_answer()
    out = buf.getvalue()
    assert "[copilot] timing:" in out
