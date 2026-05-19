"""Проверки перед публикацией репозитория на GitHub."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_LOCAL = ROOT / "context" / "forbidden-patterns.local"

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

_HH_RESUME_URL_RE = re.compile(
    r"https?://hh\.ru/resume/[a-f0-9]{20,}",
    re.I,
)
_HH_RESUME_API_RE = re.compile(
    r"api\.hh\.ru/resumes/[a-f0-9]{20,}",
    re.I,
)

_PLACEHOLDER_MARKERS = (
    "YOUR_RESUME_ID",
    "YOUR_HH_RESUME_ID",
    "YOUR_RESUME_ID_HERE",
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


def _load_local_forbidden_needles() -> tuple[str, ...]:
    needles: list[str] = []
    env_raw = os.environ.get("COPILOT_FORBIDDEN_PII", "")
    for part in env_raw.replace(";", ",").split(","):
        part = part.strip()
        if part:
            needles.append(part)
    if _FORBIDDEN_LOCAL.exists():
        for line in _FORBIDDEN_LOCAL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            needles.append(line)
    return tuple(needles)


def _tracked_text_files() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for rel in _git_ls_files():
        if rel.endswith(".example"):
            continue
        path = ROOT / rel
        if not path.is_file() or path.suffix in (".png", ".jpg", ".pdf"):
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        out.append((rel, path))
    return out


def test_sensitive_paths_not_tracked() -> None:
    tracked = set(_git_ls_files())
    for path in _TRACKED_DENYLIST:
        assert path not in tracked, f"{path} не должен быть в git"


def test_no_hh_resume_ids_in_tracked_files() -> None:
    for rel, path in _tracked_text_files():
        text = path.read_text(encoding="utf-8")
        for pat in (_HH_RESUME_URL_RE, _HH_RESUME_API_RE):
            for match in pat.finditer(text):
                fragment = match.group(0)
                if any(marker in fragment for marker in _PLACEHOLDER_MARKERS):
                    continue
                if any(marker in text for marker in _PLACEHOLDER_MARKERS):
                    continue
                assert False, (
                    f"Похоже на реальный ID резюме hh.ru в {rel}: {fragment[:48]}..."
                )


def test_no_local_forbidden_pii_in_tracked_files() -> None:
    needles = _load_local_forbidden_needles()
    if not needles:
        pytest.skip(
            "Нет context/forbidden-patterns.local и COPILOT_FORBIDDEN_PII "
            "(локальная проверка ПДн пропущена)"
        )
    for rel, path in _tracked_text_files():
        if "/test_" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
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
