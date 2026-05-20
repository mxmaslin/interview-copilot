from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from .cursor_stream import parse_answer_stream_line

from .config import (
    AGENT_STATE_PATH,
    CURSOR_AGENT_DIR,
    DATA_DIR,
    REPO_ROOT,
    cursor_api_key,
)
from .config import screenshot_minimal_prompt, screenshot_reuse_agent
from .cursor_model_resolve import screenshot_cursor_model_selection_json
from .cursor_model_resolve import cursor_model_selection_json
from .interview_quiet import log
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
_TIMEOUT_SCREENSHOT = 240
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


def _is_stderr_noise(line: str) -> bool:
    if len(line) > 400:
        return True
    if "keyword:" in line and "schemaType:" in line:
        return True
    return False


def _extract_sdk_error(stderr: str, stdout: str) -> str:
    blob = (stderr or "") + "\n" + (stdout or "")
    tail = blob[-12000:] if len(blob) > 12000 else blob
    for pattern in (
        r"ConfigurationError[^\n]{0,400}",
        r"CursorAgentError[^\n]{0,400}",
        r'\{"error"[^\n]{0,400}',
    ):
        m = re.search(pattern, tail)
        if m:
            return _truncate(m.group(0).strip(), 800)
    markers = (
        "ConfigurationError",
        "CursorAgentError",
        "Cannot use this model",
        "No active Cursor agent",
        '{"error"',
        " not found",
    )
    lines = [
        ln.strip()
        for ln in tail.splitlines()
        if ln.strip() and not _is_stderr_noise(ln.strip())
    ]
    picked: list[str] = []
    for ln in lines:
        if any(m in ln for m in markers) or (
            ln.startswith("Error") and len(ln) < 200
        ):
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
        if _is_stderr_noise(ln):
            continue
        log("[cursor-agent]", ln)


def _cursor_sdk_env(*, with_answer_payload: bool = False) -> dict[str, str]:
    import base64

    key = cursor_api_key()
    if not key:
        raise CursorBridgeError(
            "CURSOR_API_KEY не задан. Скопируй .env.example → .env и укажи ключ."
        )
    env = {
        **os.environ,
        "CURSOR_API_KEY": key,
        "CURSOR_MODEL_JSON": cursor_model_selection_json(),
        "SCREENSHOT_CURSOR_MODEL_JSON": screenshot_cursor_model_selection_json(),
        "SCREENSHOT_MINIMAL_PROMPT": "1" if screenshot_minimal_prompt() else "0",
        "SCREENSHOT_REUSE_AGENT": "1" if screenshot_reuse_agent() else "0",
    }
    if with_answer_payload:
        from .answer_provider import cursor_answer_payload

        payload = cursor_answer_payload()
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        env["COPILOT_ANSWER_PAYLOAD_B64"] = base64.standard_b64encode(raw).decode(
            "ascii"
        )
    return env


def _run_node(command: str, *extra: str, timeout: int = _TIMEOUT_START) -> dict:
    global _active_proc
    agent_script = CURSOR_AGENT_DIR / "agent.mjs"
    if not agent_script.exists():
        raise CursorBridgeError(f"Не найден {agent_script}")

    env = _cursor_sdk_env(with_answer_payload=command == "answer")
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
            f"Таймаут Cursor SDK ({timeout} с). Закрой зависший Agent в Cursor или CP → Выход."
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
        log("[copilot] привязка chatId сброшена")


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


