from __future__ import annotations

import threading

import pytest

import copilot.transcript as transcript
from copilot.endpointing import reset_final_debounce_for_tests


@pytest.fixture(autouse=True)
def _reset_endpointing_state() -> None:
    reset_final_debounce_for_tests()
    transcript.pin_answer_target(None)


@pytest.fixture(autouse=True)
def _isolated_call_mic_muted(tmp_path, monkeypatch) -> None:
    """Не читать data/call-mic-muted с диска пользователя между тестами."""
    monkeypatch.setattr(
        transcript, "CALL_MIC_MUTED_FLAG", tmp_path / "call-mic-muted"
    )
    transcript.set_call_mic_muted_runtime(False)


def test_append_line_interviewer() -> None:
    line = transcript.append_line("interviewer", "Что такое GIL?")

    assert line == "[Интервьюер]: Что такое GIL?"
    assert transcript.dialogue_lines() == ["[Интервьюер]: Что такое GIL?"]


def test_append_line_self(tmp_path, monkeypatch) -> None:

    line = transcript.append_line("self", "Отвечу про GIL")

    assert line == "[Я]: Отвечу про GIL"


def test_last_interviewer_line(tmp_path, monkeypatch) -> None:

    transcript.append_line("interviewer", "Первый вопрос")
    transcript.append_line("self", "Мой ответ")
    transcript.append_line("interviewer", "Второй вопрос")

    assert transcript.last_interviewer_line() == "Второй вопрос"


def test_last_interviewer_question_merges_consecutive(tmp_path, monkeypatch) -> None:
    import copilot.config as cfg

    monkeypatch.setattr(cfg, "answer_interviewer_merge_max", lambda: 10)

    transcript.append_line("interviewer", "Расскажи про GIL")
    transcript.append_line("interviewer", "и про asyncio")

    assert transcript.last_interviewer_question() == "Расскажи про GIL и про asyncio"


def test_last_interviewer_merge_capped(tmp_path, monkeypatch) -> None:
    import copilot.config as cfg

    monkeypatch.setattr(cfg, "answer_interviewer_merge_max", lambda: 2)

    for n in range(5):
        transcript.append_line("interviewer", f"seg{n}")

    assert transcript.last_interviewer_question() == "seg3 seg4"


def test_last_interviewer_question_stops_at_self(tmp_path, monkeypatch) -> None:

    transcript.append_line("interviewer", "Старый вопрос")
    transcript.append_line("self", "Ответ")
    transcript.append_line("interviewer", "Часть один")
    transcript.append_line("interviewer", "часть два")

    assert transcript.last_interviewer_question() == "Часть один часть два"


def test_clear_dialogue() -> None:
    transcript.append_line("interviewer", "Вопрос")
    transcript.append_line("self", "Ответ")
    transcript.clear_dialogue()

    assert transcript.dialogue_lines() == []
    assert transcript.last_interviewer_line() is None


def test_last_interviewer_skips_trailing_self(tmp_path, monkeypatch) -> None:

    transcript.append_line("interviewer", "Ну не надо.")
    transcript.append_line("self", "Ещё раз спросите")

    assert transcript.last_interviewer_line() == "Ну не надо."


def test_last_self_question_merges(tmp_path, monkeypatch) -> None:
    import copilot.config as cfg

    monkeypatch.setattr(cfg, "answer_self_merge_max", lambda: 2)
    monkeypatch.setattr(transcript, "call_mic_muted_effective", lambda: False)

    transcript.append_line("interviewer", "начало")
    transcript.append_line("self", "Что такое GIL")
    transcript.append_line("self", "и asyncio")

    assert transcript.last_self_question() == "Что такое GIL и asyncio"


def test_last_answer_target_solo_self(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "answer_self_questions_active", lambda: True)

    transcript.append_line("self", "Расскажи про Redis")

    assert transcript.last_answer_target() == ("Расскажи про Redis", "self")


