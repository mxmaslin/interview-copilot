from __future__ import annotations

from datetime import datetime, timezone

from .config import DATA_DIR, TRANSCRIPT_PATH


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def append_line(speaker: str, text: str) -> str:
    """speaker: 'interviewer' | 'self'"""
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


def last_interviewer_line() -> str | None:
    if not TRANSCRIPT_PATH.exists():
        return None
    lines = [
        ln
        for ln in TRANSCRIPT_PATH.read_text(encoding="utf-8").splitlines()
        if ln.startswith("[Интервьюер]:")
    ]
    if not lines:
        return None
    return lines[-1].replace("[Интервьюер]:", "", 1).strip()


def dialogue_lines() -> list[str]:
    if not TRANSCRIPT_PATH.exists():
        return []
    out: list[str] = []
    for ln in TRANSCRIPT_PATH.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("[Интервьюер]:") or s.startswith("[Я]:"):
            out.append(s)
    return out


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
