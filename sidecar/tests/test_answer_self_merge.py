from __future__ import annotations

import copilot.answer_provider as ap
import copilot.config as cfg
import copilot.transcript as transcript


def test_build_messages_skips_stale_context_when_call_mic_muted(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        transcript, "CALL_MIC_MUTED_FLAG", tmp_path / "call-mic-muted"
    )
    monkeypatch.setattr(cfg, "answer_minimal_context", lambda: False)
    monkeypatch.setattr(cfg, "answer_context_chars", lambda: 800)
    transcript.set_call_mic_muted_runtime(True)

    transcript.append_line("self", "Привет, слышишь меня?")
    transcript.append_line("self", "Как твоё настроение?")

    _system, user = ap._build_messages()

    assert "Как твоё настроение?" in user
    assert "Привет, слышишь меня?" not in user
    assert "Краткий контекст диалога" not in user
