from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

from .answer_delivery import write_last_answer, write_last_screenshot_answer
from .answer_provider import AnswerProviderError, _openai_client
from .clipboard_image import (
    clear_clipboard,
    pasteboard_change_count,
    read_clipboard_image,
)
from .screenshot_optimize import optimize_screenshot_image
from .clipboard_watcher import notify_clipboard_cleared
from .config import (
    answer_max_tokens,
    answer_provider,
    answer_request_timeout,
    cursor_api_key,
    deepseek_api_base,
    deepseek_api_key,
    anthropic_api_key,
    openai_api_key,
    screenshot_answer_provider,
    screenshot_clear_clipboard,
    screenshot_openai_base_url,
    screenshot_solve_also_last_answer,
    screenshot_vision_model,
    terminal_answer_stream,
)
from .cursor_bridge import CursorBridgeError, solve_screenshot_stream
from .screenshot_anthropic import anthropic_vision_once, anthropic_vision_stream
from .interview_quiet import log
from .terminal_display import ScreenshotAnswerStream, print_interview_answer

SCREENSHOT_LABEL = "[Задача со скриншота]"

SCREENSHOT_SYSTEM = (
    "Ты решаешь задачу с изображения (скриншот экрана). "
    "Ответ на русском, EN-термины где уместно. "
    "Если на картинке задача на код — дай готовое решение (код + краткое пояснение). "
    "Если теория — структура: определение → пример → оговорки. "
    "Без воды, сразу к решению."
)

USER_TEXT = (
    "Реши задачу на изображении. "
    "Если это вопрос с вариантами — укажи правильный ответ и почему."
)


def screenshot_provider_hint() -> str:
    return screenshot_answer_provider()


def _vision_messages(image_bytes: bytes, mime: str = "image/png") -> list[dict[str, Any]]:
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    return [
        {"role": "system", "content": SCREENSHOT_SYSTEM},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": USER_TEXT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                },
            ],
        },
    ]


def _resolve_provider() -> str:
    provider = screenshot_answer_provider()
    if provider == "cursor" and not cursor_api_key():
        raise AnswerProviderError(
            "SCREENSHOT_ANSWER_PROVIDER=cursor, но CURSOR_API_KEY не задан."
        )
    if provider == "openai" and not openai_api_key():
        raise AnswerProviderError("SCREENSHOT_ANSWER_PROVIDER=openai, но OPENAI_API_KEY пуст.")
    if provider == "anthropic" and not anthropic_api_key():
        raise AnswerProviderError(
            "SCREENSHOT_ANSWER_PROVIDER=anthropic, но ANTHROPIC_API_KEY не задан."
        )
    if provider == "deepseek":
        raise AnswerProviderError(
            "deepseek-chat не поддерживает картинки в API. "
            "Добавь ANTHROPIC_API_KEY, CURSOR_API_KEY или SCREENSHOT_ANSWER_PROVIDER=openai."
        )
    if provider not in ("openai", "deepseek", "cursor", "anthropic"):
        raise AnswerProviderError(
            f"Неизвестный SCREENSHOT_ANSWER_PROVIDER={provider!r}. "
            "Допустимо: cursor | openai | anthropic | deepseek."
        )
    return provider


def _api_credentials(provider: str) -> tuple[str, str | None]:
    if provider == "openai":
        return openai_api_key() or "", screenshot_openai_base_url()
    return deepseek_api_key() or "", deepseek_api_base()


def _chat_stream(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None,
    messages: list[dict[str, Any]],
    on_delta: Callable[[str], None],
) -> str:
    client = _openai_client(api_key=api_key, base_url=base_url)
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=answer_max_tokens(),
        temperature=0.2,
        stream=True,
    )
    parts: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            parts.append(delta)
            on_delta(delta)
    return "".join(parts).strip()


