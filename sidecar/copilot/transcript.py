from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from .config import DATA_DIR

CALL_MIC_MUTED_FLAG = DATA_DIR / "call-mic-muted"
from .transcript_rules import (
    self_override_length_ratio,
    self_override_min_self_len,
    spurious_interviewer_re,
    spurious_max_chars,
    spurious_max_words,
    spurious_short_questions,
)

_lock = threading.RLock()
_call_mic_muted_runtime = False
_pending_self_utterance: str | None = None
_on_self_line_committed: Callable[[], None] | None = None
_pending_flush_timer: threading.Timer | None = None
_answer_speaker_pin: str | None = None
_answer_target_pin: tuple[str, str] | None = None
# Диалог только в RAM — без read/write на каждую реплику (hot path STT / ⌘↩).
_dialogue_lines: list[str] = []


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def pending_self_utterance() -> str | None:
    with _lock:
        return _pending_self_utterance


def set_on_self_line_committed(callback: Callable[[], None] | None) -> None:
    """Вызывается после записи [Я] в transcript (финал или pending flush) — для ANSWER_AUTO."""
    global _on_self_line_committed
    _on_self_line_committed = callback


def _notify_self_line_committed() -> None:
    cb = _on_self_line_committed
    if cb is not None:
        try:
            cb()
        except Exception:
            pass


def _cancel_pending_flush_timer() -> None:
    global _pending_flush_timer
    with _lock:
        if _pending_flush_timer is not None:
            _pending_flush_timer.cancel()
            _pending_flush_timer = None


def _schedule_pending_flush_timer() -> None:
    from .config import stt_pending_flush_sec

    sec = stt_pending_flush_sec()
    if sec <= 0:
        return
    from .main_thread import run_on_main

    def fire() -> None:
        run_on_main(_flush_pending_to_ui, None)

    global _pending_flush_timer
    with _lock:
        if _pending_flush_timer is not None:
            _pending_flush_timer.cancel()
        _pending_flush_timer = threading.Timer(sec, fire)
        _pending_flush_timer.daemon = True
        _pending_flush_timer.start()


def _flush_pending_to_ui() -> None:
    """Таймаут: обрезок STT → transcript (+ терминал на main thread)."""
    line = flush_pending_self_line()
    if not line:
        return
    shown = line.replace("[Я]:", "", 1).strip()

    def show() -> None:
        from .interview_quiet import interview_active
        from .terminal_display import print_self_transcript_live

        if interview_active():
            print_self_transcript_live(shown, final=True)

    if threading.current_thread() is threading.main_thread():
        show()
        _notify_self_line_committed()
    else:
        from .main_thread import run_on_main

        def show_and_notify() -> None:
            show()
            _notify_self_line_committed()

        run_on_main(show_and_notify, None)


def flush_pending_self_line() -> str | None:
    """Записать буфер обрезанной реплики [Я] перед ⌘↩."""
    global _pending_self_utterance
    _cancel_pending_flush_timer()
    with _lock:
        pending = _pending_self_utterance
        if not pending:
            return None
        _pending_self_utterance = None
        return _write_dialogue_line("self", pending)


def _write_dialogue_line(speaker: str, text: str) -> str:
    label = "[Я]" if speaker == "self" else "[Интервьюер]"
    line = f"{label}: {text.strip()}"
    with _lock:
        _dialogue_lines.append(line)
    return line


def format_dialogue_for_terminal() -> str:
    """Текст диалога для печати в терминал (CP → Показать диалог)."""
    lines = dialogue_lines()
    if not lines:
        return "(диалог пуст)"
    return "\n".join(lines)


def merge_rolling_transcript(partials: list[str], final: str) -> str:
    """Склеить rolling-куски и финальный сегмент Whisper в одну реплику."""
    from difflib import SequenceMatcher

    chunks = [p.strip() for p in partials if (p or "").strip()]
    fin = (final or "").strip()
    if not chunks:
        return fin
    merged = " ".join(chunks).strip()
    if not fin:
        return merged
    low_m, low_f = merged.lower(), fin.lower()
    if low_f.startswith(low_m) or low_m in low_f:
        return fin
    if low_m.endswith(low_f) or low_f in low_m:
        return merged
    if SequenceMatcher(None, low_m, low_f).ratio() < 0.48:
        return fin
    return f"{merged} {fin}".strip()


