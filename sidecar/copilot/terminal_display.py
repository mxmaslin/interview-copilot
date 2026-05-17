from __future__ import annotations

import os
import shutil
import sys
import textwrap
from datetime import datetime

_INNER = 70


def _term_width() -> int:
    try:
        return max(52, min(shutil.get_terminal_size().columns, 96))
    except OSError:
        return 76


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR", "").strip() == ""


def _c(code: str, text: str) -> str:
    if not _use_color():
        return text
    return f"\033[{code}m{text}\033[0m"


def _wrap_block(text: str, indent: str = "  ") -> list[str]:
    width = min(_INNER, _term_width() - 4) - len(indent)
    lines: list[str] = []
    for para in text.strip().split("\n"):
        para = para.strip()
        if not para:
            lines.append("")
            continue
        wrapped = textwrap.fill(
            para,
            width=max(32, width),
            initial_indent=indent,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.extend(wrapped.splitlines())
    return lines


def print_interview_answer(
    question: str,
    answer: str,
    *,
    provider: str = "",
    model: str = "",
) -> None:
    """Красивый блок ответа в stdout (терминал, где запущен copilot)."""
    w = _term_width()
    bar = "─" * w
    now = datetime.now().strftime("%H:%M:%S")
    label = provider or "copilot"
    if model:
        label = f"{label} · {model}"
    header = f" COPILOT · {label} · {now} "
    pad = max(0, w - len(header) - 2)

    lines: list[str] = []
    border = ("╭", "│", "├", "╰") if _use_color() else ("+", "|", "+", "+")
    btm = ("╮", "│", "┤", "╯") if _use_color() else ("+", "|", "+", "+")

    def edge(left: str, mid: str, right: str) -> str:
        return _c("36", left + mid + right) if _use_color() else left + mid + right

    lines.append(edge(border[0], bar, btm[0]))
    lines.append(edge(border[1], header + " " * pad, btm[1]))
    lines.append(edge(border[2], bar, btm[2]))

    q_head = _c("1;33", "  Вопрос") if _use_color() else "  Вопрос"
    lines.append(edge(border[1], q_head, btm[1]))
    for ln in _wrap_block(question):
        lines.append(edge(border[1], ln or " ", btm[1]))

    lines.append(edge(border[1], " ", btm[1]))
    a_head = _c("1;32", "  Ответ") if _use_color() else "  Ответ"
    sub = _c("2", " · для озвучивания") if _use_color() else " · для озвучивания"
    lines.append(edge(border[1], a_head + sub, btm[1]))
    for ln in _wrap_block(answer):
        lines.append(edge(border[1], ln or " ", btm[1]))

    lines.append(edge(border[1], " ", btm[1]))
    lines.append(edge(border[3], bar, btm[3]))
    lines.append("")

    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
