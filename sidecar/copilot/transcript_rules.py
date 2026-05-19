"""Общие правила транскрипта (источник: transcript_rules.json, также agent.mjs)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_RULES_PATH = Path(__file__).with_name("transcript_rules.json")


@lru_cache(maxsize=1)
def load_transcript_rules() -> dict:
    return json.loads(_RULES_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def spurious_interviewer_re() -> re.Pattern[str]:
    rules = load_transcript_rules()
    return re.compile(rules["spurious_interviewer_regex"], re.IGNORECASE)


def spurious_short_questions() -> frozenset[str]:
    items = load_transcript_rules().get("spurious_short_questions", [])
    return frozenset(str(x).lower() for x in items)


def spurious_max_chars() -> int:
    return int(load_transcript_rules().get("spurious_max_chars", 22))


def spurious_max_words() -> int:
    return int(load_transcript_rules().get("spurious_max_words", 3))


def self_override_min_self_len() -> int:
    return int(load_transcript_rules().get("self_override_min_self_len", 10))


def self_override_length_ratio() -> float:
    return float(load_transcript_rules().get("self_override_length_ratio", 0.45))
