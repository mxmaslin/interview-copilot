"""Общие фикстуры pytest для sidecar."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_pending_stt_timer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STT_PENDING_FLUSH_SEC", "0")
