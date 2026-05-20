"""Архив сессий интервью: транскрипт + ответы + метрики для разбора качества."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .transcript import dialogue_lines, export_transcript_markdown

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
            "turns_completed": 0,
            "turns_cancelled": 0,
            "turns_superseded": 0,
        }
        (d / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (d / "review.md").write_text(
            f"# Сессия интервью\n\n**Начало:** {meta['started_at']}\n\n"
            "Формат: `review.md` — для чтения; `turns.jsonl` — для скриптов/аналитики.\n\n",
            encoding="utf-8",
        )
        (d / "turns.jsonl").write_text("", encoding="utf-8")
        _sync_transcript_locked(d)
        return d


def _format_timing(timing: dict[str, Any] | None) -> str:
    if not timing:
        return ""
    parts: list[str] = []
    stt = timing.get("stt_ms")
    llm = timing.get("llm_ttft_ms")
    total = timing.get("answer_total_ms")
    if stt is not None:
        parts.append(f"stt={stt}ms")
    if llm is not None:
        parts.append(f"llm_ttft={llm}ms")
    if total is not None:
        parts.append(
            f"total={total / 1000:.1f}s" if total >= 1000 else f"total={total}ms"
        )
    return " · ".join(parts)


def record_answer_turn(
    question: str,
    answer: str = "",
    *,
    provider: str,
    model: str = "",
    source: str = "hotkey",
    status: str = "completed",
    timing: dict[str, Any] | None = None,
    speaker: str = "",
) -> None:
    """Ход ⌘↩ / auto: completed | cancelled | superseded."""
    global _turn_index
    with _lock:
        d = _session_dir
        if d is None:
            return
        _turn_index += 1
        n = _turn_index
        label = f"{provider}/{model}" if model else provider
        timing_line = _format_timing(timing)
        meta_bits = [f"**Источник:** {source}", f"**Провайдер:** {label}", f"**Статус:** {status}"]
        if speaker:
            meta_bits.append(f"**Спикер:** {speaker}")
        if timing_line:
            meta_bits.append(f"**Тайминг:** {timing_line}")

        block = f"\n## Ход {n} — {_utc_now()}\n\n" + " · ".join(meta_bits)
        block += f"\n\n### Вопрос\n\n{question.strip()}\n\n"
        if answer.strip():
            block += f"### Ответ Copilot\n\n{answer.strip()}\n"
        elif status != "completed":
            block += f"### Ответ Copilot\n\n_({status})_\n"

        with (d / "review.md").open("a", encoding="utf-8") as f:
            f.write(block)

        record = {
            "turn": n,
            "ts": _utc_now(),
            "status": status,
            "source": source,
            "provider": provider,
            "model": model,
            "speaker": speaker,
            "question": question.strip(),
            "answer": answer.strip(),
            "timing": timing or {},
        }
        with (d / "turns.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        counts = {
            "turns": n,
            "turns_completed": 0,
            "turns_cancelled": 0,
            "turns_superseded": 0,
        }
        path = d / "turns.jsonl"
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                st = row.get("status", "completed")
                if st == "cancelled":
                    counts["turns_cancelled"] += 1
                elif st == "superseded":
                    counts["turns_superseded"] += 1
                else:
                    counts["turns_completed"] += 1
        _update_meta_locked(d, **counts)
        _sync_transcript_locked(d)


def record_screenshot_turn(
    answer: str,
    *,
    provider: str,
    model: str = "",
    timing: dict[str, Any] | None = None,
) -> None:
    with _lock:
        d = _session_dir
        if d is None:
            return
        timing_line = _format_timing(timing)
        block = (
            f"\n## Скриншот — {_utc_now()}\n\n"
            f"**Провайдер:** {provider}/{model or '-'}"
        )
        if timing_line:
            block += f" · **Тайминг:** {timing_line}"
        block += f"\n\n### Решение\n\n{answer.strip()}\n"
        with (d / "review.md").open("a", encoding="utf-8") as f:
            f.write(block)
        record = {
            "turn": "screenshot",
            "ts": _utc_now(),
            "status": "completed",
            "source": "screenshot",
            "provider": provider,
            "model": model,
            "answer": answer.strip(),
            "timing": timing or {},
        }
        with (d / "turns.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
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
    if not dialogue_lines():
        text = "# Interview transcript\n\n(пусто)\n"
    else:
        text = export_transcript_markdown()
    (session_dir / "transcript.md").write_text(text, encoding="utf-8")


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
