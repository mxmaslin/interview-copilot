"""Согласование параллельных ответов (barge-in / turn-taking для текста).

Практика voice agents: отмена in-flight генерации не должна оставлять устаревший
артефакт (last-answer.md) от прерванного хода.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_generation = 0
_active: int | None = None


def bind_answer_generation(token: int | None) -> None:
    global _active
    with _lock:
        _active = token


def active_answer_generation() -> int | None:
    with _lock:
        return _active


def next_answer_generation() -> int:
    global _generation
    with _lock:
        _generation += 1
        return _generation


def is_current_generation(token: int) -> bool:
    with _lock:
        return token == _generation


def reset_answer_generations_for_tests() -> None:
    global _generation
    with _lock:
        _generation = 0
