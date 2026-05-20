from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone

import rumps

logger = logging.getLogger(__name__)

from .config import (
    ANSWERS_PATH,
    DATA_DIR,
    answer_auto_delay_sec,
    answer_auto_enabled,
    answer_barge_in_speakers,
    answer_pause_audio,
    answer_provider,
    stt_live_min_words,
    audio_device_hint_interviewer,
    audio_device_hint_self,
    audio_listen_interviewer,
    audio_listen_self,
    cursor_agent_fresh_each_run,
    cursor_api_key,
    screenshot_solve_enabled,
    telegram_input_enabled,
    terminal_show_interviewer_stt,
    terminal_show_self_stt,
)
from .answer_provider import dispatch_answer
from .clipboard_watcher import ClipboardScreenshotWatcher
from .screenshot_queue import ScreenshotJob, ScreenshotQueue
from .screenshot_solve import (
    AnswerProviderError,
    screenshot_provider_hint,
    solve_screenshot_png,
)
from .terminal_display import (
    clear_self_transcript_live,
    print_interview_answer,
    print_interviewer_transcript,
    print_interviewer_transcript_live,
    print_self_transcript,
    print_self_transcript_live,
)
from .cursor_bridge import (
    CursorBridgeError,
    bind_user_chat,
    cancel_active_sdk,
    open_agent_in_cursor,
    reset_agent_state,
)
from .cursor_ide_chat import (
    BIND_HELP,
    chat_is_bound,
    resolve_bound_chat_id,
    sync_env_chat_binding,
)
from .interview_quiet import interview_active, log, set_interview_active
from .stt_filter import is_stt_hallucination
from .stt_live import (
    is_stt_noise_chunk,
    live_question_supersedes_file,
    sanitize_live_transcript,
)
from .shutdown import shutdown_resources, suppress_resource_tracker_warning
from .instance import SidecarLock
from .audio_devices import AudioDeviceNotFoundError
from .listener import AudioListener
from .telegram_input import TelegramInputError, TelegramInterviewerInput
from .main_thread import run_on_main
from .answer_turn import bind_answer_generation, next_answer_generation
from .pipeline_timing import begin_answer, finish_answer, note_stt_final, peek_timing_record
from .notify import notify
from .runtime_macos import ensure_info_plist
from .session_archive import end_session, record_answer_turn, start_session
from .transcript import (
    answer_self_questions_active,
    append_line,
    commit_interviewer_text_now,
    commit_self_text_now,
    clear_dialogue,
    flush_pending_self_line,
    pending_self_utterance,
    last_answer_line,
    last_answer_target,
    last_answer_target_for_speaker,
    last_self_question,
    merge_rolling_transcript,
    call_mic_muted_effective,
    init_call_mic_muted_from_disk,
    pin_answer_speaker,
    pin_answer_target,
    set_on_self_line_committed,
    reset_call_mic_muted,
    set_call_mic_muted_runtime,
)

HOTKEY = "<cmd>+<enter>"  # pynput GlobalHotKeys
HOTKEY_CLEAR = "<cmd>+g"
HOTKEY_LABEL = "⌘↩"
HOTKEY_CLEAR_LABEL = "⌘G"


