from __future__ import annotations

from copilot.transcript import merge_rolling_transcript


def test_final_replaces_unrelated_partials() -> None:
    merged = merge_rolling_transcript(["Привет"], "Как слышишь меня?")
    assert merged == "Как слышишь меня?"
