from __future__ import annotations

import json
from typing import Any, Literal

StreamKind = Literal["delta", "done", "skip"]


def parse_answer_stream_line(line: str) -> tuple[StreamKind, dict[str, Any] | None]:
    """Разбор NDJSON-строки stdout от `agent.mjs answer`."""
    line = line.strip()
    if not line.startswith("{"):
        return "skip", None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return "skip", None
    if not isinstance(obj, dict):
        return "skip", None

    event = obj.get("event")
    if event == "delta":
        return "delta", obj
    if event == "done":
        return "done", obj

    if "text" in obj and "status" in obj:
        return "done", obj
    return "skip", None
