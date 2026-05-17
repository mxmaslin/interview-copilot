from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

from PyObjCTools.AppHelper import callAfter

T = TypeVar("T")


def run_on_main(func: Callable[..., T], *args: object, **kwargs: object) -> None:
    """Schedule UI work on the AppKit main thread (rumps has no call_on_main_thread)."""
    if threading.current_thread() is threading.main_thread():
        func(*args, **kwargs)
    else:
        callAfter(func, *args, **kwargs)
