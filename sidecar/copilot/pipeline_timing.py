from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .config import (
    DATA_DIR,
    copilot_timing_enabled,
    copilot_timing_hints_enabled,
    copilot_timing_jsonl_enabled,
)
from .timing_hints import suggest_tuning_hints

_lock = threading.Lock()
_active: TurnMarks | None = None


@dataclass
class TurnMarks:
    speaker: str = ""
    source: str = ""
    provider: str = ""
    speech_end: float = 0.0
    stt_final: float = 0.0
    answer_start: float = 0.0
    llm_first_token: float = 0.0
    answer_done: float = 0.0
    _llm_marked: bool = field(default=False, repr=False)


def _mono() -> float:
    return time.monotonic()


def _ms(start: float, end: float) -> int | None:
    if start <= 0 or end <= 0 or end < start:
        return None
    return max(0, round((end - start) * 1000))


def note_speech_end(speaker: str) -> None:
    """Конец речи (тишина) — сегмент ушёл в STT на финал."""
    if not copilot_timing_enabled():
        return
    global _active
    with _lock:
        _active = TurnMarks(speaker=speaker, speech_end=_mono())


def note_stt_final(speaker: str) -> None:
    """Финальный текст STT записан / отдан в transcript."""
    if not copilot_timing_enabled():
        return
    global _active
    with _lock:
        now = _mono()
        if _active is None or _active.speaker != speaker:
            _active = TurnMarks(speaker=speaker)
        _active.stt_final = now


def begin_answer(*, source: str, provider: str, speaker: str = "") -> None:
    if not copilot_timing_enabled():
        return
    global _active
    with _lock:
        if _active is None:
            _active = TurnMarks()
        _active.source = source
        _active.provider = provider
        if speaker:
            _active.speaker = speaker
        _active.answer_start = _mono()


def peek_timing_record() -> dict[str, Any] | None:
    """Снимок метрик текущего хода (для архива сессии), без сброса."""
    if not copilot_timing_enabled():
        return None
    with _lock:
        if _active is None:
            return None
        m = _active
        marks = TurnMarks(
            speaker=m.speaker,
            source=m.source,
            provider=m.provider,
            speech_end=m.speech_end,
            stt_final=m.stt_final,
            answer_start=m.answer_start,
            llm_first_token=m.llm_first_token,
            answer_done=m.answer_done if m.answer_done > 0 else _mono(),
        )
    return marks_to_record(marks)


def note_llm_first_token() -> None:
    if not copilot_timing_enabled():
        return
    with _lock:
        if _active is None or _active._llm_marked:
            return
        _active._llm_marked = True
        _active.llm_first_token = _mono()


def finish_answer() -> None:
    """Печать summary в терминал и опционально jsonl."""
    if not copilot_timing_enabled():
        return
    with _lock:
        global _active
        if _active is None:
            return
        marks = _active
        _active = None

    marks.answer_done = _mono()
    record = marks_to_record(marks)
    line = format_summary(marks)
    if line:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    if copilot_timing_hints_enabled():
        hints = suggest_tuning_hints(record)
        if hints:
            for hint in hints:
                sys.stdout.write(f"[copilot] hint: {hint}\n")
            sys.stdout.flush()
    if copilot_timing_jsonl_enabled():
        _append_jsonl(record)


def format_summary(marks: TurnMarks) -> str:
    stt = _ms(marks.speech_end, marks.stt_final)
    llm = _ms(marks.answer_start, marks.llm_first_token)
    total = _ms(marks.answer_start, marks.answer_done)
    parts: list[str] = []
    if stt is not None:
        parts.append(f"stt={stt}ms")
    if llm is not None:
        parts.append(f"llm_ttft={llm}ms")
    if total is not None:
        parts.append(f"total={total / 1000:.1f}s" if total >= 1000 else f"total={total}ms")
    if not parts:
        return ""
    meta = ", ".join(
        x
        for x in (marks.provider, marks.source, marks.speaker)
        if x
    )
    suffix = f" ({meta})" if meta else ""
    return f"[copilot] timing: {' '.join(parts)}{suffix}"


def marks_to_record(marks: TurnMarks) -> dict[str, Any]:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "speaker": marks.speaker,
        "source": marks.source,
        "provider": marks.provider,
        "stt_ms": _ms(marks.speech_end, marks.stt_final),
        "llm_ttft_ms": _ms(marks.answer_start, marks.llm_first_token),
        "answer_total_ms": _ms(marks.answer_start, marks.answer_done),
    }


def wrap_stream_delta(on_delta: Callable[[str], None]) -> Callable[[str], None]:
    def wrapped(delta: str) -> None:
        if delta:
            note_llm_first_token()
        on_delta(delta)

    return wrapped


def _append_jsonl(record: dict[str, Any]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / "session-timing.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def reset_for_tests() -> None:
    """Только для unit-тестов."""
    global _active
    with _lock:
        _active = None
