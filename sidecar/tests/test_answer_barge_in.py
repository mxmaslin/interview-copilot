from __future__ import annotations

import pytest

from copilot.config import answer_barge_in_speakers


def test_barge_in_speakers_interviewer_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANSWER_BARGE_IN_ON_SPEECH", raising=False)
    assert answer_barge_in_speakers() == frozenset({"interviewer"})


def test_barge_in_speakers_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANSWER_BARGE_IN_ON_SPEECH", "0")
    assert answer_barge_in_speakers() == frozenset()


def test_barge_in_speakers_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANSWER_BARGE_IN_ON_SPEECH", "all")
    assert answer_barge_in_speakers() == frozenset({"interviewer", "self"})
