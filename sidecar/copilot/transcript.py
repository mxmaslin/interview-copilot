from __future__ import annotations

import threading
from datetime import datetime, timezone

from .config import DATA_DIR, TRANSCRIPT_PATH

_lock = threading.Lock()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_line(speaker: str, text: str) -> str:
    """speaker: 'interviewer' | 'self'"""
    with _lock:
        ensure_data_dir()
        label = "[Я]" if speaker == "self" else "[Интервьюер]"
        line = f"{label}: {text.strip()}"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        block = f"\n<!-- {ts} -->\n{line}\n"
        if not TRANSCRIPT_PATH.exists():
            TRANSCRIPT_PATH.write_text("# Interview transcript\n", encoding="utf-8")
        with TRANSCRIPT_PATH.open("a", encoding="utf-8") as f:
            f.write(block)
        return line


def _interviewer_text(line: str) -> str:
    return line.replace("[Интервьюер]:", "", 1).strip()


def clear_dialogue() -> None:
    """Удалить все реплики [Интервьюер] и [Я] из transcript.md."""
    with _lock:
        ensure_data_dir()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        TRANSCRIPT_PATH.write_text(
            "# Interview transcript\n\n" f"<!-- cleared {ts} -->\n",
            encoding="utf-8",
        )


def dialogue_lines() -> list[str]:
    with _lock:
        if not TRANSCRIPT_PATH.exists():
            return []
        lines = TRANSCRIPT_PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("[Интервьюер]:") or s.startswith("[Я]:"):
            out.append(s)
    return out


def last_interviewer_question() -> str | None:
    """Подряд идущие [Интервьюер] с конца диалога (до [Я]) — один вопрос."""
    dialogue = dialogue_lines()
    if not dialogue:
        return None
    parts: list[str] = []
    for line in reversed(dialogue):
        if line.startswith("[Я]:"):
            break
        if line.startswith("[Интервьюер]:"):
            text = _interviewer_text(line)
            if text:
                parts.append(text)
    if not parts:
        return None
    parts.reverse()
    return " ".join(parts)


def last_interviewer_line() -> str | None:
    """Алиас: см. last_interviewer_question."""
    return last_interviewer_question()


def compact_dialogue_context(max_chars: int) -> str:
    """Последние реплики диалога, без HTML/заголовков — меньше токенов."""
    dialogue = dialogue_lines()
    if not dialogue:
        return ""
    picked: list[str] = []
    total = 0
    for line in reversed(dialogue):
        add = len(line) + (1 if picked else 0)
        if picked and total + add > max_chars:
            break
        picked.append(line)
        total += add
    picked.reverse()
    return "\n".join(picked)
