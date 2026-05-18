from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import DATA_DIR, REPO_ROOT
from .interview_quiet import log

LAST_ANSWER_PATH = DATA_DIR / "last-answer.md"


def write_last_answer(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
) -> Path:
    label = f"{provider} ({model})" if model else provider
    body = (
        f"# Последний ответ Copilot\n\n"
        f"**Источник:** {label}\n\n"
        f"## Вопрос интервьюера\n\n{question.strip()}\n\n"
        f"## Ответ для озвучивания\n\n{answer.strip()}\n"
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_ANSWER_PATH.write_text(body, encoding="utf-8")
    return LAST_ANSWER_PATH


def reveal_in_cursor(path: Path | None = None) -> None:
    """Открыть ответ в Cursor (редактор) и поднять окно _copilot."""
    target = path or LAST_ANSWER_PATH
    if not target.exists():
        return
    opened = False
    cursor_cli = shutil.which("cursor")
    if cursor_cli:
        r = subprocess.run([cursor_cli, str(target)], check=False, capture_output=True)
        opened = r.returncode == 0
    if not opened:
        subprocess.run(["open", "-a", "Cursor", str(target)], check=False)
    subprocess.run(["open", "-a", "Cursor", str(REPO_ROOT)], check=False)
    log("[copilot] открываю в Cursor:", target.name)