def _chat_once(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None,
    messages: list[dict[str, Any]],
) -> str:
    client = _openai_client(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=answer_max_tokens(),
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _maybe_clear_clipboard_after_screenshot(
    paste_count_at_read: int,
) -> tuple[bool, bool]:
    """(cleared, deferred) — deferred=True если в буфере уже лежит следующий скрин."""
    if not screenshot_clear_clipboard():
        return False, False
    try:
        if pasteboard_change_count() != paste_count_at_read:
            log(
                "[copilot] буфер не очищаем — пока шёл ответ SDK, "
                "в буфере уже другой скриншот"
            )
            return False, True
        cleared = clear_clipboard()
        if cleared:
            notify_clipboard_cleared()
            log("[copilot] буфер обмена очищен")
        return cleared, False
    except Exception as e:
        log("[copilot] WARN: не удалось очистить буфер:", e)
        return False, False


def solve_screenshot_from_clipboard() -> dict[str, Any]:
    paste_count_at_read = pasteboard_change_count()
    item = read_clipboard_image()
    if item is None:
        raise AnswerProviderError(
            "В буфере нет изображения. Сделай ⌘⌃⇧4 (выделение → в буфер)."
        )
    data, mime = item
    return solve_screenshot_png(
        data, mime=mime, paste_count_at_read=paste_count_at_read
    )


def solve_screenshot_png(
    png_bytes: bytes,
    *,
    mime: str = "image/png",
    paste_count_at_read: int | None = None,
) -> dict[str, Any]:
    """Отправить изображение (из буфера ⌘⌃⇧4) в vision-модель."""
    if not png_bytes:
        raise AnswerProviderError("Пустое изображение.")
    png_bytes, mime = optimize_screenshot_image(png_bytes, mime)
    provider = _resolve_provider()
    model = screenshot_vision_model(provider)
    base = answer_provider()
    if base == "deepseek" and provider != "deepseek":
        log(
            f"[copilot] screenshot: ANSWER_PROVIDER=deepseek без vision "
            f"→ используем {provider}"
        )
    log(
        f"[copilot] screenshot solve: provider={provider} model={model} "
        f"bytes={len(png_bytes)} timeout={answer_request_timeout()}s"
    )

    if provider == "cursor":
        if terminal_answer_stream():
            stream = ScreenshotAnswerStream(provider=provider, model=model)
            stream.begin()
            parts: list[str] = []

            def on_delta(delta: str) -> None:
                if delta:
                    parts.append(delta)
                    stream.write_chunk(delta)

            try:
                sdk = solve_screenshot_stream(png_bytes, mime=mime, on_delta=on_delta)
            except CursorBridgeError as e:
                raise AnswerProviderError(str(e)) from e
            text = (sdk.get("text") or "").strip() or "".join(parts).strip()
            model = str(sdk.get("model") or model)
            if not text:
                stream.write_chunk(
                    "\n[copilot] Пустой ответ Cursor по скриншоту — "
                    "попробуй SCREENSHOT_ANSWER_PROVIDER=anthropic или openai\n"
                )
            stream.end()
            if not text:
                raise AnswerProviderError(
                    "Cursor SDK вернул пустой ответ по скриншоту. "
                    "В .env: SCREENSHOT_ANSWER_PROVIDER=anthropic (быстрее) или openai."
                )
        else:
            parts: list[str] = []

            def on_delta(delta: str) -> None:
                if delta:
                    parts.append(delta)

            try:
                sdk = solve_screenshot_stream(png_bytes, mime=mime, on_delta=on_delta)
            except CursorBridgeError as e:
                raise AnswerProviderError(str(e)) from e
            text = (sdk.get("text") or "").strip() or "".join(parts).strip()
            model = str(sdk.get("model") or model)
            if not text:
                raise AnswerProviderError(
                    "Cursor SDK вернул пустой ответ по скриншоту. "
                    "SCREENSHOT_ANSWER_PROVIDER=anthropic или openai."
                )
            print_interview_answer(
                SCREENSHOT_LABEL, text, provider=provider, model=model
            )
    elif provider == "anthropic":
        stream = ScreenshotAnswerStream(provider=provider, model=model)
        if terminal_answer_stream():
            stream.begin()
            parts: list[str] = []

            def on_delta(delta: str) -> None:
                if delta:
                    parts.append(delta)
                    stream.write_chunk(delta)

            text = anthropic_vision_stream(
                image_bytes=png_bytes,
                mime=mime,
                model=model,
                system=SCREENSHOT_SYSTEM,
                user_text=USER_TEXT,
                on_delta=on_delta,
            ).strip() or "".join(parts).strip()
            stream.end()
        else:
            text = anthropic_vision_once(
                image_bytes=png_bytes,
                mime=mime,
                model=model,
                system=SCREENSHOT_SYSTEM,
                user_text=USER_TEXT,
            )
            print_interview_answer(
                SCREENSHOT_LABEL, text, provider=provider, model=model
            )
    elif terminal_answer_stream():
        api_key, base_url = _api_credentials(provider)
        messages = _vision_messages(png_bytes, mime)
        stream = ScreenshotAnswerStream(provider=provider, model=model)
        stream.begin()
        parts: list[str] = []

        def on_delta(delta: str) -> None:
            if delta:
                parts.append(delta)
                stream.write_chunk(delta)

        text = _chat_stream(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            messages=messages,
            on_delta=on_delta,
        ).strip() or "".join(parts).strip()
        stream.end()
    else:
        api_key, base_url = _api_credentials(provider)
        messages = _vision_messages(png_bytes, mime)
        text = _chat_once(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            messages=messages,
        )
        print_interview_answer(
            SCREENSHOT_LABEL, text, provider=provider, model=model
        )

    shot_path = write_last_screenshot_answer(text, provider=provider, model=model)
    answer_path = shot_path
    if screenshot_solve_also_last_answer():
        answer_path = write_last_answer(
            SCREENSHOT_LABEL, text, provider=provider, model=model
        )
    log("[copilot] screenshot answer:", shot_path)
    count_at_read = (
        paste_count_at_read
        if paste_count_at_read is not None
        else pasteboard_change_count()
    )
    clipboard_cleared, clipboard_deferred = _maybe_clear_clipboard_after_screenshot(
        count_at_read
    )
    return {
        "status": "finished",
        "text": text,
        "provider": provider,
        "model": model,
        "screenshot_path": str(shot_path),
        "answer_path": str(answer_path),
        "terminal": True,
        "clipboard_cleared": clipboard_cleared,
        "clipboard_deferred": clipboard_deferred,
    }