class CopilotApp(rumps.App):
    def __init__(self, lock: SidecarLock) -> None:
        super().__init__("CP", quit_button=None)
        self._lock = lock
        self.session_active = False
        self._answer_busy = False
        self._answer_source = "hotkey"
        self._answer_generation = 0
        self._hotkey_listener = None
        self._clipboard_watcher: ClipboardScreenshotWatcher | None = None
        self._screenshot_queue = ScreenshotQueue(
            process=self._process_screenshot_job,
            on_busy_change=self._on_screenshot_busy_change,
            on_status=self._set_status_from_queue,
        )
        self._listening_active = False
        self._sdk_pause_depth = 0
        self._auto_answer_timer: threading.Timer | None = None
        self._auto_answer_timer_lock = threading.Lock()
        self._auto_answer_speaker: str | None = None
        self._rolling_interviewer: list[str] = []
        self._rolling_self: list[str] = []
        self._audio_interviewer = AudioListener(
            speaker="interviewer",
            device_hint=audio_device_hint_interviewer(),
            label="интервьюер",
            on_transcript=self._on_transcript_interviewer,
            on_speech_start=lambda: self._on_speech_barge_in("interviewer"),
        )
        self._audio_self = AudioListener(
            speaker="self",
            device_hint=audio_device_hint_self(),
            label="я",
            on_transcript=self._on_transcript_self,
            on_speech_start=lambda: self._on_speech_barge_in("self"),
        )
        self._telegram = TelegramInterviewerInput(
            on_message=self._on_transcript_interviewer
        )
        set_on_self_line_committed(
            lambda: self._schedule_auto_answer(speaker="self")
        )
        self.menu = [
            rumps.MenuItem("Статус: ожидание", callback=None),
            None,
            rumps.MenuItem("Начать прослушивание (интервьюер + я)", callback=self.on_listen_start),
            rumps.MenuItem("Остановить прослушивание", callback=self.on_listen_stop),
            None,
            rumps.MenuItem(
                f"Ответ на последний вопрос ({HOTKEY_LABEL})",
                callback=self.on_answer,
            ),
            rumps.MenuItem(
                "Микрофон на созвоне выкл (свои вопросы)",
                callback=self.on_toggle_call_mic_muted,
            ),
            rumps.MenuItem(
                f"Очистить транскрипт ({HOTKEY_CLEAR_LABEL})",
                callback=self.on_clear_transcript,
            ),
            rumps.MenuItem(
                "Решить скриншот из буфера (⌘⌃⇧4)",
                callback=self.on_screenshot_solve,
            ),
            None,
            rumps.MenuItem("Открыть data/transcript.md", callback=self.on_open_transcript),
            rumps.MenuItem("Открыть последний ответ", callback=self.on_open_last_answer),
            rumps.MenuItem(
                "Открыть ответ по скриншоту",
                callback=self.on_open_last_screenshot_answer,
            ),
            None,
            rumps.MenuItem("Выход", callback=self.on_quit),
        ]

    @property
    def status_item(self) -> rumps.MenuItem:
        return self.menu["Статус: ожидание"]

    def _set_status(self, text: str) -> None:
        self.status_item.title = f"Статус: {text}"

    @rumps.timer(0.5)
    def _process_signals(self, _: object) -> None:
        """Lets Python deliver SIGINT while NSApplication runs."""
        pass

    @rumps.timer(0.5)
    def _boot_bindings(self, timer: rumps.Timer) -> None:
        timer.stop()
        if cursor_agent_fresh_each_run():
            reset_agent_state()
        cid = sync_env_chat_binding()
        if cid:
            log("[copilot] chatId из .env:", cid)
        if screenshot_solve_enabled():
            self._start_clipboard_watcher()
        if telegram_input_enabled():
            self._start_telegram_input()
        init_call_mic_muted_from_disk()
        self._sync_call_mic_menu_state()
        from .session_warmup import warmup_session

        warmup_session()
        self._begin_interview(silent=True)

    def _clear_rolling_stt_buffers(self) -> None:
        for attr in ("_rolling_interviewer", "_rolling_self"):
            buf = getattr(self, attr, None)
            if buf is not None:
                buf.clear()

    def _begin_interview(self, *, silent: bool = False) -> None:
        clear_dialogue()
        self._clear_rolling_stt_buffers()
        start_session()
        self.session_active = True
        set_interview_active(True)
        self._set_status("интервью")
        self._start_hotkey()
        if silent:
            log("[copilot] сессия интервью (⌘↩, ⌘G); transcript сброшен")
            return
        bound = resolve_bound_chat_id()
        hint = (
            f"Привязан чат {bound[:8]}…"
            if bound
            else "Создай агента в Cursor (New Agent), при желании привяжи chatId"
        )
        notify("Copilot", "Интервью", f"⌘↩ ответ. ⌘G очистить. {hint}"[:180])

    def _end_interview_session(self) -> None:
        self._cancel_auto_answer_timer()
        if self._answer_busy or self._screenshot_active():
            cancel_active_sdk()
        self._answer_busy = False
        self._listening_active = False
        self._sdk_pause_depth = 0
        self.session_active = False
        set_interview_active(False)
        self._stop_all_audio()
        self._stop_hotkey()
        archived = end_session()
        if archived:
            log("[copilot] сессия сохранена:", archived)

    def on_bind_chat(self, _: object) -> None:
        w = rumps.Window(
            "В Cursor: Agents → _copilot → **New Agent**.\n\n"
            "chatId (UUID): из `cursor agent create-chat` в терминале "
            "или скопируй из контекста чата.\n\n"
            "Вставь UUID:",
            title="Привязать Agents-чат",
            default_text=resolve_bound_chat_id() or "",
            ok="Привязать",
            cancel="Отмена",
            dimensions=(420, 160),
        )
        resp = w.run()
        if not resp.clicked:
            return
        raw = (resp.text or "").strip()
        if not raw:
            return
        try:
            result = bind_user_chat(raw)
            notify("Copilot", "Привязано", result["chatId"][:36])
        except CursorBridgeError as e:
            rumps.alert("Ошибка", str(e))

    def on_clear_chat_bind(self, _: object) -> None:
        reset_agent_state()
        notify("Copilot", "Сброшено", "Привязка chatId удалена")

    def _start_telegram_input(self) -> str:
        if not telegram_input_enabled():
            return ""
        try:
            status = self._telegram.start()
            logger.info("[copilot] Telegram: %s", status)
            log("[copilot] Telegram:", status)
            return status[:80]
        except TelegramInputError as e:
            log("[copilot] Telegram WARN:", e)
            notify("Telegram", "Не запущен", str(e)[:120])
            return ""

    def _stop_telegram_input(self) -> None:
        self._telegram.stop()

    def _on_transcript_interviewer(self, text: str, *, final: bool = True) -> None:
        def apply() -> None:
            if not final:
                chunk = (text or "").strip()
                if not chunk or is_stt_noise_chunk(chunk):
                    return
                self._rolling_interviewer.append(text)
                if (
                    interview_active()
                    and terminal_show_interviewer_stt()
                    and self._live_ready_for_display("interviewer")
                ):
                    print_interviewer_transcript_live(
                        self._merged_rolling("interviewer"), final=False
                    )
                return
            merged = merge_rolling_transcript(self._rolling_interviewer, text)
            self._rolling_interviewer.clear()
            note_stt_final("interviewer")
            if interview_active() and terminal_show_interviewer_stt():
                print_interviewer_transcript_live(merged, final=True)
            if append_line("interviewer", merged):
                self._schedule_auto_answer(speaker="interviewer")

        run_on_main(apply)

    def _on_transcript_self(self, text: str, *, final: bool = True) -> None:
        def apply() -> None:
            if not final:
                chunk = (text or "").strip()
                if not chunk or is_stt_noise_chunk(chunk):
                    return
                self._rolling_self.append(text)
                if (
                    interview_active()
                    and terminal_show_self_stt()
                    and self._live_ready_for_display("self")
                ):
                    print_self_transcript_live(
                        self._merged_rolling("self"), final=False
                    )
                return
            merged = merge_rolling_transcript(self._rolling_self, text)
            self._rolling_self.clear()
            note_stt_final("self")
            line = append_line("self", merged)
            if not line:
                pending = pending_self_utterance()
                if pending and interview_active() and terminal_show_self_stt():
                    print_self_transcript_live(f"{pending} …", final=False)
                elif interview_active() and terminal_show_self_stt():
                    clear_self_transcript_live()
                return
            shown = line.replace("[Я]:", "", 1).strip()
            if interview_active() and terminal_show_self_stt():
                print_self_transcript_live(shown, final=True)
            notify("Транскрипт", "Я", shown[:100])
            self._schedule_auto_answer(speaker="self")

        run_on_main(apply)

    def _merged_rolling(self, speaker: str) -> str:
        buf = self._rolling_self if speaker == "self" else self._rolling_interviewer
        return sanitize_live_transcript(
            merge_rolling_transcript(list(buf), "").strip()
        )

    def _live_ready_for_display(self, speaker: str) -> bool:
        """Не спамить терминал односложным live (voice-agent partial UX)."""
        min_words = stt_live_min_words()
        if min_words <= 0:
            return True
        merged = self._merged_rolling(speaker)
        if not merged:
            return False
        return len(merged.split()) >= min_words

    def _resolve_hotkey_answer_target(self) -> tuple[str, str] | None:
        """⌘↩: приоритет live rolling над устаревшей строкой в transcript.md."""
        flush_pending_self_line()
        file_target = last_answer_target()
        file_q = file_target[0] if file_target else None

        self_live = self._merged_rolling("self")
        if self_live and live_question_supersedes_file(file_q, self_live):
            line = commit_self_text_now(self_live, force=True)
            if line:
                self._rolling_self.clear()
                clear_self_transcript_live()
                return (line.replace("[Я]:", "", 1).strip(), "self")

        iv_live = self._merged_rolling("interviewer")
        if iv_live and live_question_supersedes_file(file_q, iv_live):
            line = commit_interviewer_text_now(iv_live, force=True)
            if line:
                self._rolling_interviewer.clear()
                return (line.replace("[Интервьюер]:", "", 1).strip(), "interviewer")

        if self_live and not is_stt_hallucination(self_live):
            line = commit_self_text_now(self_live, force=True)
            if line:
                self._rolling_self.clear()
                clear_self_transcript_live()
                return (line.replace("[Я]:", "", 1).strip(), "self")

        return file_target

    def _stop_all_audio(self) -> None:
        self._audio_interviewer.stop()
        self._audio_self.stop()

    def _audio_any_running(self) -> bool:
        return self._audio_interviewer.running or self._audio_self.running

    def _pause_audio_for_sdk(self) -> None:
        """Пауза STT на время SDK; вложенные вызовы (⌘↩ + скрин) — счётчик."""
        self._sdk_pause_depth += 1
        self._stop_all_audio()

    def _resume_audio_if_needed(self) -> None:
        if self._sdk_pause_depth > 0:
            self._sdk_pause_depth -= 1
        if self._sdk_pause_depth > 0:
            return
        if not self._listening_active or not self.session_active:
            return
        ok_lines, err_lines = self._start_listening_channels()
        if ok_lines:
            status = ok_lines[0] if len(ok_lines) == 1 else f"{len(ok_lines)} канала"
            self._set_status(f"слушаю ({status})")
            if interview_active():
                sys.stdout.write(
                    "\n[copilot] STT возобновлено: " + "; ".join(ok_lines) + "\n\n"
                )
                sys.stdout.flush()
        elif err_lines:
            notify("STT", "Не удалось возобновить запись", err_lines[0][:120])

    def _start_listening_channels(self) -> tuple[list[str], list[str]]:
        from .stt import warmup_local_model

        warmup_local_model()
        channels: list[tuple[str, AudioListener]] = []
        if audio_listen_interviewer():
            channels.append(("Интервьюер", self._audio_interviewer))
        if audio_listen_self():
            channels.append(("Я", self._audio_self))
        if not channels:
            return [], []

        ok_lines: list[str] = []
        err_lines: list[str] = []
        for i, (title, listener) in enumerate(channels):
            if i > 0:
                time.sleep(0.35)
            try:
                dev = listener.start()
                ok_lines.append(f"{title}: {dev}")
            except AudioDeviceNotFoundError as e:
                err_lines.append(str(e))
            except Exception as e:
                err_lines.append(f"{title}: {e}")
        if ok_lines and interview_active():
            sys.stdout.write(
                "\n[copilot] слушаю: " + "; ".join(ok_lines) + "\n"
                "[copilot] BlackHole = звук звонка (оба голоса); "
                "«Я» = только микрофон (Brio)\n\n"
            )
            sys.stdout.flush()
        return ok_lines, err_lines

    def on_listen_start(self, _: object) -> None:
        self._sdk_pause_depth = 0
        self._listening_active = True
        ok_lines, err_lines = self._start_listening_channels()
        if not ok_lines:
            if err_lines:
                rumps.alert(
                    "Не удалось начать запись",
                    "\n".join(err_lines)
                    + "\n\nПроверь: pip install -e '.[audio]', ffmpeg, BlackHole + Brio — docs/audio-setup.md",
                )
            else:
                rumps.alert("STT", "Оба канала отключены (AUDIO_ENABLE_INTERVIEWER/SELF=0).")
            return

        status = ok_lines[0]
        if len(ok_lines) > 1:
            status = f"{len(ok_lines)} канала"
        self._set_status(f"слушаю ({status})")
        body = "\n".join(ok_lines)
        if err_lines:
            body += "\n" + "\n".join(err_lines)
        notify("STT", "Прослушивание", body[:160])

    def on_listen_stop(self, _: object) -> None:
        self._listening_active = False
        self._sdk_pause_depth = 0
        self._stop_all_audio()
        if self.session_active:
            self._set_status("интервью")
        else:
            self._set_status("ожидание")
        notify("STT", "Остановлено", "Прослушивание выключено")

    def _screenshot_active(self) -> bool:
        return (
            self._screenshot_queue.processing
            or self._screenshot_queue.pending_count() > 0
        )

    def on_add_interviewer(self, _: object) -> None:
        w = rumps.Window("Реплика интервьюера", "Текст", default_text="")
        w.add_buttons("OK", "Отмена")
        resp = w.run()
        if resp.clicked == 1 and resp.text.strip():
            line = append_line("interviewer", resp.text)
            notify("Транскрипт", "Добавлено", line[:80])

    def on_add_self(self, _: object) -> None:
        w = rumps.Window("Моя реплика", "Текст", default_text="")
        w.add_buttons("OK", "Отмена")
        resp = w.run()
        if resp.clicked == 1 and resp.text.strip():
            line = append_line("self", resp.text)
            notify("Транскрипт", "Добавлено", line[:80])

    def on_cancel_sdk(self, _: object) -> None:
        if not self._answer_busy and not self._screenshot_active():
            notify("Copilot", "SDK", "Нет активного запроса.")
            return
        cancelled = cancel_active_sdk()
        if self._answer_busy:
            self._answer_busy = False
        if cancelled:
            self._set_status("интервью" if self.session_active else "ожидание")
            notify("Copilot", "Отменено", "Запрос прерван.")
            self._resume_audio_if_needed()
        else:
            notify("Copilot", "SDK", "Запрос уже завершился.")

    def _start_clipboard_watcher(self) -> None:
        self._stop_clipboard_watcher()
        if not screenshot_solve_enabled():
            return
        self._screenshot_queue.start()
        watcher = ClipboardScreenshotWatcher(
            on_image=lambda: run_on_main(self._enqueue_screenshot, None),
        )
        watcher.start()
        self._clipboard_watcher = watcher

    def _stop_clipboard_watcher(self) -> None:
        watcher = self._clipboard_watcher
        self._clipboard_watcher = None
        if watcher is not None:
            watcher.stop()

    def _stop_screenshot_pipeline(self) -> None:
        self._stop_clipboard_watcher()
        self._screenshot_queue.stop()

    def _enqueue_screenshot(self, _: object = None) -> None:
        if not self._screenshot_queue.enqueue_clipboard():
            notify("Copilot", "Скриншот", "В буфере нет изображения (⌘⌃⇧4).")

    def on_screenshot_solve(self, _: object) -> None:
        self._enqueue_screenshot()

    def _process_screenshot_job(self, job: ScreenshotJob) -> dict:
        prov = screenshot_provider_hint()
        log(f"[copilot] screenshot #{job.job_id}: provider={prov}")
        try:
            result = solve_screenshot_png(
                job.png_bytes,
                mime=job.mime,
                clipboard_cleared_at_capture=True,
            )
        except AnswerProviderError as e:
            log(f"[copilot] screenshot #{job.job_id} ERROR:", e)
            run_on_main(
                lambda: notify("Copilot", "Скриншот", str(e)[:160]),
                None,
            )
            if interview_active():
                sys.stdout.write(f"\n[copilot] скриншот #{job.job_id}: {e}\n\n")
                sys.stdout.flush()
            raise
        text = (result.get("text") or "").strip()
        if text:
            preview = text[:500] + ("…" if len(text) > 500 else "")
            run_on_main(lambda: self._log_answer(preview), None)
        return result

    def _on_screenshot_busy_change(self, busy: bool) -> None:
        def apply() -> None:
            if busy:
                self._pause_audio_for_sdk()
                prov = screenshot_provider_hint()
                self._set_status(f"скриншот ({prov})…")
            else:
                if not self._answer_busy:
                    self._set_status("интервью" if self.session_active else "ожидание")
                self._resume_audio_if_needed()

        run_on_main(apply, None)

    def _set_status_from_queue(self, text: str) -> None:
        run_on_main(lambda: self._set_status(text), None)

    def _sync_call_mic_menu_state(self) -> None:
        menu = getattr(self, "menu", None)
        if not menu:
            return
        try:
            mic_item = menu["Микрофон на созвоне выкл (свои вопросы)"]
        except (KeyError, TypeError):
            return
        mic_item.state = 1 if call_mic_muted_effective() else 0

    def on_toggle_call_mic_muted(self, sender: rumps.MenuItem) -> None:
        sender.state = not bool(getattr(sender, "state", 0))
        muted = bool(sender.state)
        set_call_mic_muted_runtime(muted)
        if muted:
            notify(
                "Copilot",
                "Свои вопросы",
                "⌘↩ отвечает и на [Я] (микрофон на созвоне выключен).",
            )
        else:
            notify(
                "Copilot",
                "Свои вопросы",
                "⌘↩ снова только на [Интервьюер], если он есть в транскрипте.",
            )

    def on_clear_transcript(self, _: object) -> None:
        clear_dialogue()
        self._clear_rolling_stt_buffers()
        if interview_active():
            sys.stdout.write("\n[Транскрипт очищен — интервьюер и я]\n\n")
            sys.stdout.flush()
        else:
            notify("Copilot", "Транскрипт", "Реплики интервьюера и твои удалены")

    def _on_speech_barge_in(self, speaker: str) -> None:
        """Новая реплика во время генерации — отменить ответ (как повторный ⌘↩)."""
        if speaker not in answer_barge_in_speakers():
            return

        def apply() -> None:
            if not self._answer_busy:
                return
            log("[copilot] barge-in: речь", speaker, "— отмена ответа")
            timing = peek_timing_record()
            record_answer_turn(
                self._question_for_answer(source="hotkey") or "",
                "",
                provider=answer_provider(),
                source="barge-in",
                status="cancelled",
                timing=timing,
                speaker=speaker,
            )
            cancel_active_sdk()
            bind_answer_generation(None)
            self._answer_busy = False
            self._resume_audio_if_needed()

        run_on_main(apply, None)

    def _cancel_auto_answer_timer(self) -> None:
        lock = getattr(self, "_auto_answer_timer_lock", None)
        if lock is None:
            return
        with lock:
            timer = getattr(self, "_auto_answer_timer", None)
            self._auto_answer_timer = None
        if timer is not None:
            timer.cancel()

    def _schedule_auto_answer(self, *, speaker: str) -> None:
        if not answer_auto_enabled():
            return
        if not self.session_active:
            log("[copilot] auto-answer: пропуск (сессия не активна)")
            return
        if speaker not in ("interviewer", "self"):
            return
        self._cancel_auto_answer_timer()
        self._auto_answer_speaker = speaker
        log("[copilot] auto-answer: запланирован", speaker)
        delay = answer_auto_delay_sec()

        def fire() -> None:
            with self._auto_answer_timer_lock:
                self._auto_answer_timer = None
            self._start_answer(source="auto")

        if delay <= 0:
            fire()
            return
        timer = threading.Timer(delay, lambda: run_on_main(fire, None))
        timer.daemon = True
        with self._auto_answer_timer_lock:
            self._auto_answer_timer = timer
        timer.start()

    def on_answer(self, _: object) -> None:
        self._cancel_auto_answer_timer()
        self._auto_answer_speaker = None
        self._start_answer(source="hotkey")

    def _question_for_answer(self, *, source: str) -> str | None:
        if source == "auto" and self._auto_answer_speaker:
            target = last_answer_target_for_speaker(self._auto_answer_speaker)
            return target[0] if target else None
        return last_answer_line()

    def _start_answer(self, *, source: str = "hotkey") -> None:
        if self._answer_busy:
            if source == "hotkey":
                prev_q = self._question_for_answer(source="hotkey") or ""
                timing = peek_timing_record()
                record_answer_turn(
                    prev_q,
                    "",
                    provider=answer_provider(),
                    source="hotkey",
                    status="cancelled",
                    timing=timing,
                    speaker=(timing or {}).get("speaker") or "",
                )
                cancel_active_sdk()
                bind_answer_generation(None)
                self._answer_busy = False
                self._resume_audio_if_needed()
            else:
                log("[copilot] auto-answer: пропуск (уже идёт ответ)")
                return

        auto_pin = source == "auto" and self._auto_answer_speaker
        if auto_pin:
            pin_answer_speaker(self._auto_answer_speaker)

        answer_target: tuple[str, str] | None = None
        if source == "hotkey":
            answer_target = self._resolve_hotkey_answer_target()
        elif source == "auto" and self._auto_answer_speaker:
            t = last_answer_target_for_speaker(self._auto_answer_speaker)
            answer_target = t
        else:
            answer_target = last_answer_target()

        if answer_target:
            pin_answer_target(answer_target)
        question = answer_target[0] if answer_target else None
        if question and is_stt_hallucination(question):
            log("[copilot] ответ пропущен: STT-галлюцинация:", question[:80])
            if interview_active():
                sys.stdout.write(
                    "\n[copilot] вопрос похож на мусор STT (эхо prompt / «Смешка») — "
                    "ответ не запущен; дождись финала или ⌘G\n\n"
                )
                sys.stdout.flush()
            if auto_pin:
                pin_answer_speaker(None)
            return
        if not question:
            if auto_pin:
                pin_answer_speaker(None)
            if call_mic_muted_effective():
                hint = (
                    "Сначала твоя реплика [Я] (Начать прослушивание + микрофон Brio). "
                    "Старый [Интервьюер] в транскрипте не используется — ⌘G при необходимости."
                )
                term_hint = (
                    "\n[copilot] Нет [Я] для ⌘↩ — включено «микрофон на созвоне выкл»\n"
                )
            elif answer_self_questions_active():
                hint = "Сначала реплика [Интервьюер] или [Я] (STT, Telegram, меню)."
                term_hint = (
                    "\n[copilot] Нет вопроса для ⌘↩ — дождись STT или ⌘G и новую реплику\n"
                )
            else:
                hint = "Сначала реплика [Интервьюер] (STT, Telegram или меню)."
                term_hint = (
                    "\n[copilot] Нет вопроса для ⌘↩ — дождись STT/Telegram "
                    "или ⌘G и новую реплику интервьюера\n"
                    "(микрофон мог записать только [Я] — включи «Микрофон на созвоне выкл» "
                    "или соло без [Интервьюер])\n\n"
                )
            notify("Copilot", "Нет вопроса", hint)
            if interview_active():
                sys.stdout.write(term_hint)
                sys.stdout.flush()
            if source == "auto":
                log("[copilot] auto-answer: нет вопроса для", self._auto_answer_speaker)
            return

        self._answer_source = source
        self._answer_generation = next_answer_generation()
        bind_answer_generation(self._answer_generation)
        self._answer_busy = True
        if source == "auto" and interview_active():
            sys.stdout.write(
                f"\n[copilot] авто-ответ ({self._auto_answer_speaker or '?'})…\n"
            )
            sys.stdout.flush()
        if answer_pause_audio():
            self._pause_audio_for_sdk()
        provider = answer_provider()
        label = {
            "openai": "OpenAI",
            "deepseek": "DeepSeek",
            "cursor": "Cursor",
        }.get(provider, provider)
        if self._screenshot_active():
            self._set_status(f"генерация ({label}) + скрин…")
            log("[copilot] answer: parallel with screenshot queue")
        else:
            self._set_status(f"генерация ({label})…")
        if source == "auto" and self._auto_answer_speaker:
            log(
                "[copilot] auto-answer:",
                self._auto_answer_speaker,
                "provider=",
                provider,
            )
        else:
            log("[copilot] answer: provider=", provider)
        threading.Thread(target=self._answer_worker, daemon=True).start()

    def _answer_worker(self) -> None:
        pin = self._auto_answer_speaker
        try:
            pin_answer_speaker(pin)
            target = last_answer_target()
            speaker_tag = target[1] if target else ""
            begin_answer(
                source=self._answer_source,
                provider=answer_provider(),
                speaker=speaker_tag,
            )
            result = dispatch_answer()
            text = (result.get("text") or result.get("raw") or "").strip()
            question = last_answer_line() or ""
            provider = result.get("provider") or answer_provider()
            model = result.get("model") or ""
            if text and question and not result.get("terminal"):
                print_interview_answer(
                    question, text, provider=provider, model=model
                )
            preview = text[:500] + ("…" if len(text) > 500 else "")

            def on_ok() -> None:
                finish_answer()
                self._answer_busy = False
                self._log_answer(preview)
                if result.get("cursor_agent_error") and not result.get(
                    "cursor_agent_pushed"
                ):
                    log("[copilot] mirror:", result["cursor_agent_error"])
                self._set_status("интервью" if self.session_active else "ожидание")
                self._resume_audio_if_needed()

            run_on_main(on_ok)
        except (CursorBridgeError, AnswerProviderError, Exception) as e:

            def on_err() -> None:
                finish_answer()
                self._answer_busy = False
                rumps.alert("Ошибка ответа", str(e))
                self._set_status("интервью" if self.session_active else "ожидание")
                self._resume_audio_if_needed()

            run_on_main(on_err)
        finally:
            pin_answer_speaker(None)
            pin_answer_target(None)
            bind_answer_generation(None)
            self._auto_answer_speaker = None

    def _log_answer(self, text: str) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with ANSWERS_PATH.open("a", encoding="utf-8") as f:
            f.write(f"\n--- {ts} ---\n{text}\n")

    def on_open_last_answer(self, _: object) -> None:
        from .answer_delivery import LAST_ANSWER_PATH, reveal_in_cursor

        if not LAST_ANSWER_PATH.exists():
            rumps.alert("Нет ответа", "Сначала запроси ответ (⌘↩).")
            return
        reveal_in_cursor(LAST_ANSWER_PATH)

    def on_open_last_screenshot_answer(self, _: object) -> None:
        from .answer_delivery import LAST_SCREENSHOT_ANSWER_PATH, reveal_in_cursor

        if not LAST_SCREENSHOT_ANSWER_PATH.exists():
            rumps.alert(
                "Нет ответа",
                "Сначала реши скриншот (⌘⌃⇧4 или пункт меню).",
            )
            return
        reveal_in_cursor(LAST_SCREENSHOT_ANSWER_PATH)

    def on_open_cursor_agent(self, _: object) -> None:
        if not chat_is_bound():
            rumps.alert("Нет привязки", BIND_HELP)
            return
        try:
            open_agent_in_cursor()
        except CursorBridgeError as e:
            rumps.alert("Cursor", str(e))

    def on_open_transcript(self, _: object) -> None:
        from .config import TRANSCRIPT_PATH

        TRANSCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not TRANSCRIPT_PATH.exists():
            TRANSCRIPT_PATH.write_text("# Interview transcript\n", encoding="utf-8")
        subprocess_open = __import__("subprocess")
        subprocess_open.run(["open", str(TRANSCRIPT_PATH)], check=False)

    def on_quit(self, _: object) -> None:
        reset_call_mic_muted()
        self._end_interview_session()
        try:
            cancel_active_sdk()
        except Exception:
            pass
        self._stop_telegram_input()
        self._stop_screenshot_pipeline()
        shutdown_resources()
        self._lock.release()
        rumps.quit_application()

    def _start_hotkey(self) -> None:
        self._stop_hotkey()
        try:
            from pynput import keyboard

            def on_activate() -> None:
                try:
                    run_on_main(self.on_answer, None)
                except Exception:
                    import traceback

                    traceback.print_exc()

            def on_clear() -> None:
                try:
                    run_on_main(self.on_clear_transcript, None)
                except Exception:
                    import traceback

                    traceback.print_exc()

            listener = keyboard.GlobalHotKeys(
                {HOTKEY: on_activate, HOTKEY_CLEAR: on_clear}
            )
            listener.start()
            self._hotkey_listener = listener
        except Exception as e:
            rumps.alert(
                "Hotkey недоступен",
                f"Дай Accessibility для Terminal/Python:\n{e}\n\n"
                f"Или жми пункт меню «Ответ на последний вопрос».",
            )

    def _stop_hotkey(self) -> None:
        listener = self._hotkey_listener
        self._hotkey_listener = None
        if listener is None:
            return
        try:
            listener.stop()
            join = getattr(listener, "join", None)
            if callable(join):
                join(timeout=1.0)
        except Exception:
            pass


