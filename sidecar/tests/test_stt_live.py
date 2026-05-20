from __future__ import annotations

from copilot.stt_live import live_differs_from_file, live_question_supersedes_file


def test_supersedes_short_new_question() -> None:
    old = "Расскажешь, что знаешь про Kafka"
    live = "Что такое партийция в карте"
    assert live_question_supersedes_file(old, live)
    assert live_differs_from_file(old, live)


def test_supersedes_three_words() -> None:
    assert live_question_supersedes_file(
        "Расскажи про Kafka", "Что такое партиция"
    )


def test_same_question_not_supersedes() -> None:
    q = "Расскажи про Kafka"
    assert not live_question_supersedes_file(q, q)
    assert not live_differs_from_file(q, q)
