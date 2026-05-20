"""Архив сессий интервью: транскрипт + ответы ИИ для последующего разбора."""

from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR, TRANSCRIPT_PATH

SESSIONS_DIR = DATA_DIR / "sessions"

_lock = threading.Lock()
_session_dir: Path | None = None
_turn_index = 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _session_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def active_session_dir() -> Path | None:
    return _session_dir


def start_session() -> Path | None:
    """Новая сессия (при старте copilot / сбросе интервью)."""
    global _session_dir, _turn_index
    with _lock:
        if _session_dir is not None:
            _finalize_locked(_session_dir)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        d = SESSIONS_DIR / _session_stamp()
        d.mkdir(parents=True, exist_ok=True)
        _session_dir = d
        _turn_index = 0
        meta = {
            "started_at": _utc_now(),
            "status": "active",
            "turns": 0,
        }
        (d / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (d / "review.md").write_text(
            f"# Сессия интервью\n\n**Начало:** {meta['started_at']}\n\n",
            encoding="utf-8",
        )
        _sync_transcript_locked(d)
        return d


def record_answer_turn(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
    source: str = "hotkey",
) -> None:
    """Очередной ответ ⌘↩ (или mirror)."""
    global _turn_index
    with _lock:
        d = _session_dir
        if d is None:
            return
        _turn_index += 1
        n = _turn_index
        label = f"{provider}/{model}" if model else provider
        block = (
            f"\n## Ход {n} — {_utc_now()}\n\n"
            f"**Источник:** {source} · **Провайдер:** {label}"
        )
        block += (
            f"\n\n### Вопрос\n\n{question.strip()}\n\n"
            f"### Ответ Copilot\n\n{answer.strip()}\n"
        )
        with (d / "review.md").open("a", encoding="utf-8") as f:
            f.write(block)
        _update_meta_locked(d, turns=n)
        _sync_transcript_locked(d)


def record_screenshot_turn(
    answer: str,
    *,
    provider: str,
    model: str = "",
) -> None:
    with _lock:
        d = _session_dir
        if d is None:
            return
        block = (
            f"\n## Скриншот — {_utc_now()}\n\n"
            f"**Провайдер:** {provider}/{model or '-'}\n\n"
            f"### Решение\n\n{answer.strip()}\n"
        )
        with (d / "review.md").open("a", encoding="utf-8") as f:
            f.write(block)
        _sync_transcript_locked(d)


def end_session() -> Path | None:
    """Завершение сессии (выход, конец интервью)."""
    global _session_dir
    with _lock:
        d = _session_dir
        if d is None:
            return None
        _finalize_locked(d)
        _session_dir = None
        return d


def _sync_transcript_locked(session_dir: Path) -> None:
    if TRANSCRIPT_PATH.is_file():
        shutil.copy2(TRANSCRIPT_PATH, session_dir / "transcript.md")
    else:
        (session_dir / "transcript.md").write_text(
            "# Interview transcript\n\n(пусто)\n",
            encoding="utf-8",
        )


def _update_meta_locked(session_dir: Path, **fields: Any) -> None:
    path = session_dir / "meta.json"
    meta: dict[str, Any] = {}
    if path.is_file():
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta.update(fields)
    path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _finalize_locked(session_dir: Path) -> None:
    _sync_transcript_locked(session_dir)
    _update_meta_locked(
        session_dir,
        ended_at=_utc_now(),
        status="completed",
    )
