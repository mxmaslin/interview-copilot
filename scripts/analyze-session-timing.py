#!/usr/bin/env python3
"""Сводка таймингов из data/sessions/*/turns.jsonl (фаза 5 voice pipeline)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = ROOT / "data" / "sessions"
GLOBAL_JSONL = ROOT / "data" / "session-timing.jsonl"


def _pct(values: list[int], p: float) -> int | None:
    if not values:
        return None
    s = sorted(values)
    i = min(len(s) - 1, int(round((len(s) - 1) * p)))
    return s[i]


def _load_turns(session_dir: Path | None) -> list[dict]:
    rows: list[dict] = []
    dirs = [session_dir] if session_dir else sorted(SESSIONS.glob("*"))
    for d in dirs:
        if not d.is_dir():
            continue
        path = d / "turns.jsonl"
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") != "completed":
                continue
            timing = row.get("timing") or {}
            rows.append(
                {
                    "session": d.name,
                    "source": row.get("source", ""),
                    "stt_ms": timing.get("stt_ms"),
                    "llm_ttft_ms": timing.get("llm_ttft_ms"),
                    "answer_total_ms": timing.get("answer_total_ms"),
                }
            )
    if not rows and GLOBAL_JSONL.is_file():
        for line in GLOBAL_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(
                {
                    "session": "global",
                    "source": row.get("source", ""),
                    "stt_ms": row.get("stt_ms"),
                    "llm_ttft_ms": row.get("llm_ttft_ms"),
                    "answer_total_ms": row.get("answer_total_ms"),
                }
            )
    return rows


def _summarize(name: str, values: list[int]) -> str:
    if not values:
        return f"{name}: (нет данных)"
    return (
        f"{name}: n={len(values)} "
        f"med={int(statistics.median(values))}ms "
        f"p95={_pct(values, 0.95)}ms "
        f"max={max(values)}ms"
    )


def _recommend(rows: list[dict]) -> list[str]:
    stt = [r["stt_ms"] for r in rows if isinstance(r.get("stt_ms"), int)]
    llm = [r["llm_ttft_ms"] for r in rows if isinstance(r.get("llm_ttft_ms"), int)]
    out: list[str] = []
    if stt and _pct(stt, 0.5) and _pct(stt, 0.5) >= 800:
        out.append(
            "Узкое место STT: AUDIO_PRESET=call, STT_LATENCY=fast, "
            "AUDIO_SILENCE_SEC_SELF=0.85"
        )
    if llm and _pct(llm, 0.5) and _pct(llm, 0.5) >= 1500:
        out.append(
            "Узкое место LLM: deepseek-chat, ANSWER_MINIMAL_CONTEXT=1, "
            "меньше ANSWER_MAX_TOKENS"
        )
    hotkey_no_stt = sum(
        1 for r in rows if r.get("source") == "hotkey" and r.get("stt_ms") is None
    )
    if hotkey_no_stt >= max(2, len(rows) // 3):
        out.append(
            f"⌘↩ без stt_ms в {hotkey_no_stt} ходах — ожидаемо на live; "
            "смотри финал после паузы"
        )
    if not out:
        out.append("Явных узких мест по порогам 800/1500 ms не видно.")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "session",
        nargs="?",
        help="Имя папки в data/sessions (например 2026-05-20_18-22-52)",
    )
    args = parser.parse_args()
    session_dir = SESSIONS / args.session if args.session else None
    if args.session and not session_dir.is_dir():
        print(f"Нет сессии: {session_dir}", file=sys.stderr)
        return 1

    rows = _load_turns(session_dir)
    if not rows:
        print("Нет completed-ходов с timing в turns.jsonl", file=sys.stderr)
        return 1

    stt = [r["stt_ms"] for r in rows if isinstance(r.get("stt_ms"), int)]
    llm = [r["llm_ttft_ms"] for r in rows if isinstance(r.get("llm_ttft_ms"), int)]
    total = [
        r["answer_total_ms"] for r in rows if isinstance(r.get("answer_total_ms"), int)
    ]

    print(f"Ходов: {len(rows)}")
    print(_summarize("stt_ms", stt))
    print(_summarize("llm_ttft_ms", llm))
    print(_summarize("answer_total_ms", total))
    print("\nРекомендации:")
    for line in _recommend(rows):
        print(f"  • {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
