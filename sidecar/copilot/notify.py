from __future__ import annotations

"""macOS notifications отключены — ответы и статус только в терминале."""


def notify(title: str, subtitle: str = "", message: str = "") -> None:
    del title, subtitle, message
