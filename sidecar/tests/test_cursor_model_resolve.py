from __future__ import annotations

import json

import copilot.config as config
import copilot.cursor_model_resolve as cmr


def test_resolve_auto_from_cli_config(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "cli-config.json"
    cfg.write_text(
        json.dumps(
            {
                "selectedModel": {
                    "modelId": "composer-2",
                    "parameters": [{"id": "fast", "value": "true"}],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cmr, "_CLI_CONFIG", cfg)
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("CURSOR_MODEL", "auto")

    sel = cmr.resolve_cursor_model_selection()
    assert sel["id"] == "composer-2"
    assert sel["params"] == [{"id": "fast", "value": "true"}]
    assert cmr.cursor_model_label(sel) == "composer-2(fast=true)"


def test_resolve_explicit_model(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("CURSOR_MODEL", "composer-2")

    sel = cmr.resolve_cursor_model_selection()
    assert sel == {"id": "composer-2"}