def append_line(speaker: str, text: str) -> str | None:
    """speaker: 'interviewer' | 'self'. None — реплика [Я] буферизована (обрезан STT)."""
    from .endpointing import (
        is_duplicate_final,
        is_semantically_complete,
        note_final_committed,
    )
    from .stt_filter import is_stt_hallucination
    from .stt_segment import merge_self_continuation

    global _pending_self_utterance
    from .stt_glossary import apply_glossary_fixes

    cleaned = apply_glossary_fixes((text or "").strip())
    if not cleaned or is_stt_hallucination(cleaned):
        return None
    if is_duplicate_final(speaker, cleaned):
        return None

    with _lock:
        if speaker == "self":
            if _pending_self_utterance:
                cleaned = merge_self_continuation(_pending_self_utterance, cleaned)
            if not is_semantically_complete(cleaned, speaker="self"):
                _pending_self_utterance = cleaned
                _schedule_pending_flush_timer()
                return None
            _cancel_pending_flush_timer()
            _pending_self_utterance = None
            line = _write_dialogue_line("self", cleaned)
            if line:
                note_final_committed("self", cleaned)
            return line
        if not is_semantically_complete(cleaned, speaker="interviewer"):
            return None
        _pending_self_utterance = None
        line = _write_dialogue_line(speaker, cleaned)
        if line:
            note_final_committed(speaker, cleaned)
        return line


def commit_self_text_now(text: str, *, force: bool = False) -> str | None:
    """Записать [Я] без ожидания «целой» реплики (⌘↩ и буфер rolling)."""
    global _pending_self_utterance
    from .endpointing import is_duplicate_final, note_final_committed
    from .stt_filter import is_stt_hallucination

    from .stt_glossary import apply_glossary_fixes

    cleaned = apply_glossary_fixes((text or "").strip())
    if not cleaned or is_stt_hallucination(cleaned):
        return None
    if not force and is_duplicate_final("self", cleaned):
        return None
    with _lock:
        _pending_self_utterance = None
        line = _write_dialogue_line("self", cleaned)
        if line:
            note_final_committed("self", cleaned)
        return line


def _interviewer_text(line: str) -> str:
    return line.replace("[Интервьюер]:", "", 1).strip()


def _self_text(line: str) -> str:
    return line.replace("[Я]:", "", 1).strip()


def clear_dialogue() -> None:
    """Очистить диалог в RAM (⌘G / старт copilot)."""
    global _pending_self_utterance, _dialogue_lines, _answer_speaker_pin, _answer_target_pin
    _cancel_pending_flush_timer()
    with _lock:
        _pending_self_utterance = None
        _dialogue_lines.clear()
        _answer_speaker_pin = None
        _answer_target_pin = None


def dialogue_lines() -> list[str]:
    with _lock:
        return list(_dialogue_lines)


def has_interviewer_lines() -> bool:
    return any(ln.startswith("[Интервьюер]:") for ln in dialogue_lines())


def has_self_lines() -> bool:
    return any(ln.startswith("[Я]:") for ln in dialogue_lines())


def reset_call_mic_muted() -> None:
    """Сброс меню «микрофон на созвоне выкл» (при старте/выходе copilot)."""
    global _call_mic_muted_runtime
    _call_mic_muted_runtime = False
    try:
        if CALL_MIC_MUTED_FLAG.exists():
            CALL_MIC_MUTED_FLAG.unlink()
    except OSError:
        pass


def init_call_mic_muted_from_disk() -> bool:
    """При старте sidecar — всегда без галочки (не сохраняем между сессиями)."""
    reset_call_mic_muted()
    return False


def set_call_mic_muted_runtime(value: bool) -> None:
    """Меню CP: микрофон выключен на созвоне — отвечать на [Я]. Только на текущую сессию."""
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