def _run_node_stream(
    command: str,
    *extra: str,
    on_delta: Callable[[str], None],
    timeout: int,
) -> dict:
    global _active_proc
    agent_script = CURSOR_AGENT_DIR / "agent.mjs"
    if not agent_script.exists():
        raise CursorBridgeError(f"Не найден {agent_script}")

    env = _cursor_sdk_env(with_answer_payload=command == "answer")
    cmd = ["node", str(agent_script), command, f"--cwd={REPO_ROOT}", *extra]

    proc = subprocess.Popen(
        cmd,
        cwd=str(CURSOR_AGENT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    with _proc_lock:
        _active_proc = proc

    stderr_chunks: list[str] = []
    final: dict | None = None

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            kind, obj = parse_answer_stream_line(line)
            if kind == "delta" and obj:
                text = obj.get("text") or ""
                if text:
                    on_delta(text)
            elif kind == "done" and obj:
                final = obj

        assert proc.stderr is not None
        stderr_chunks.append(proc.stderr.read())
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        cancel_active_sdk()
        raise CursorBridgeError(
            f"Таймаут Cursor SDK ({timeout} с). Закрой зависший Agent в Cursor или CP → Выход."
        ) from None
    finally:
        with _proc_lock:
            if _active_proc is proc:
                _active_proc = None

    stderr = "".join(stderr_chunks).strip()
    if proc.returncode != 0:
        _log_sdk_stderr(stderr)
        msg = _extract_sdk_error(stderr, "") or _truncate(
            stderr or f"exit {proc.returncode}"
        )
        raise CursorBridgeError(msg)

    if final is None:
        return {"status": "finished", "text": ""}

    return {
        "status": final.get("status", "finished"),
        "text": (final.get("text") or "").strip(),
        "runId": final.get("runId"),
        "model": final.get("model"),
    }


def answer_last_question_stream(on_delta: Callable[[str], None]) -> dict:
    """Cursor SDK answer с NDJSON delta на stdout (`agent.mjs answer`)."""
    return _run_node_stream("answer", on_delta=on_delta, timeout=_TIMEOUT_ANSWER)


def _warm_node(
    command: str, *, label: str, timeout: int = 90, block: bool = False
) -> bool:
    def _run() -> bool:
        try:
            _run_node(command, timeout=timeout)
            if not block:
                log(f"[copilot] {label}: ok")
            return True
        except CursorBridgeError as e:
            short = _extract_sdk_error(str(e), "") or _truncate(str(e), 200)
            log(f"[copilot] {label}:", short)
            return False

    if block:
        return _run()
    threading.Thread(target=_run, name=label, daemon=True).start()
    return True


def warmup_screenshot_agent() -> None:
    """Фоном создать/проверить SDK-агента для скриншотов (быстрее первый ⌘⌃⇧4)."""
    from .config import screenshot_answer_provider, screenshot_warm_agent

    if not screenshot_warm_agent() or screenshot_answer_provider() != "cursor":
        return
    _warm_node("screenshot-warm", label="screenshot agent warm")


def warmup_answer_agent(*, block: bool = False) -> bool:
    """Resume SDK-агента для ⌘↩ без отправки сообщения."""
    return _warm_node(
        "answer-warm", label="cursor answer warm", timeout=90, block=block
    )


def solve_screenshot_stream(
    png_bytes: bytes,
    *,
    mime: str = "image/png",
    on_delta: Callable[[str], None],
) -> dict:
    """Скриншот → Cursor SDK (agent.mjs solve-screenshot), ephemeral agent."""
    import base64

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload_path = DATA_DIR / "screenshot-cursor-payload.json"
    try:
        payload_path.write_text(
            json.dumps(
                {
                    "pngBase64": base64.standard_b64encode(png_bytes).decode("ascii"),
                    "mimeType": mime,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return _run_node_stream(
            "solve-screenshot",
            f"--payload={payload_path}",
            on_delta=on_delta,
            timeout=_TIMEOUT_SCREENSHOT,
        )
    finally:
        try:
            payload_path.unlink(missing_ok=True)
        except OSError:
            pass

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
        log("[copilot] push в привязанный чат", f"({sid[:20]}…)")
        return {"status": "finished", "mirrored": True, "chatId": sid}
    except CursorIdeChatError as e:
        raise CursorBridgeError(str(e)) from e


def open_agent_in_cursor() -> None:
    try:
        open_ide_chat(background=True)
    except CursorIdeChatError as e:
        raise CursorBridgeError(str(e)) from e
