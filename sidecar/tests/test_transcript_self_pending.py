from __future__ import annotations

import copilot.transcript as transcript


def test_pending_self_merges_before_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STT_PENDING_FLUSH_SEC", "0")

    assert transcript.append_line("self", "Расскажи, что знаешь про...") is None
    assert transcript.pending_self_utterance() == "Расскажи, что знаешь про..."
    line = transcript.append_line("self", "Python")
    assert line == "[Я]: Расскажи, что знаешь про Python"
    assert transcript.dialogue_lines() == ["[Я]: Расскажи, что знаешь про Python"]


def test_flush_pending_before_answer(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STT_PENDING_FLUSH_SEC", "0")
    monkeypatch.setattr(transcript, "call_mic_muted_effective", lambda: True)

    transcript.append_line("self", "Расскажи, что знаешь про...")
    assert transcript.last_answer_target() == (
        "Расскажи, что знаешь про...",
        "self",
    )
