from __future__ import annotations

from dataclasses import dataclass

from .config import audio_device_hint_interviewer


class AudioDeviceNotFoundError(RuntimeError):
    """Устройство из .env не найдено в списке входов macOS."""


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    channels: int


def list_input_devices() -> list[AudioDevice]:
    import sounddevice as sd

    devices: list[AudioDevice] = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append(
                AudioDevice(
                    index=i,
                    name=str(dev["name"]),
                    channels=int(dev["max_input_channels"]),
                )
            )
    return devices


def device_sample_rate(device_index: int | None) -> int:
    """Native sample rate for PortAudio (avoids PaMacCore err -50 on macOS)."""
    import sounddevice as sd

    try:
        if device_index is None:
            default = sd.default.device
            device_index = default[0] if isinstance(default, (list, tuple)) else default
        if device_index is not None and int(device_index) >= 0:
            sr = float(sd.query_devices(int(device_index))["default_samplerate"])
            if sr > 0:
                return int(sr)
    except Exception:
        pass
    return 48000


def _pick_sample_rate(device_index: int | None, preferred: int) -> int:
    """PortAudio check — avoids PaMacCore -50 from bad samplerate at stream open."""
    import sounddevice as sd

    candidates: list[int] = []
    for rate in (preferred, 48000, 44100, 16000):
        if rate not in candidates:
            candidates.append(rate)

    last_err: Exception | None = None
    for sr in candidates:
        try:
            sd.check_input_settings(
                device=device_index,
                channels=1,
                samplerate=sr,
                dtype="float32",
            )
            return sr
        except Exception as e:
            last_err = e
    raise RuntimeError(
        f"Не удалось настроить запись (sample rate). Последняя ошибка: {last_err}"
    ) from last_err


def resolve_input_device(hint: str | None = None) -> tuple[int | None, str, int]:
    """
    Pick input device: first whose name contains hint (case-insensitive),
    else system default input.
    Returns (device_index or None for default, description, sample_rate).
    """
    import sounddevice as sd

    hint = (hint if hint is not None else audio_device_hint_interviewer()).strip()
    devices = list_input_devices()

    if hint:
        low = hint.lower()
        for d in devices:
            if low in d.name.lower():
                sr = _pick_sample_rate(d.index, device_sample_rate(d.index))
                return d.index, d.name, sr
        raise AudioDeviceNotFoundError(
            f"Вход «{hint}» не найден. "
            f"Установи BlackHole (brew install --cask blackhole-2ch + перезагрузка) "
            f"или поправь .env — docs/audio-setup.md"
        )

    try:
        default = sd.default.device
        in_idx = default[0] if isinstance(default, (list, tuple)) else default
        if in_idx is not None and int(in_idx) >= 0:
            in_idx = int(in_idx)
            name = str(sd.query_devices(in_idx)["name"])
            sr = _pick_sample_rate(in_idx, device_sample_rate(in_idx))
            return in_idx, name, sr
    except Exception:
        pass

    sr = _pick_sample_rate(None, device_sample_rate(None))
    return None, "системный ввод по умолчанию", sr
