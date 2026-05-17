from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import AGENT_STATE_PATH, REPO_ROOT, cursor_agent_chat_id_env

_TIMEOUT_TURN = 120

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_AGENT_ID_RE = re.compile(r"^agent-[0-9a-f-]{36}$", re.I)


class CursorIdeChatError(RuntimeError):
    pass


BIND_HELP = (
    "В Cursor: **Agents → _copilot → New Agent** (создаёт только пользователь).\n"
    "Затем CP → «Привязать chatId…» и вставь UUID чата "
    "(или `CURSOR_AGENT_CHAT_ID` в `.env`)."
)


def cursor_cli_path() -> str | None:
    return shutil.which("cursor")


def load_agent_state() -> dict | None:
    if not AGENT_STATE_PATH.exists():
        return None
    try:
        return json.loads(AGENT_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_agent_state(state: dict) -> None:
    AGENT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def session_id(state: dict | None) -> str | None:
    if not state:
        return None
    for key in ("chatId", "agentId"):
        val = (state.get(key) or "").strip()
        if val:
            return val
    return None


def normalize_chat_id(raw: str) -> str:
    cid = raw.strip()
    if _UUID_RE.match(cid) or _AGENT_ID_RE.match(cid):
        return cid
    raise CursorIdeChatError(
        f"Неверный chatId: {cid[:40]!r}. Нужен UUID или agent-…"
    )


def resolve_bound_chat_id() -> str | None:
    """Привязка из .env или data/agent-state.json (без автосоздания агента)."""
    env_id = cursor_agent_chat_id_env()
    if env_id:
        return env_id
    return session_id(load_agent_state())


def chat_is_bound() -> bool:
    return bool(resolve_bound_chat_id())


def bind_chat_id(chat_id: str, *, source: str = "menu") -> dict:
    cid = normalize_chat_id(chat_id)
    state = {
        "chatId": cid,
        "agentId": cid,
        "cwd": str(REPO_ROOT),
        "boundAt": datetime.now(timezone.utc).isoformat(),
        "kind": "user-bound",
        "source": source,
    }
    save_agent_state(state)
    print(f"[copilot] привязан чат Agents: {cid}", flush=True)
    return {"status": "bound", "chatId": cid, "agentId": cid}


def sync_env_chat_binding() -> str | None:
    env_id = cursor_agent_chat_id_env()
    if not env_id:
        return None
    try:
        bind_chat_id(env_id, source="env")
        return env_id
    except CursorIdeChatError:
        return None


def run_ide_turn(
    chat_id: str,
    prompt: str,
    *,
    cwd: Path | None = None,
    print_mode: bool = True,
    timeout: int = _TIMEOUT_TURN,
) -> None:
    cli = cursor_cli_path()
    if not cli:
        raise CursorIdeChatError("CLI `cursor` не найден в PATH")
    root = cwd or REPO_ROOT
    cmd = [
        cli,
        "agent",
        "--resume",
        chat_id,
        "--workspace",
        str(root),
        "--trust",
    ]
    if print_mode:
        cmd.extend(["--print", "--output-format", "text"])
    cmd.append(prompt)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(root),
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        raise CursorIdeChatError(err[:600])


def open_ide_chat(
    chat_id: str | None = None,
    *,
    cwd: Path | None = None,
    background: bool = True,
) -> None:
    cli = cursor_cli_path()
    if not cli:
        raise CursorIdeChatError("CLI `cursor` не найден")
    sid = chat_id or resolve_bound_chat_id()
    if not sid:
        raise CursorIdeChatError(BIND_HELP)
    root = cwd or REPO_ROOT
    cmd = [
        cli,
        "agent",
        "--resume",
        sid,
        "--workspace",
        str(root),
        "--trust",
    ]
    if background:
        subprocess.Popen(
            [cli, "-r", str(root)],
            cwd=str(root),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.35)
        subprocess.Popen(
            cmd,
            cwd=str(root),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[copilot] фокус на привязанном чате: {sid[:24]}…", flush=True)
        return
    subprocess.run(cmd, cwd=str(root), check=False, timeout=_TIMEOUT_TURN)


def push_turn_ide(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
    cwd: Path | None = None,
) -> None:
    sid = resolve_bound_chat_id()
    if not sid:
        raise CursorIdeChatError(BIND_HELP)
    label = f"{provider} ({model})" if model else provider
    prompt = (
        f"[Copilot · {label}]\n\n"
        f"Вопрос интервьюера:\n{question.strip()}\n\n"
        "Выведи **только** текст ниже как свой ответ (без перефразирования):\n\n"
        f"{answer.strip()}"
    )
    run_ide_turn(sid, prompt, cwd=cwd, print_mode=True)
