from __future__ import annotations

import base64
from collections.abc import Callable

from .answer_provider import AnswerProviderError
from .config import (
    answer_max_tokens,
    answer_request_timeout,
    anthropic_api_key,
    anthropic_base_url,
)
_anthropic_clients: dict[tuple[str, str, float], object] = {}


def _anthropic_media_type(mime: str) -> str:
    m = (mime or "image/png").lower().split(";")[0].strip()
    if m in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        return m
    if m.endswith("/jpeg") or m.endswith("/jpg"):
        return "image/jpeg"
    return "image/png"


def _anthropic_client(*, api_key: str, base_url: str | None):
    try:
        import anthropic
    except ImportError as e:
        raise AnswerProviderError(
            "SCREENSHOT_ANSWER_PROVIDER=anthropic: pip install -e 'sidecar/[llm]' "
            "(нужен пакет anthropic)"
        ) from e

    timeout = answer_request_timeout()
    cache_key = (api_key, base_url or "", timeout)
    client = _anthropic_clients.get(cache_key)
    if client is None:
        kwargs: dict = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        client = anthropic.Anthropic(**kwargs)
        _anthropic_clients[cache_key] = client
    return client


def anthropic_vision_stream(
    *,
    image_bytes: bytes,
    mime: str,
    model: str,
    system: str,
    user_text: str,
    on_delta: Callable[[str], None],
) -> str:
    key = anthropic_api_key()
    if not key:
        raise AnswerProviderError(
            "SCREENSHOT_ANSWER_PROVIDER=anthropic, но ANTHROPIC_API_KEY не задан."
        )
    client = _anthropic_client(api_key=key, base_url=anthropic_base_url())
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    parts: list[str] = []

    with client.messages.stream(
        model=model,
        max_tokens=answer_max_tokens(),
        temperature=0.2,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _anthropic_media_type(mime),
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            if text:
                parts.append(text)
                on_delta(text)

    return "".join(parts).strip()


def anthropic_vision_once(
    *, image_bytes: bytes, mime: str, model: str, system: str, user_text: str
) -> str:
    key = anthropic_api_key()
    if not key:
        raise AnswerProviderError(
            "SCREENSHOT_ANSWER_PROVIDER=anthropic, но ANTHROPIC_API_KEY не задан."
        )
    client = _anthropic_client(api_key=key, base_url=anthropic_base_url())
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    message = client.messages.create(
        model=model,
        max_tokens=answer_max_tokens(),
        temperature=0.2,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _anthropic_media_type(mime),
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    )
    chunks: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            chunks.append(getattr(block, "text", "") or "")
    return "".join(chunks).strip()
