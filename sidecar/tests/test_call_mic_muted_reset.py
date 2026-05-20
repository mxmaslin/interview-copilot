from __future__ import annotations

import copilot.transcript as transcript


def test_reset_clears_runtime_and_flag_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        transcript, "CALL_MIC_MUTED_FLAG", tmp_path / "call-mic-muted"
    )
    transcript.set_call_mic_muted_runtime(True)
    (tmp_path / "call-mic-muted").write_text("1\n", encoding="utf-8")

    transcript.reset_call_mic_muted()

    assert transcript.call_mic_muted_effective() is False
    assert not (tmp_path / "call-mic-muted").exists()


def test_init_does_not_restore_flag_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        transcript, "CALL_MIC_MUTED_FLAG", tmp_path / "call-mic-muted"
    )
    (tmp_path / "call-mic-muted").write_text("1\n", encoding="utf-8")

    assert transcript.init_call_mic_muted_from_disk() is False
    assert transcript.call_mic_muted_effective() is False
