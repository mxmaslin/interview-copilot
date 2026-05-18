from __future__ import annotations

import sys
from typing import Any

_interview_active = False


def set_interview_active(active: bool) -> None:
    global _interview_active
    _interview_active = active


def interview_active() -> bool:
    return _interview_active


def log(*parts: Any, **kwargs: Any) -> None:
    """Служебные сообщения → stderr; во время интервью не печатаются."""
    if _interview_active:
        return
    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    file = kwargs.pop("file", sys.stderr)
    print(sep.join(str(p) for p in parts if p is not None), end=end, file=file, flush=True, **kwargs)
