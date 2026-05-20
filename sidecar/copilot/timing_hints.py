"""Подсказки по тюнингу latency (фаза 5 voice pipeline)."""

from __future__ import annotations

from typing import Any

from .config import (
    audio_preset,
    copilot_llm_slow_ms,
    copilot_stt_slow_ms,
    silence_seconds,
    stt_latency_preset,
)


def suggest_tuning_hints(record: dict[str, Any]) -> list[str]:
    """Рекомендации по полям timing из marks_to_record / turns.jsonl."""
    hints: list[str] = []
    stt = record.get("stt_ms")
    llm = record.get("llm_ttft_ms")
    total = record.get("answer_total_ms")
    source = (record.get("source") or "").lower()

    stt_thr = copilot_stt_slow_ms()
    llm_thr = copilot_llm_slow_ms()

    if stt is not None and stt >= stt_thr:
        preset = audio_preset() or "(не задан)"
        sil_self = silence_seconds(speaker="self")
        lat = stt_latency_preset()
        hints.append(
            f"STT {stt}ms ≥ {stt_thr}ms: сейчас preset={preset!r}, "
            f"AUDIO_SILENCE_SEC_SELF≈{sil_self}, STT_LATENCY={lat}; "
            "если медленно — interview/fast, STT_LATENCY=fast, WHISPER_MODEL_SIZE=small"
        )
    if llm is not None and llm >= llm_thr:
        hints.append(
            f"LLM TTFT {llm}ms ≥ {llm_thr}ms: deepseek-chat, "
            "ANSWER_MINIMAL_CONTEXT=1, меньше ANSWER_MAX_TOKENS"
        )
    if source == "hotkey" and stt is None and llm is not None:
        hints.append(
            "⌘↩ на live без финала: stt в timing пуст — норма; "
            "ответ идёт по rolling, финал в transcript после паузы"
        )
    if total is not None and total >= 8000 and llm is not None and llm < llm_thr:
        hints.append(
            f"total {total}ms при быстром TTFT: уменьши ANSWER_MAX_TOKENS или длину ответа"
        )
    return hints
