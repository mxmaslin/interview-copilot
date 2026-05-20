from __future__ import annotations

import copilot.config as cfg
from copilot.pipeline_timing import (
    TurnMarks,
    begin_answer,
    finish_answer,
    format_summary,
    marks_to_record,
    note_speech_end,
    note_stt_final,
    reset_for_tests,
)


def test_format_summary_stt_and_llm(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "load_dotenv", lambda: None)
    marks = TurnMarks(
        speaker="self",
        source="hotkey",
        provider="deepseek",
        speech_end=1.0,
        stt_final=1.42,
        answer_start=2.0,
        llm_first_token=2.89,
        answer_done=3.3,
    )
    line = format_summary(marks)
    assert "stt=420ms" in line
    assert "llm_ttft=890ms" in line
    assert "deepseek" in line
    assert "self" in line


def test_marks_to_record_json_fields(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "load_dotenv", lambda: None)
    marks = TurnMarks(
        speaker="interviewer",
        source="auto",
        provider="cursor",
        speech_end=10.0,
        stt_final=10.5,
        answer_start=11.0,
        llm_first_token=11.2,
        answer_done=12.0,
    )
    rec = marks_to_record(marks)
    assert rec["stt_ms"] == 500
    assert rec["llm_ttft_ms"] == 200
    assert rec["answer_total_ms"] == 1000


def test_finish_answer_prints_when_enabled(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(cfg, "load_dotenv", lambda: None)
    monkeypatch.setenv("COPILOT_TIMING", "1")
    reset_for_tests()
    note_speech_end("self")
    note_stt_final("self")
    begin_answer(source="hotkey", provider="deepseek")
    finish_answer()
    out = capsys.readouterr().out
    assert "[copilot] timing:" in out
