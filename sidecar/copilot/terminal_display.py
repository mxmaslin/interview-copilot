from __future__ import annotations

import os
import shutil
import sys
import textwrap
from datetime import datetime

from .interview_quiet import interview_active

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


class InterviewAnswerStream:
    """Потоковый вывод ответа: заголовок один раз, тело — по чанкам."""

    def __init__(
        self,
        question: str,
        *,
        provider: str = "",
        model: str = "",
    ) -> None:
        self._question = question
        self._provider = provider
        self._model = model
        self._begun = False
        self._full_mode = False

    def begin(self) -> None:
        if self._begun:
            return
        self._begun = True
        if interview_active():
            self._begin_minimal()
        else:
            self._begin_full()

    def write_chunk(self, text: str) -> None:
        if not text:
            return
        if not self._begun:
            self.begin()
        sys.stdout.write(text)
        sys.stdout.flush()

    def end(self) -> None:
        if not self._begun:
            return
        if self._full_mode:
            self._end_full()
        else:
            sys.stdout.write("\n\n")
            sys.stdout.flush()

    def _begin_minimal(self) -> None:
        q_label = _c("1;33", "Вопрос") if _use_color() else "Вопрос"
        a_label = _c("1;32", "Ответ") if _use_color() else "Ответ"
        sep = _c("2", "─" * min(40, _term_width() - 2)) if _use_color() else "─" * 40
        out: list[str] = ["", q_label, sep]
        out.extend(_wrap_block(self._question, indent=""))
        out.extend(["", a_label, sep])
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()

    def _begin_full(self) -> None:
        self._full_mode = True
        w = _term_width()
        bar = "─" * w
        now = datetime.now().strftime("%H:%M:%S")
        label = self._provider or "copilot"
        if self._model:
            label = f"{label} · {self._model}"
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
        for ln in _wrap_block(self._question):
            lines.append(edge(border[1], ln or " ", btm[1]))

        lines.append(edge(border[1], " ", btm[1]))
        a_head = _c("1;32", "  Ответ") if _use_color() else "  Ответ"
        sub = _c("2", " · для озвучивания") if _use_color() else " · для озвучивания"
        lines.append(edge(border[1], a_head + sub, btm[1]))
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    def _end_full(self) -> None:
        w = _term_width()
        bar = "─" * w
        border = ("╭", "│", "├", "╰") if _use_color() else ("+", "|", "+", "+")
        btm = ("╮", "│", "┤", "╯") if _use_color() else ("+", "|", "+", "+")

        def edge(left: str, mid: str, right: str) -> str:
            return _c("36", left + mid + right) if _use_color() else left + mid + right

        lines = [
            edge(border[1], " ", btm[1]),
            edge(border[3], bar, btm[3]),
            "",
        ]
        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()


def print_interview_answer(
    question: str,
    answer: str,
    *,
    provider: str = "",
    model: str = "",
) -> None:
    """Ответ в stdout: во время интервью — только вопрос и ответ."""
    stream = InterviewAnswerStream(question, provider=provider, model=model)
    stream.begin()
    if answer:
        if interview_active():
            for ln in _wrap_block(answer, indent=""):
                stream.write_chunk(ln + "\n")
        else:
            w = _term_width()
            border = ("╭", "│", "├", "╰") if _use_color() else ("+", "|", "+", "+")
            btm = ("╮", "│", "┤", "╯") if _use_color() else ("+", "|", "+", "+")

            def edge(left: str, mid: str, right: str) -> str:
                return _c("36", left + mid + right) if _use_color() else left + mid + right

            for ln in _wrap_block(answer):
                stream.write_chunk(edge(border[1], ln or " ", btm[1]) + "\n")
    stream.end()


class ScreenshotAnswerStream:
    """Потоковый вывод ответа по скриншоту из буфера обмена."""

    def __init__(
        self,
        *,
        provider: str = "",
        model: str = "",
    ) -> None:
        self._provider = provider
        self._model = model
        self._begun = False

    def begin(self) -> None:
        if self._begun:
            return
        self._begun = True
        label = _c("1;36", "Скриншот") if _use_color() else "Скриншот"
        task = _c("1;33", "Задача") if _use_color() else "Задача"
        ans = _c("1;32", "Решение") if _use_color() else "Решение"
        sep = _c("2", "─" * min(40, _term_width() - 2)) if _use_color() else "─" * 40
        prov = self._provider or "copilot"
        if self._model:
            prov = f"{prov} · {self._model}"
        out = [
            "",
            label,
            sep,
            f"  {task}: изображение из буфера (⌘⌃⇧4)",
            f"  {prov}",
            "",
            ans,
            sep,
        ]
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()

    def write_chunk(self, text: str) -> None:
        if not text:
            return
        if not self._begun:
            self.begin()
        sys.stdout.write(text)
        sys.stdout.flush()

    def end(self) -> None:
        if not self._begun:
            return
        sys.stdout.write("\n\n")
        sys.stdout.flush()


def _print_speaker_transcript(text: str, *, label: str, color: str) -> None:
    if not text.strip():
        return
    head = _c(color, label) if _use_color() else label
    sep = _c("2", "─" * min(40, _term_width() - 2)) if _use_color() else "─" * 40
    out: list[str] = ["", head, sep]
    out.extend(_wrap_block(text.strip(), indent=""))
    out.append("")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


_live_interviewer_line = ""
_live_self_line = ""


def print_interviewer_transcript_live(text: str, *, final: bool) -> None:
    """Rolling STT: частичный текст во время речи; final — завершённая реплика."""
    global _live_interviewer_line
    chunk = (text or "").strip()
    if not chunk:
        return
    if final:
        _live_interviewer_line = ""
        print_interviewer_transcript(chunk)
        return
    prev = _live_interviewer_line
    if prev and chunk.lower().startswith(prev.lower()[: min(16, len(prev))]):
        _live_interviewer_line = chunk
    else:
        _live_interviewer_line = f"{prev} {chunk}".strip() if prev else chunk
    head = _c("1;33", "Интервьюер (live)") if _use_color() else "Интервьюер (live)"
    line = _wrap_block(_live_interviewer_line, indent="")
    out = "\n".join([head, *line, ""])
    sys.stdout.write("\x1b[2K\r" + out)
    sys.stdout.flush()


def print_self_transcript_live(text: str, *, final: bool) -> None:
    global _live_self_line
    chunk = (text or "").strip()
    if not chunk:
        return
    if final:
        _live_self_line = ""
        print_self_transcript(chunk)
        return
    prev = _live_self_line
    if prev and chunk.lower().startswith(prev.lower()[: min(16, len(prev))]):
        _live_self_line = chunk
    else:
        _live_self_line = f"{prev} {chunk}".strip() if prev else chunk
    head = _c("1;36", "Я (live)") if _use_color() else "Я (live)"
    line = _wrap_block(_live_self_line, indent="")
    out = "\n".join([head, *line, ""])
    sys.stdout.write("\x1b[2K\r" + out)
    sys.stdout.flush()


def print_interviewer_transcript(text: str) -> None:
    """Реплика интервьюера в stdout (после сегмента STT)."""
    _print_speaker_transcript(text, label="Интервьюер", color="1;33")


def print_self_transcript(text: str) -> None:
    """Своя реплика с микрофона в stdout."""
    _print_speaker_transcript(text, label="Я", color="1;36")
