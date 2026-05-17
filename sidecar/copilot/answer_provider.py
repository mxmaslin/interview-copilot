from __future__ import annotations

from typing import Any

from .config import (
    answer_context_chars,
    answer_max_tokens,
    answer_minimal_context,
    answer_openai_model,
    answer_provider,
    cursor_agent_mirror,
    cursor_open_answer_file,
    deepseek_answer_model,
    deepseek_api_base,
    deepseek_api_key,
    openai_api_key,
)
from .answer_delivery import reveal_in_cursor, write_last_answer
from .terminal_display import print_interview_answer
from .cursor_bridge import (
    CursorBridgeError,
    load_bound_session,
    push_turn_to_agent,
)
from .cursor_ide_chat import BIND_HELP, chat_is_bound
from .transcript import compact_dialogue_context, last_interviewer_line

INTERVIEW_SYSTEM = (
    "Ты — ассистент на техническом интервью (Python backend). "
    "Отвечай кратко на русском, EN-термины где уместно. "
    "Структура: определение → пример → оговорки. 5–8 предложений, для озвучивания вслух."
)


class AnswerProviderError(RuntimeError):
    pass


def _build_user_message() -> str:
    question = last_interviewer_line()
    if not question:
        raise AnswerProviderError("Нет реплики [Интервьюер] в транскрипте.")
    user = f"Вопрос интервьюера:\n{question.strip()}"
    if not answer_minimal_context():
        context = compact_dialogue_context(answer_context_chars())
        if context:
            user += f"\n\nКраткий контекст диалога:\n{context}"
    return user


def _publish_answer(
    question: str,
    answer: str,
    *,
    provider: str,
    model: str = "",
) -> dict[str, Any]:
    """
    1) data/last-answer.md (архив).
    2) При CURSOR_AGENT_MIRROR=1 — ответ в панели Agents → _copilot (приоритет над файлом).
    """
    meta: dict[str, Any] = {
        "cursor_delivery": False,
        "cursor_agent_pushed": False,
    }
    print_interview_answer(
        question, answer, provider=provider, model=model
    )
    meta["terminal"] = True

    path = write_last_answer(question, answer, provider=provider, model=model)
    meta["answer_path"] = str(path)
    print(f"[copilot] также: {path}", flush=True)

    if cursor_agent_mirror():
        if not chat_is_bound():
            meta["cursor_agent_error"] = "чат не привязан (New Agent в Cursor вручную)"
            print(f"[copilot] MIRROR: {BIND_HELP}", flush=True)
        else:
            try:
                state = load_bound_session() or {}
                meta["agentId"] = state.get("agentId", "") or state.get("chatId", "")
                meta["chatId"] = state.get("chatId", meta["agentId"])
                push_turn_to_agent(question, answer, provider=provider, model=model)
                meta["cursor_agent_pushed"] = True
                print("[copilot] push в привязанный чат (без переключения окна)", flush=True)
            except CursorBridgeError as e:
                meta["cursor_agent_error"] = str(e)
                print(f"[copilot] WARN: {e}", flush=True)

    if cursor_open_answer_file():
        reveal_in_cursor(path)
        meta["cursor_delivery"] = True
        print("[copilot] открыт last-answer.md в Cursor (CURSOR_OPEN_ANSWER_FILE=1)", flush=True)

    return meta


def _chat_complete(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise AnswerProviderError("pip install -e 'sidecar/[openai]'") from e

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": INTERVIEW_SYSTEM},
            {"role": "user", "content": _build_user_message()},
        ],
        max_tokens=answer_max_tokens(),
        temperature=0.25,
    )
    text = (resp.choices[0].message.content or "").strip()
    return {"status": "finished", "text": text, "provider": provider, "model": model}


def answer_via_openai() -> dict[str, Any]:
    key = openai_api_key()
    if not key:
        raise AnswerProviderError(
            "ANSWER_PROVIDER=openai, но OPENAI_API_KEY не задан в .env"
        )
    question = last_interviewer_line() or ""
    model = answer_openai_model()
    result = _chat_complete(
        provider="openai",
        api_key=key,
        model=model,
    )
    result.update(_publish_answer(question, result["text"], provider="openai", model=model))
    return result


def answer_via_deepseek() -> dict[str, Any]:
    key = deepseek_api_key()
    if not key:
        raise AnswerProviderError(
            "ANSWER_PROVIDER=deepseek, но DEEPSEEK_API_KEY не задан в .env"
        )
    question = last_interviewer_line() or ""
    model = deepseek_answer_model()
    result = _chat_complete(
        provider="deepseek",
        api_key=key,
        model=model,
        base_url=deepseek_api_base(),
    )
    result.update(_publish_answer(question, result["text"], provider="deepseek", model=model))
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
    from .cursor_bridge import answer_last_question

    return answer_last_question()
