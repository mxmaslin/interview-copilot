"""transcript_rules.json — общий контракт Python и agent.mjs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from copilot.transcript_rules import (
    load_transcript_rules,
    spurious_interviewer_re,
    spurious_short_questions,
)

RULES_PATH = Path(__file__).resolve().parents[1] / "copilot" / "transcript_rules.json"


def test_rules_json_valid_and_matches_loader() -> None:
    raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    assert raw == load_transcript_rules()
    assert spurious_interviewer_re().pattern == raw["spurious_interviewer_regex"]
    assert "сказать" in spurious_short_questions()


def test_spurious_regex_matches_noise() -> None:
    pat = spurious_interviewer_re()
    assert pat.match("алло?")
    assert pat.match("угу.")
    assert not pat.match("что такое GIL в Python?")
