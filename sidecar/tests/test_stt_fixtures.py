from __future__ import annotations

from pathlib import Path

from copilot.stt_filter import is_stt_hallucination
from copilot.stt_segment import is_incomplete_self_utterance

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "stt"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8").strip()


def test_fixture_silence_tech_echo_filtered() -> None:
    assert is_stt_hallucination(_read("silence_tech_echo.txt"))


def test_fixture_complete_question_passes() -> None:
    assert not is_stt_hallucination(_read("complete_question.txt"))


def test_fixture_incomplete_tail_pending() -> None:
    assert is_incomplete_self_utterance(_read("incomplete_tail.txt"))
