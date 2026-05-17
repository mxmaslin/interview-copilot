from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

from .config import AGENT_STATE_PATH, CURSOR_AGENT_DIR, DATA_DIR, REPO_ROOT, cursor_api_key
from .cursor_ide_chat import (
    BIND_HELP,
    CursorIdeChatError,
    bind_chat_id,
    chat_is_bound,
    cursor_cli_path,
    load_agent_state,
    open_ide_chat,
    push_turn_ide,
    resolve_bound_chat_id,
    sync_env_chat_binding,
)

_active_proc: subprocess.Popen[str] | None = None
_proc_lock = threading.Lock()

_TIMEOUT_START = 120
_TIMEOUT_ANSWER = 180
_TIMEOUT_PUSH = 120


class CursorBridgeError(RuntimeError):
    pass


def cancel_active_sdk() -> bool:
    global _active_proc
    with _proc_lock:
        proc = _active_proc
        _active_proc = None
    if proc is None or proc.poll() is not None:
        return False
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)
    return True


def _truncate(msg: str, max_len: int = 600) -> str:
    msg = msg.strip()
    if len(msg) <= max_len:
        return msg
    return msg[:max_len] + "…"


def _extract_sdk_error(stderr: str, stdout: str) -> str:
    blob = (stderr or "") + "\n" + (stdout or "")
    if len(blob) > 8000:
        blob = blob[-8000:]
    markers = (
        "ConfigurationError",
        "CursorAgentError",
        "Cannot use this model",
        "No active Cursor agent",
        '{"error"',
    )
    lines = [ln.strip() for ln in blob.splitlines() if ln.strip()]
    picked: list[str] = []
    for ln in lines:
        if any(m in ln for m in markers) or ln.startswith("Error"):
            picked.append(ln)
    if picked:
        return _truncate("\n".join(picked[-6:]), 800)
    if lines:
        return _truncate("\n".join(lines[-4:]), 800)
    return ""


def _log_sdk_stderr(stderr: str) -> None:
    err = _extract_sdk_error(stderr, "")
    if not err:
        return
    for ln in err.splitlines():
        print(f"[cursor-agent] {ln}", flush=True)


def _run_node(command: str, *extra: str, timeout: int = _TIMEOUT_START) -> dict:
    global _active_proc
    key = cursor_api_key()
    if not key:
        raise CursorBridgeError(
            "CURSOR_API_KEY не задан. Скопируй .env.example → .env и укажи ключ."
        )
    agent_script = CURSOR_AGENT_DIR / "agent.mjs"
    if not agent_script.exists():
        raise CursorBridgeError(f"Не найден {agent_script}")

    env = {**os.environ, "CURSOR_API_KEY": key}
    cmd = ["node", str(agent_script), command, f"--cwd={REPO_ROOT}", *extra]

    proc = subprocess.Popen(
        cmd,
        cwd=str(CURSOR_AGENT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    with _proc_lock:
        _active_proc = proc

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        cancel_active_sdk()
        raise CursorBridgeError(
            f"Таймаут Cursor SDK ({timeout} с). Закрой зависший Agent в Cursor или жми «Закончить интервью»."
        ) from None
    finally:
        with _proc_lock:
            if _active_proc is proc:
                _active_proc = None

    stdout = (stdout or "").strip()
    stderr = (stderr or "").strip()
    if proc.returncode != 0:
        _log_sdk_stderr(stderr)
        msg = _extract_sdk_error(stderr, stdout) or _truncate(
            stderr or stdout or f"exit {proc.returncode}"
        )
        raise CursorBridgeError(msg)

    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"raw": stdout}


def reset_agent_state() -> None:
    if AGENT_STATE_PATH.exists():
        AGENT_STATE_PATH.unlink(missing_ok=True)
        print("[copilot] привязка chatId сброшена", flush=True)


def bind_user_chat(chat_id: str) -> dict:
    try:
        return bind_chat_id(chat_id, source="menu")
    except CursorIdeChatError as e:
        raise CursorBridgeError(str(e)) from e


def load_bound_session() -> dict | None:
    sync_env_chat_binding()
    cid = resolve_bound_chat_id()
    if not cid:
        return None
    state = load_agent_state() or {}
    return {
        "status": "bound",
        "chatId": cid,
        "agentId": cid,
        "cwd": str(state.get("cwd") or REPO_ROOT),
        "kind": state.get("kind", "user-bound"),
    }


def start_sdk_session(*, fresh: bool = False) -> dict:
    """Фоновый SDK-агент (не то же самое, что New Agent в UI). Только ANSWER_PROVIDER=cursor."""
    if fresh:
        reset_agent_state()
    return _run_node("start", timeout=_TIMEOUT_START)


def answer_last_question() -> dict:
    return _run_node("answer", timeout=_TIMEOUT_ANSWER)


def agent_session_ready() -> bool:
    return chat_is_bound()


def push_turn_to_agent(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
) -> dict:
    """Эксперимент: push в чат, если пользователь привязал chatId."""
    sid = resolve_bound_chat_id()
    if not sid:
        raise CursorBridgeError(BIND_HELP)
    if not cursor_cli_path():
        raise CursorBridgeError("CLI `cursor` не найден в PATH")
    try:
        push_turn_ide(question, answer, provider=provider, model=model)
        print(f"[copilot] push в привязанный чат ({sid[:20]}…)", flush=True)
        return {"status": "finished", "mirrored": True, "chatId": sid}
    except CursorIdeChatError as e:
        raise CursorBridgeError(str(e)) from e


def open_agent_in_cursor() -> None:
    try:
        open_ide_chat(background=True)
    except CursorIdeChatError as e:
        raise CursorBridgeError(str(e)) from e
