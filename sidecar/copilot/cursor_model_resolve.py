from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_dotenv

_CLI_CONFIG = Path.home() / ".cursor" / "cli-config.json"
_DEFAULT_ID = "composer-2"


def _env(name: str, default: str = "") -> str:
    load_dotenv()
    import os

    return os.environ.get(name, default).strip()


def read_cli_config_model() -> dict[str, Any] | None:
    """Модель из ~/.cursor/cli-config.json (selectedModel / model)."""
    if not _CLI_CONFIG.is_file():
        return None
    try:
        data = json.loads(_CLI_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    sel = data.get("selectedModel") or data.get("model")
    if not isinstance(sel, dict):
        return None

    model_id = (sel.get("modelId") or sel.get("id") or "").strip()
    if not model_id:
        return None

    params = sel.get("parameters") or sel.get("params")
    if not isinstance(params, list):
        params = []

    normalized: list[dict[str, str]] = []
    for item in params:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id", "")).strip()
        val = item.get("value")
        if pid and val is not None:
            normalized.append({"id": pid, "value": str(val)})

    out: dict[str, Any] = {"id": model_id}
    if normalized:
        out["params"] = normalized
    return out


def resolve_cursor_model_selection() -> dict[str, Any]:
    """
    Выбор модели для Cursor SDK: CURSOR_MODEL=id или auto|cli|cli-config.
  """
    raw = _env("CURSOR_MODEL", _DEFAULT_ID)
    if raw.lower() in ("auto", "cli", "cli-config"):
        picked = read_cli_config_model()
        return picked if picked else {"id": _DEFAULT_ID}

    out: dict[str, Any] = {"id": raw or _DEFAULT_ID}
    params_raw = _env("CURSOR_MODEL_PARAMS")
    if params_raw:
        try:
            parsed = json.loads(params_raw)
            if isinstance(parsed, list):
                out["params"] = parsed
        except json.JSONDecodeError:
            pass
    return out


def cursor_model_label(selection: dict[str, Any] | None = None) -> str:
    sel = selection if selection is not None else resolve_cursor_model_selection()
    mid = str(sel.get("id") or _DEFAULT_ID)
    params = sel.get("params")
    if not isinstance(params, list) or not params:
        return mid
    bits: list[str] = []
    for p in params:
        if isinstance(p, dict) and p.get("id") is not None and p.get("value") is not None:
            bits.append(f"{p['id']}={p['value']}")
    return f"{mid}({','.join(bits)})" if bits else mid


def resolve_screenshot_cursor_model_selection() -> dict[str, Any]:
    """Модель только для solve-screenshot; иначе как ⌘↩ (CURSOR_MODEL)."""
    raw = _env("SCREENSHOT_CURSOR_MODEL")
    if not raw:
        return resolve_cursor_model_selection()
    if raw.lower() in ("auto", "cli", "cli-config"):
        picked = read_cli_config_model()
        return picked if picked else {"id": _DEFAULT_ID}
    out: dict[str, Any] = {"id": raw or _DEFAULT_ID}
    params_raw = _env("SCREENSHOT_CURSOR_MODEL_PARAMS")
    if params_raw:
        try:
            parsed = json.loads(params_raw)
            if isinstance(parsed, list):
                out["params"] = parsed
        except json.JSONDecodeError:
            pass
    return out


def screenshot_cursor_model_selection_json() -> str:
    return json.dumps(resolve_screenshot_cursor_model_selection(), ensure_ascii=False)


def cursor_model_selection_json() -> str:
    return json.dumps(resolve_cursor_model_selection(), ensure_ascii=False)
