from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .config import (
    answer_context_chars,
    answer_max_tokens,
    answer_minimal_context,
    answer_openai_model,
    answer_provider,
    answer_request_timeout,
    cursor_agent_mirror,
    cursor_model,
    cursor_open_answer_file,
    deepseek_answer_model,
    deepseek_api_base,
    deepseek_api_key,
    openai_api_key,
    terminal_answer_stream,
)
from .answer_delivery import reveal_in_cursor, write_last_answer
from .interview_quiet import log
from .terminal_display import InterviewAnswerStream, print_interview_answer
from .cursor_bridge import (
    CursorBridgeError,
    answer_last_question,
    answer_last_question_stream,
    load_bound_session,
    push_turn_to_agent,
)

_openai_clients: dict[tuple[str, str], object] = {}
from .cursor_ide_chat import BIND_HELP, chat_is_bound
from .interview_prompt import build_system_prompt, build_user_message as build_answer_user_message
from .session_archive import record_answer_turn
from .transcript import (
    answer_self_questions_active,
    compact_dialogue_context,
    last_answer_line,
    last_answer_target,
)


class AnswerProviderError(RuntimeError):
    pass


def _openai_client(*, api_key: str, base_url: str | None):
    try:
        from openai import OpenAI
    except ImportError as e:
        raise AnswerProviderError("pip install -e 'sidecar/[openai]'") from e

    timeout = answer_request_timeout()
    cache_key = (api_key, base_url or "", timeout)
    client = _openai_clients.get(cache_key)
    if client is None:
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs)
        _openai_clients[cache_key] = client
    return client


def _no_question_error() -> str:
    if answer_self_questions_active():
        return "Нет реплики [Интервьюер] или [Я] в транскрипте."
    return "Нет реплики [Интервьюер] в транскрипте."


def _build_messages() -> tuple[str, str]:
    """(system, user)."""
    target = last_answer_target()
    if not target:
        raise AnswerProviderError(_no_question_error())
    question, speaker = target
    context = ""
    if not answer_minimal_context():
        context = compact_dialogue_context(answer_context_chars())
    user = build_answer_user_message(
        question, speaker=speaker, dialogue_context=context
    )
    system = build_system_prompt()
    return system, user


def _finalize_answer(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
) -> dict[str, Any]:
    """Файл, mirror, открытие в Cursor — без печати в терминал."""
    meta: dict[str, Any] = {
        "cursor_delivery": False,
        "cursor_agent_pushed": False,
    }

    path = write_last_answer(question, answer, provider=provider, model=model)
    meta["answer_path"] = str(path)
    if question and answer:
        record_answer_turn(
            question,
            answer,
            provider=provider,
            model=model,
        )
    log("[copilot] также:", path)

    if cursor_agent_mirror():
        if not chat_is_bound():
            meta["cursor_agent_error"] = "чат не привязан (New Agent в Cursor вручную)"
            log("[copilot] MIRROR:", BIND_HELP)
        else:
            try:
                state = load_bound_session() or {}
                meta["agentId"] = state.get("agentId", "") or state.get("chatId", "")
                meta["chatId"] = state.get("chatId", meta["agentId"])
                push_turn_to_agent(question, answer, provider=provider, model=model)
                meta["cursor_agent_pushed"] = True
                log("[copilot] push в привязанный чат")
            except CursorBridgeError as e:
                meta["cursor_agent_error"] = str(e)
                log("[copilot] WARN:", e)

    if cursor_open_answer_file():
        reveal_in_cursor(path)
        meta["cursor_delivery"] = True
        log("[copilot] открыт last-answer.md в Cursor")

    return meta


def _publish_answer(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
) -> dict[str, Any]:
    print_interview_answer(question, answer, provider=provider, model=model)
    meta = _finalize_answer(
        question,
        answer,
        provider=provider,
        model=model,
    )
    meta["terminal"] = True
    return meta


def _publish_with_stream(
    question: str,
    *,
    provider: str,
    model: str,
    collect: Callable[[Callable[[str], None]], str],
) -> dict[str, Any]:
    """collect(on_delta) -> full text; печать в терминал по чанкам."""
    stream = InterviewAnswerStream(question, provider=provider, model=model)
    stream.begin()
    parts: list[str] = []

    def on_delta(delta: str) -> None:
        if not delta:
            return
        parts.append(delta)
        stream.write_chunk(delta)

    text = collect(on_delta).strip() or "".join(parts).strip()
    if not text:
        stream.write_chunk(
            "\n[copilot] Пустой ответ от провайдера — "
            "проверь agent.mjs start или ANSWER_PROVIDER=deepseek\n"
        )
    stream.end()
    if not text:
        raise AnswerProviderError(
            f"Пустой ответ ({provider}). "
            "Cursor: node scripts/cursor-agent/agent.mjs start; "
            "или ANSWER_PROVIDER=deepseek в .env"
        )
    meta = _finalize_answer(question, text, provider=provider, model=model)
    meta["terminal"] = True
    meta["text"] = text
    return meta


