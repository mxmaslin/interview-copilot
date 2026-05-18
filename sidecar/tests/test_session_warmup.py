from __future__ import annotations

import copilot.config as config
import copilot.session_warmup as sw


def test_session_warmup_enabled_default(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("COPILOT_SESSION_WARMUP", raising=False)
    assert config.copilot_session_warmup_enabled() is True


def test_warmup_session_starts_once(monkeypatch) -> None:
    monkeypatch.setattr(sw, "copilot_session_warmup_enabled", lambda: True)
    calls: list[str] = []

    def fake_run() -> None:
        calls.append("run")

    monkeypatch.setattr(sw, "_run_warmup", fake_run)
    sw._warm_started = False
    sw._warm_thread = None
    sw.warmup_session()
    sw.warmup_session()
    if sw._warm_thread is not None:
        sw._warm_thread.join(timeout=2.0)
    assert len(calls) == 1
