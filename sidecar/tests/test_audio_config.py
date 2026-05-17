from __future__ import annotations

import copilot.config as config


def test_audio_hints_defaults(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("AUDIO_INPUT_INTERVIEWER", raising=False)
    monkeypatch.delenv("AUDIO_INPUT_DEVICE", raising=False)
    monkeypatch.delenv("AUDIO_INPUT_SELF", raising=False)
    assert config.audio_device_hint_interviewer() == "BlackHole"
    assert config.audio_device_hint_self() == "Brio"


def test_audio_hints_override(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("AUDIO_INPUT_INTERVIEWER", "Loopback")
    monkeypatch.setenv("AUDIO_INPUT_SELF", "AirPods")
    assert config.audio_device_hint_interviewer() == "Loopback"
    assert config.audio_device_hint_self() == "AirPods"


def test_resolve_missing_hint_raises() -> None:
    from copilot.audio_devices import AudioDeviceNotFoundError, resolve_input_device

    try:
        resolve_input_device("NoSuchDevice_XYZ_999")
        assert False, "expected AudioDeviceNotFoundError"
    except AudioDeviceNotFoundError as e:
        assert "NoSuchDevice" in str(e)
