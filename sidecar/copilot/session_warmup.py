"""Фоновый прогрев тяжёлых компонентов при старте copilot (до первого ⌘↩ / ⌘⌃⇧4)."""

from __future__ import annotations

import threading

from .config import (
    answer_provider,
    anthropic_api_key,
    anthropic_base_url,
    copilot_session_warmup_enabled,
    deepseek_api_base,
    deepseek_api_key,
    openai_api_key,
    screenshot_answer_provider,
    stt_provider,
)
from .interview_quiet import log

_warm_thread: threading.Thread | None = None
_warm_started = False


def warmup_session() -> None:
    """Один раз на процесс copilot; повторный вызов игнорируется."""
    global _warm_thread, _warm_started
    if not copilot_session_warmup_enabled():
        return
    if _warm_started:
        return
    _warm_started = True
    _warm_thread = threading.Thread(
        target=_run_warmup, daemon=True, name="copilot-session-warmup"
    )
    _warm_thread.start()


def _run_warmup() -> None:
    if stt_provider() == "local":
        try:
            from .stt import warmup_local_model

            warmup_local_model()
            log("[copilot] session warm: whisper loading…")
        except Exception as e:
            log("[copilot] session warm: whisper:", e)

    shot = screenshot_answer_provider()
    if shot == "openai":
        _warm_openai()
    elif shot == "anthropic":
        _warm_anthropic()
    elif shot == "cursor":
        _warm_cursor_screenshot()

    ap = answer_provider()
    if ap == "cursor":
        _warm_cursor_answer()
    elif ap == "deepseek":
        _warm_deepseek()
    elif ap == "openai":
        _warm_openai()


def _warm_openai() -> None:
    key = openai_api_key()
    if not key:
        return
    try:
        from .answer_provider import _openai_client
        from .config import screenshot_openai_base_url

        base = screenshot_openai_base_url() if screenshot_answer_provider() == "openai" else None
        _openai_client(api_key=key, base_url=base)
        log("[copilot] session warm: openai client ok")
    except Exception as e:
        log("[copilot] session warm: openai:", e)


def _warm_anthropic() -> None:
    if not anthropic_api_key():
        return
    try:
        from .screenshot_anthropic import _anthropic_client

        _anthropic_client(api_key=anthropic_api_key() or "", base_url=anthropic_base_url())
        log("[copilot] session warm: anthropic client ok")
    except Exception as e:
        log("[copilot] session warm: anthropic:", e)


def _warm_deepseek() -> None:
    key = deepseek_api_key()
    if not key:
        return
    try:
        from .answer_provider import _openai_client

        _openai_client(api_key=key, base_url=deepseek_api_base())
        log("[copilot] session warm: deepseek client ok")
    except Exception as e:
        log("[copilot] session warm: deepseek:", e)


def _warm_cursor_screenshot() -> None:
    from .config import screenshot_warm_agent
    from .cursor_bridge import warmup_screenshot_agent

    if not screenshot_warm_agent():
        return
    warmup_screenshot_agent()


def _warm_cursor_answer() -> None:
    from .cursor_bridge import warmup_answer_agent
    from .cursor_ide_chat import load_agent_state, resolve_bound_chat_id

    if not resolve_bound_chat_id() and not load_agent_state():
        log(
            "[copilot] session warm: ⌘↩ (ANSWER_PROVIDER=cursor) — нет SDK-агента "
            "(data/agent-state.json). Один раз: CP → «Привязать chatId…» "
            "или: node scripts/cursor-agent/agent.mjs start"
        )
        return
    if warmup_answer_agent(block=True):
        log("[copilot] session warm: cursor answer agent ok")
