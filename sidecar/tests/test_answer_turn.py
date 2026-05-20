from __future__ import annotations

from copilot.answer_turn import (
    bind_answer_generation,
    is_current_generation,
    next_answer_generation,
    reset_answer_generations_for_tests,
)


def test_generation_invalidation() -> None:
    reset_answer_generations_for_tests()
    g1 = next_answer_generation()
    bind_answer_generation(g1)
    assert is_current_generation(g1)
    g2 = next_answer_generation()
    bind_answer_generation(g2)
    assert not is_current_generation(g1)
    assert is_current_generation(g2)
