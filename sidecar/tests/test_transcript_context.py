from __future__ import annotations

from copilot import transcript as tr


def test_compact_dialogue_context_tail_only() -> None:
    tr.append_line("interviewer", "Q1")
    tr.append_line("self", "A1")
    tr.append_line("interviewer", "Q2 long " + "x" * 200)
    ctx = tr.compact_dialogue_context(80)
    assert "[Интервьюер]: Q2" in ctx
    assert "Q1" not in ctx
