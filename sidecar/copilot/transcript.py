from __future__ import annotations

import re
import threading
from collections.abc import Callable
from datetime import datetime, timezone

from .config import DATA_DIR, TRANSCRIPT_PATH

_lock = threading.Lock()
_call_mic_muted_runtime = False


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


def _self_text(line: str) -> str:
    return line.replace("[Я]:", "", 1).strip()


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


def has_interviewer_lines() -> bool:
    return any(ln.startswith("[Интервьюер]:") for ln in dialogue_lines())


def has_self_lines() -> bool:
    return any(ln.startswith("[Я]:") for ln in dialogue_lines())


def set_call_mic_muted_runtime(value: bool) -> None:
    """Меню CP: микрофон выключен на созвоне — отвечать на [Я]."""
    global _call_mic_muted_runtime
    _call_mic_muted_runtime = value


def call_mic_muted_effective() -> bool:
    from .config import call_mic_muted_on_call

    return call_mic_muted_on_call() or _call_mic_muted_runtime


def answer_self_questions_active() -> bool:
    """Отвечать на [Я], а не только на [Интервьюер] (соло / микрофон на созвоне выкл)."""
    from .config import answer_self_questions_mode, audio_listen_interviewer

    mode = answer_self_questions_mode()
    if mode in ("0", "false", "no", "never"):
        return False
    if mode in ("1", "true", "yes", "always"):
        return True
    if call_mic_muted_effective():
        return True
    if not audio_listen_interviewer():
        return True
    return not has_interviewer_lines()


def _merged_block_from_end(
    prefix: str,
    extract: Callable[[str], str],
    *,
    max_parts: int | None = None,
) -> str | None:
    dialogue = dialogue_lines()
    if not dialogue:
        return None
    i = len(dialogue) - 1
    other = "[Я]:" if prefix == "[Интервьюер]:" else "[Интервьюер]:"
    while i >= 0 and dialogue[i].startswith(other):
        i -= 1
    if i < 0 or not dialogue[i].startswith(prefix):
        return None
    parts: list[str] = []
    while i >= 0 and dialogue[i].startswith(prefix):
        text = extract(dialogue[i])
        if text:
            parts.append(text)
        i -= 1
        if max_parts is not None and len(parts) >= max_parts:
            break
    if not parts:
        return None
    parts.reverse()
    return " ".join(parts)


def last_self_question() -> str | None:
    """Последний блок [Я] с конца (подряд идущие реплики склеиваются)."""
    from .config import answer_self_merge_max

    return _merged_block_from_end(
        "[Я]:", _self_text, max_parts=answer_self_merge_max()
    )


def last_dialogue_question() -> tuple[str, str] | None:
    """(текст, 'interviewer' | 'self') — последняя реплика с конца, любой стороны."""
    dialogue = dialogue_lines()
    if not dialogue:
        return None
    last = dialogue[-1]
    if last.startswith("[Я]:"):
        text = last_self_question()
        return (text, "self") if text else None
    if last.startswith("[Интервьюер]:"):
        text = last_interviewer_question()
        return (text, "interviewer") if text else None
    return None


_SPURIOUS_INTERVIEWER_RE = re.compile(
    r"^(?:"
    r"сказать\??|"
    r"да\b|"
    r"алло\??|"
    r"угу\.?|"
    r"ага\.?|"
    r"ну\b|"
    r"слушаю\.?|"
    r"повтори\.?|"
    r"можно\??|"
    r"так\??"
    r")\s*$",
    re.IGNORECASE,
)


def _is_spurious_interviewer_fragment(text: str) -> bool:
    """Короткий шум с BlackHole (UI созвона, эхо), не вопрос собеседника."""
    t = text.strip()
    if not t:
        return True
    if _SPURIOUS_INTERVIEWER_RE.match(t):
        return True
    words = t.split()
    if len(t) <= 22 and len(words) <= 3 and t.endswith("?"):
        low = t.lower().rstrip("?")
        if low in ("сказать", "да", "алло", "ну", "так", "можно"):
            return True
    return False


def _self_overrides_interviewer(interviewer: str, self_text: str) -> bool:
    """Вопрос с Brio важнее короткого шума с BlackHole (не про «слышите»)."""
    s = self_text.strip()
    i = interviewer.strip()
    if len(s) < 10:
        return False
    if _is_spurious_interviewer_fragment(i):
        return True
    if len(i) < len(s) * 0.45 and len(s.split()) >= len(i.split()) + 2:
        return True
    return False


def last_answer_target() -> tuple[str, str] | None:
    """Цель для ⌘↩: (вопрос, speaker). speaker: interviewer | self."""
    if answer_self_questions_active():
        return last_dialogue_question()

    iv_q = last_interviewer_question()
    self_q = last_self_question()
    if self_q and iv_q and _self_overrides_interviewer(iv_q, self_q):
        return (self_q, "self")
    if self_q and not iv_q:
        return (self_q, "self")
    if iv_q:
        return (iv_q, "interviewer")
    if self_q:
        return (self_q, "self")
    return None


def last_interviewer_question() -> str | None:
    """Последние N сегментов [Интервьюер] с конца; хвостовые [Я] пропускаем."""
    from .config import answer_interviewer_merge_max

    dialogue = dialogue_lines()
    if not dialogue:
        return None
    i = len(dialogue) - 1
    while i >= 0 and dialogue[i].startswith("[Я]:"):
        i -= 1
    if i < 0:
        return None
    cap = answer_interviewer_merge_max()
    parts: list[str] = []
    while i >= 0 and dialogue[i].startswith("[Интервьюер]:"):
        text = _interviewer_text(dialogue[i])
        if text:
            parts.append(text)
        i -= 1
        if len(parts) >= cap:
            break
    if not parts:
        return None
    parts.reverse()
    return " ".join(parts)


def last_interviewer_line() -> str | None:
    """Алиас: см. last_interviewer_question."""
    return last_interviewer_question()


def last_answer_line() -> str | None:
    """Текст последнего вопроса для ⌘↩ (интервьюер или я в solo-режиме)."""
    target = last_answer_target()
    return target[0] if target else None


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
