"""Архив сессий в data/sessions/."""

from __future__ import annotations

import json

from copilot import session_archive


def test_session_lifecycle(tmp_path, monkeypatch) -> None:
    sessions = tmp_path / "sessions"
    transcript = tmp_path / "transcript.md"
    monkeypatch.setattr(session_archive, "SESSIONS_DIR", sessions)
    monkeypatch.setattr(session_archive, "TRANSCRIPT_PATH", transcript)

    transcript.write_text(
        "# Interview transcript\n\n[Интервьюер]: Расскажите про опыт\n",
        encoding="utf-8",
    )

    d1 = session_archive.start_session()
    assert d1 is not None
    session_archive.record_answer_turn(
        "Расскажите про опыт",
        "Работал в Самолёте над OAuth.",
        provider="deepseek",
        model="deepseek-chat",
        source="hotkey",
        status="completed",
        timing={"stt_ms": 120, "llm_ttft_ms": 800, "answer_total_ms": 2100},
        speaker="interviewer",
    )
    session_archive.record_answer_turn(
        "Уточнение",
        "",
        provider="deepseek",
        source="hotkey",
        status="cancelled",
    )
    transcript.write_text(
        transcript.read_text(encoding="utf-8") + "[Я]: уточнение\n",
        encoding="utf-8",
    )
    d2 = session_archive.end_session()
    assert d2 == d1

    review = (d1 / "review.md").read_text(encoding="utf-8")
    assert "Расскажите про опыт" in review
    assert "OAuth" in review
    assert "Ответ Copilot" in review
    assert (d1 / "transcript.md").read_text(encoding="utf-8").find("[Я]:") >= 0

    meta = json.loads((d1 / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "completed"
    assert meta.get("turns") == 2
    assert meta.get("turns_completed") == 1
    assert meta.get("turns_cancelled") == 1
    assert (d1 / "turns.jsonl").read_text(encoding="utf-8").count('"turn"') == 2
    assert "llm_ttft=800ms" in review

    assert session_archive.active_session_dir() is None
