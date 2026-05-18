from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from .config import (
    DATA_DIR,
    telegram_allowed_chat_ids,
    telegram_bot_token,
    telegram_input_enabled,
)

logger = logging.getLogger(__name__)

_OFFSET_PATH = DATA_DIR / "telegram-update-offset.json"
_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramInputError(RuntimeError):
    pass


class TelegramInterviewerInput:
    """Long-poll Telegram Bot API → реплики интервьюера в транскрипт."""

    def __init__(self, on_message: Callable[[str], None]) -> None:
        self._on_message = on_message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._offset = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> str:
        if not telegram_input_enabled():
            raise TelegramInputError("TELEGRAM_INPUT_ENABLED=0")
        token = telegram_bot_token()
        if not token:
            raise TelegramInputError("Задай TELEGRAM_BOT_TOKEN в .env")
        allowed = telegram_allowed_chat_ids()
        if not allowed:
            raise TelegramInputError(
                "Задай TELEGRAM_CHAT_IDS (твой chat id, через @userinfobot)"
            )
        if self.running:
            return "уже запущен"
        self._offset = _load_offset()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(token, allowed),
            daemon=True,
            name="telegram-interviewer",
        )
        self._thread.start()
        return f"бот активен, чаты: {', '.join(str(c) for c in sorted(allowed))}"

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _poll_loop(self, token: str, allowed: set[int]) -> None:
        while not self._stop.is_set():
            try:
                updates = _get_updates(token, self._offset, timeout=25)
            except TelegramInputError as e:
                logger.warning("Telegram poll: %s", e)
                if self._stop.wait(5.0):
                    break
                continue
            for update_id, chat_id, text in updates:
                self._offset = max(self._offset, update_id + 1)
                _save_offset(self._offset)
                if chat_id not in allowed:
                    continue
                text = text.strip()
                if not text:
                    continue
                if text.startswith("/"):
                    if text.split()[0] in ("/start", "/help"):
                        _send_message(
                            token,
                            chat_id,
                            "Copilot: пиши вопросы интервьюера текстом. "
                            "В терминале copilot: ⌘↩ ответ, ⌘G очистка.",
                        )
                    continue
                try:
                    self._on_message(text)
                except Exception:
                    logger.exception("Telegram on_message failed")


def _load_offset() -> int:
    try:
        if _OFFSET_PATH.exists():
            data = json.loads(_OFFSET_PATH.read_text(encoding="utf-8"))
            return int(data.get("offset", 0))
    except Exception:
        pass
    return 0


def _save_offset(offset: int) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _OFFSET_PATH.write_text(
            json.dumps({"offset": offset}, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        logger.debug("Could not save telegram offset", exc_info=True)


def _api_call(token: str, method: str, **params: Any) -> dict[str, Any]:
    url = _API.format(token=token, method=method)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise TelegramInputError(f"Telegram HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise TelegramInputError(f"Telegram сеть: {e}") from e
    except json.JSONDecodeError as e:
        raise TelegramInputError("Telegram: неверный JSON") from e
    if not body.get("ok"):
        raise TelegramInputError(body.get("description", "Telegram API error"))
    return body.get("result")  # type: ignore[return-value]


def parse_telegram_updates(raw: list[Any]) -> list[tuple[int, int, str]]:
    """Разбор result из getUpdates (для тестов и poll)."""
    out: list[tuple[int, int, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        uid = int(item.get("update_id", 0))
        msg = item.get("message")
        if not isinstance(msg, dict):
            continue
        chat = msg.get("chat")
        if not isinstance(chat, dict):
            continue
        chat_id = int(chat.get("id", 0))
        text = msg.get("text")
        if isinstance(text, str):
            out.append((uid, chat_id, text))
    return out


def _get_updates(
    token: str, offset: int, *, timeout: int = 25
) -> list[tuple[int, int, str]]:
    params: dict[str, Any] = {
        "timeout": timeout,
        "allowed_updates": json.dumps(["message"]),
    }
    if offset > 0:
        params["offset"] = offset
    raw = _api_call(token, "getUpdates", **params)
    if not isinstance(raw, list):
        return []
    return parse_telegram_updates(raw)


def _send_message(token: str, chat_id: int, text: str) -> None:
    try:
        _api_post(
            token,
            "sendMessage",
            chat_id=chat_id,
            text=text[:4000],
        )
    except TelegramInputError as e:
        logger.warning("Telegram sendMessage: %s", e)


def _api_post(token: str, method: str, **params: Any) -> Any:
    url = _API.format(token=token, method=method)
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise TelegramInputError(f"Telegram HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise TelegramInputError(f"Telegram сеть: {e}") from e
    if not payload.get("ok"):
        raise TelegramInputError(payload.get("description", "Telegram API error"))
    return payload.get("result")