def _chat_complete(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    system, user = _build_messages()
    client = _openai_client(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=answer_max_tokens(),
        temperature=0.25,
    )
    text = (resp.choices[0].message.content or "").strip()
    return {"status": "finished", "text": text, "provider": provider, "model": model}


def _chat_complete_stream(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None,
    on_delta: Callable[[str], None],
) -> str:
    system, user = _build_messages()
    client = _openai_client(api_key=api_key, base_url=base_url)
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=answer_max_tokens(),
        temperature=0.25,
        stream=True,
    )
    parts: list[str] = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            parts.append(delta)
            on_delta(delta)
    return "".join(parts).strip()


def answer_via_openai() -> dict[str, Any]:
    key = openai_api_key()
    if not key:
        raise AnswerProviderError(
            "ANSWER_PROVIDER=openai, но OPENAI_API_KEY не задан в .env"
        )
    question = last_answer_line() or ""
    model = answer_openai_model()

    if terminal_answer_stream():

        def collect(on_delta: Callable[[str], None]) -> str:
            return _chat_complete_stream(
                provider="openai",
                api_key=key,
                model=model,
                base_url=None,
                on_delta=on_delta,
            )

        meta = _publish_with_stream(
            question, provider="openai", model=model, collect=collect
        )
        return {
            "status": "finished",
            "provider": "openai",
            "model": model,
            **meta,
        }

    result = _chat_complete(provider="openai", api_key=key, model=model)
    result.update(
        _publish_answer(question, result["text"], provider="openai", model=model)
    )
    return result


def answer_via_deepseek() -> dict[str, Any]:
    key = deepseek_api_key()
    if not key:
        raise AnswerProviderError(
            "ANSWER_PROVIDER=deepseek, но DEEPSEEK_API_KEY не задан в .env"
        )
    question = last_answer_line() or ""
    model = deepseek_answer_model()

    if terminal_answer_stream():

        def collect(on_delta: Callable[[str], None]) -> str:
            return _chat_complete_stream(
                provider="deepseek",
                api_key=key,
                model=model,
                base_url=deepseek_api_base(),
                on_delta=on_delta,
            )

        meta = _publish_with_stream(
            question, provider="deepseek", model=model, collect=collect
        )
        return {
            "status": "finished",
            "provider": "deepseek",
            "model": model,
            **meta,
        }

    result = _chat_complete(
        provider="deepseek",
        api_key=key,
        model=model,
        base_url=deepseek_api_base(),
    )
    result.update(
        _publish_answer(question, result["text"], provider="deepseek", model=model)
    )
    return result


def answer_via_cursor() -> dict[str, Any]:
    question = last_answer_line() or ""
    model = cursor_model()

    if terminal_answer_stream():

        def collect(on_delta: Callable[[str], None]) -> str:
            sdk = answer_last_question_stream(on_delta)
            return (sdk.get("text") or "").strip()

        meta = _publish_with_stream(
            question, provider="cursor", model=model, collect=collect
        )
        return {
            "status": "finished",
            "provider": "cursor",
            "model": model,
            "runId": meta.get("runId"),
            **meta,
        }

    sdk = answer_last_question()
    text = (sdk.get("text") or "").strip()
    if not text:
        raise AnswerProviderError(
            "Пустой ответ (cursor). "
            "node scripts/cursor-agent/agent.mjs start или ANSWER_PROVIDER=deepseek"
        )
    result = {
        "status": sdk.get("status", "finished"),
        "text": text,
        "provider": "cursor",
        "model": model,
        "runId": sdk.get("runId"),
    }
    result.update(_publish_answer(question, text, provider="cursor", model=model))
    return result


def dispatch_answer() -> dict[str, Any]:
    provider = answer_provider()
    if provider == "openai":
        return answer_via_openai()
    if provider == "deepseek":
        return answer_via_deepseek()
    if provider != "cursor":
        raise AnswerProviderError(
            f"Неизвестный ANSWER_PROVIDER={provider!r}. "
            f"Допустимо: cursor | openai | deepseek"
        )
    return answer_via_cursor()

