from __future__ import annotations

from copilot import transcript as tr


def test_compact_dialogue_context_tail_only(monkeypatch, tmp_path) -> None:
    path = tmp_path / "transcript.md"
    path.write_text(
        "# title\n"
        "<!-- meta -->\n"
        "[Интервьюер]: Q1\n"
        "[Я]: A1\n"
        "[Интервьюер]: Q2 long " + "x" * 200 + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tr, "TRANSCRIPT_PATH", path)
    ctx = tr.compact_dialogue_context(80)
    assert "[Интервьюер]: Q2" in ctx
    assert "Q1" not in ctx