def _self_question_merge_max() -> int:
    """Склеивать [Я] только при явном ANSWER_SELF_MERGE_MAX>1 (длинная фраза с паузой)."""
    from .config import answer_self_merge_max

    if call_mic_muted_effective():
        return 1
    if answer_self_questions_active() and not has_interviewer_lines():
        return 1
    return answer_self_merge_max()


def last_self_question() -> str | None:
    """Последний блок [Я] с конца; по умолчанию один сегмент — не тащить старые вопросы."""
    return _merged_block_from_end(
        "[Я]:", _self_text, max_parts=_self_question_merge_max()
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


def _is_spurious_interviewer_fragment(text: str) -> bool:
    """Короткий шум с BlackHole (UI созвона, эхо), не вопрос собеседника."""
    t = text.strip()
    if not t:
        return True
    if spurious_interviewer_re().match(t):
        return True
    words = t.split()
    if (
        len(t) <= spurious_max_chars()
        and len(words) <= spurious_max_words()
        and t.endswith("?")
    ):
        low = t.lower().rstrip("?")
        if low in spurious_short_questions():
            return True
    return False


def _self_overrides_interviewer(interviewer: str, self_text: str) -> bool:
    """Вопрос с Brio важнее короткого шума с BlackHole (не про «слышите»)."""
    s = self_text.strip()
    i = interviewer.strip()
    if len(s) < self_override_min_self_len():
        return False
    if _is_spurious_interviewer_fragment(i):
        return True
    ratio = self_override_length_ratio()
    if len(i) < len(s) * ratio and len(s.split()) >= len(i.split()) + 2:
        return True
    return False


def pin_answer_speaker(speaker: str | None) -> None:
    """Закрепить спикера для следующего ответа (авто-ответ после STT)."""
    global _answer_speaker_pin
    with _lock:
        _answer_speaker_pin = speaker if speaker in ("interviewer", "self") else None


def pin_answer_target(target: tuple[str, str] | None) -> None:
    """Закрепить (вопрос, speaker) для следующего dispatch_answer (⌘↩ + rolling)."""
    from .stt_glossary import normalize_question_text

    global _answer_target_pin
    with _lock:
        if target and target[0].strip():
            sp = target[1] if target[1] in ("interviewer", "self") else "self"
            _answer_target_pin = (normalize_question_text(target[0]), sp)
        else:
            _answer_target_pin = None


def commit_interviewer_text_now(text: str, *, force: bool = False) -> str | None:
    global _pending_self_utterance
    from .endpointing import is_duplicate_final, note_final_committed
    from .stt_filter import is_stt_hallucination

    from .stt_glossary import apply_glossary_fixes

    cleaned = apply_glossary_fixes((text or "").strip())
    if not cleaned or is_stt_hallucination(cleaned):
        return None
    if not force and is_duplicate_final("interviewer", cleaned):
        return None
    with _lock:
        _pending_self_utterance = None
        line = _write_dialogue_line("interviewer", cleaned)
        if line:
            note_final_committed("interviewer", cleaned)
        return line


def last_answer_target_for_speaker(speaker: str) -> tuple[str, str] | None:
    """Вопрос для авто-ответа — по спикеру сегмента STT, без путаницы с [Я]."""
    flush_pending_self_line()
    if speaker == "interviewer":
        q = last_interviewer_question()
        return (q, "interviewer") if q else None
    if speaker == "self":
        q = last_self_question()
        return (q, "self") if q else None
    return None


def last_answer_target() -> tuple[str, str] | None:
    """Цель для ⌘↩: (вопрос, speaker). speaker: interviewer | self."""
    with _lock:
        if _answer_target_pin:
            return _answer_target_pin
        pin = _answer_speaker_pin
    if pin:
        return last_answer_target_for_speaker(pin)

    flush_pending_self_line()
    if call_mic_muted_effective():
        self_q = last_self_question()
        return (self_q, "self") if self_q else None

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
    from .stt_glossary import normalize_question_text

    target = last_answer_target()
    if not target:
        return None
    return normalize_question_text(target[0]) or target[0]


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
