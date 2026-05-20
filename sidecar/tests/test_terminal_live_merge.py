from __future__ import annotations

from copilot.terminal_display import _merge_live_chunk


def test_merge_live_new_utterance_replaces_old() -> None:
    assert _merge_live_chunk("Привет", "Как слышишь меня") == "Как слышишь меня"
    assert _merge_live_chunk("…", "Как слышишь меня?") == "Как слышишь меня?"


def test_merge_live_extends_same_phrase() -> None:
    assert _merge_live_chunk("Как слыш", "Как слышишь меня") == "Как слышишь меня"
