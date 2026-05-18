from __future__ import annotations

import os

import copilot.config as config
import copilot.hf_hub as hf_hub


def test_hf_hub_token_from_env(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    assert config.hf_hub_token() == "hf_test"


def test_configure_hf_hub_sets_token(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("HF_TOKEN", "hf_secret")
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    hf_hub._configured = False
    hf_hub.configure_hf_hub()
    assert os.environ.get("HF_TOKEN") == "hf_secret"
    hf_hub._configured = False
