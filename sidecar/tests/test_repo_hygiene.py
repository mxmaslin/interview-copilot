"""Проверки перед публикацией репозитория на GitHub."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Реальный ID резюме не должен попадать в отслеживаемые файлы
_FORBIDDEN_RESUME_ID = "YOUR_HH_RESUME_ID"
_FORBIDDEN_PII = (
    _FORBIDDEN_RESUME_ID,
    "Маслин Максим",
    "Трубников",
)

# Файлы, где старый ID допустим (скрипт очистки истории)
_PII_ALLOWLIST = frozenset({"scripts/scrub-git-history.sh"})

_TRACKED_DENYLIST = (
    "context/resume.md",
    "context/resume-for-hh.md",
    "context/resume.hh-url",
    ".env",
)

_SECRET_PATTERNS = (
    re.compile(r"DEEPSEEK_API_KEY\s*=\s*sk-", re.I),
    re.compile(r"OPENAI_API_KEY\s*=\s*sk-", re.I),
    re.compile(r"CURSOR_API_KEY\s*=\s*cursor_[a-zA-Z0-9]{10,}", re.I),
    re.compile(r"TELEGRAM_BOT_TOKEN\s*=\s*\d+:[A-Za-z0-9_-]{20,}"),
    re.compile(r"HH_ACCESS_TOKEN\s*=\s*\S{20,}"),
)


def _git_ls_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def test_sensitive_paths_not_tracked() -> None:
    tracked = set(_git_ls_files())
    for path in _TRACKED_DENYLIST:
        assert path not in tracked, f"{path} не должен быть в git"


def test_no_known_pii_in_tracked_files() -> None:
    for rel in _git_ls_files():
        if rel.endswith(".example") or "/test_" in rel or rel in _PII_ALLOWLIST:
            continue
        path = ROOT / rel
        if not path.is_file() or path.suffix in (".png", ".jpg", ".pdf"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for needle in _FORBIDDEN_PII:
            assert needle not in text, f"PII в отслеживаемом файле: {rel}"


def test_env_example_has_no_real_secrets() -> None:
    env_ex = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in env_ex.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for pat in _SECRET_PATTERNS:
            assert not pat.search(stripped), (
                f".env.example похож на реальный секрет: {stripped[:60]}"
            )
