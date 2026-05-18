from __future__ import annotations

import copilot.config as config
from copilot.stt_glossary import apply_glossary_fixes


def test_glossary_gil_redis(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_GLOSSARY_FIXES", "1")
    assert apply_glossary_fixes("Расскажи про гил и редис") == (
        "Расскажи про GIL и Redis"
    )


def test_glossary_disabled(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("WHISPER_GLOSSARY_FIXES", "0")
    text = "про гил"
    assert apply_glossary_fixes(text) == text