def test_last_answer_target_interviewer_when_both(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "call_mic_muted_effective", lambda: False)
    monkeypatch.setattr(transcript, "answer_self_questions_active", lambda: True)

    transcript.append_line("interviewer", "Вопрос один")
    transcript.append_line("self", "Мой ответ")
    transcript.append_line("self", "Уточни про кэш")

    assert transcript.last_answer_target() == ("Уточни про cache", "self")


def test_call_mic_muted_only_latest_self_not_merged(tmp_path, monkeypatch) -> None:
    import copilot.config as cfg

    monkeypatch.setattr(cfg, "call_mic_muted_on_call", lambda: False)
    transcript.set_call_mic_muted_runtime(True)

    transcript.append_line("self", "Привет, слышишь меня?")
    transcript.append_line("self", "Расскажи, что знаешь про...")
    transcript.append_line("self", "Как твоё настроение?")

    assert transcript.last_answer_target() == ("Как твоё настроение?", "self")


def test_call_mic_muted_ignores_trailing_interviewer(tmp_path, monkeypatch) -> None:
    import copilot.config as cfg

    monkeypatch.setattr(cfg, "call_mic_muted_on_call", lambda: False)
    transcript.set_call_mic_muted_runtime(True)

    transcript.append_line("self", "Расскажи про asyncio")
    transcript.append_line("interviewer", "шум с BlackHole")

    assert transcript.last_answer_target() == ("Расскажи про asyncio", "self")


def test_self_overrides_spurious_interviewer(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "answer_self_questions_active", lambda: False)

    transcript.append_line("self", "Здравствуйте меня слышишь?")
    transcript.append_line("interviewer", "Сказать?")

    assert transcript.last_answer_target() == (
        "Здравствуйте меня слышишь?",
        "self",
    )


def test_real_interviewer_not_overridden_by_short_self(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "answer_self_questions_active", lambda: False)

    transcript.append_line("interviewer", "Расскажите про транзакции в PostgreSQL")
    transcript.append_line("self", "угу")

    assert transcript.last_answer_target() == (
        "Расскажите про транзакции в PostgreSQL",
        "interviewer",
    )


def test_last_answer_target_normal_interview(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(transcript, "answer_self_questions_active", lambda: False)

    transcript.append_line("interviewer", "Про GIL")
    transcript.append_line("self", "Мой вопрос себе")

    assert transcript.last_answer_target() == ("Про GIL", "interviewer")


def test_last_answer_target_call_mic_muted_prefers_self(
    tmp_path, monkeypatch
) -> None:
    import copilot.config as cfg

    monkeypatch.setattr(cfg, "call_mic_muted_on_call", lambda: False)
    transcript.set_call_mic_muted_runtime(True)

    transcript.append_line("interviewer", "Старый вопрос с созвона")
    transcript.append_line("self", "Что такое декоратор")

    assert transcript.last_answer_target() == ("Что такое декоратор", "self")


def test_answer_self_active_when_no_interviewer(
    tmp_path, monkeypatch
) -> None:

    import copilot.config as cfg

    monkeypatch.setattr(cfg, "answer_self_questions_mode", lambda: "auto")
    monkeypatch.setattr(cfg, "call_mic_muted_on_call", lambda: False)
    monkeypatch.setattr(cfg, "audio_listen_interviewer", lambda: True)

    transcript.append_line("self", "solo")
    assert transcript.answer_self_questions_active() is True


def test_last_interviewer_line_empty(tmp_path, monkeypatch) -> None:

    assert transcript.last_interviewer_line() is None


def test_clear_during_concurrent_append(tmp_path, monkeypatch) -> None:

    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def append_loop() -> None:
        try:
            barrier.wait(timeout=2)
            for i in range(40):
                transcript.append_line("interviewer", f"seg-{i}")
        except BaseException as e:
            errors.append(e)

    def clear_once() -> None:
        try:
            barrier.wait(timeout=2)
            transcript.clear_dialogue()
        except BaseException as e:
            errors.append(e)

    t1 = threading.Thread(target=append_loop)
    t2 = threading.Thread(target=clear_once)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not errors
    # Гонка append/clear: важно отсутствие исключений и целостность lock.