_HELP = """\
copilot — macOS menubar sidecar (CP)

Запуск:
  source scripts/activate-venv.sh
  copilot                    # Terminal.app / iTerm

Сразу: сессия интервью, ⌘↩ / ⌘G, transcript сброшен.
STT: CP → «Начать прослушивание (интервьюер + я)».

Hotkeys:
  ⌘↩     — ответ на последний вопрос → терминал + data/last-answer.md
  ⌘G     — очистить transcript
  ⌘⌃⇧4   — скриншот в буфер → vision (SCREENSHOT_SOLVE_ENABLED=1 — авто)

Меню CP: прослушивание, ответ, микрофон на созвоне выкл, скрин, файлы, выход.
Подробнее: docs/copilot-workflow.md

Выход: CP → Выход или Ctrl+C. Зависший: ./scripts/kill-sidecar.sh

  which copilot   # …/_copilot/.venv/bin/copilot
"""


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print(_HELP, end="")
        return 0

    from .hf_hub import configure_hf_hub

    ensure_info_plist()
    suppress_resource_tracker_warning()
    configure_hf_hub()

    lock = SidecarLock()
    if not lock.acquire():
        pid = SidecarLock.holder_pid()
        msg = "Sidecar уже запущен — в menubar открой CP → Выход."
        if pid:
            msg += f" (PID {pid}, при необходимости: kill {pid})"
        print(msg, file=sys.stderr, flush=True)
        return 1

    print(
        "Copilot sidecar запущен. Иконка «CP» в menubar (справа). "
        "Сессия интервью активна. Выход: CP → Выход или Ctrl+C.",
        flush=True,
    )
    print(
        "[copilot] ⌘↩ ответ; ⌘G очистить transcript; "
        "⌘⌃⇧4 скриншот (SCREENSHOT_SOLVE_ENABLED=1 — авто); "
        "CP → Начать прослушивание для STT",
        flush=True,
    )

    app = CopilotApp(lock)

    def _quit_on_signal(*_args: object) -> None:
        print("\nВыход (Ctrl+C).", flush=True)
        run_on_main(app.on_quit, None)

    signal.signal(signal.SIGINT, _quit_on_signal)
    signal.signal(signal.SIGTERM, _quit_on_signal)

    try:
        app.run()
    except Exception as exc:
        lock.release()
        print(f"Ошибка запуска sidecar: {exc}", file=sys.stderr, flush=True)
        return 1
    lock.release()
    return 0
