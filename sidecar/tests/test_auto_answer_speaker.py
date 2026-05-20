from __future__ import annotations

import copilot.transcript as transcript


def test_pin_answer_targets_interviewer_despite_trailing_self(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "transcript.md"
    monkeypatch.setattr(transcript, "TRANSCRIPT_PATH", path)
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)
    monkeypatch.setattr(transcript, "call_mic_muted_effective", lambda: True)

    transcript.append_line("interviewer", "Расскажи про Python")
    transcript.append_line("self", "угу")

    transcript.pin_answer_speaker("interviewer")
    try:
        assert transcript.last_answer_target() == (
            "Расскажи про Python",
            "interviewer",
        )
    finally:
        transcript.pin_answer_speaker(None)
