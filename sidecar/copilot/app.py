from __future__ import annotations

import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone

import rumps

from .config import (
    ANSWERS_PATH,
    DATA_DIR,
    answer_pause_audio,
    answer_provider,
    audio_device_hint_interviewer,
    audio_device_hint_self,
    audio_listen_interviewer,
    audio_listen_self,
    cursor_agent_fresh_each_run,
    cursor_api_key,
    terminal_show_interviewer_stt,
)
from .answer_provider import AnswerProviderError, dispatch_answer
from .terminal_display import print_interview_answer
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
from .terminal_display import print_interviewer_transcript
from .shutdown import shutdown_resources, suppress_resource_tracker_warning
from .instance import SidecarLock
from .audio_devices import AudioDeviceNotFoundError
from .listener import AudioListener
from .main_thread import run_on_main
from .notify import notify
from .runtime_macos import ensure_info_plist
from .transcript import append_line, last_interviewer_line

HOTKEY = "<cmd>+<enter>"


class CopilotApp(rumps.App):
    def __init__(self, lock: SidecarLock) -> None:
        super().__init__("CP", quit_button=None)
        self._lock = lock
        self.session_active = False
        self._sdk_busy = False
        self._hotkey_listener = None
        self._resume_listening_after_sdk = False
        self._audio_interviewer = AudioListener(
            speaker="interviewer",
            device_hint=audio_device_hint_interviewer(),
            label="интервьюер",
            on_transcript=self._on_transcript_interviewer,
        )
        self._audio_self = AudioListener(
            speaker="self",
            device_hint=audio_device_hint_self(),
            label="я",
            on_transcript=self._on_transcript_self,
        )
        self.menu = [
            rumps.MenuItem("Статус: ожидание", callback=None),
            None,
            rumps.MenuItem("Начать интервью", callback=self.on_start),
            rumps.MenuItem("Закончить интервью", callback=self.on_stop),
            rumps.MenuItem("Привязать chatId Agents…", callback=self.on_bind_chat),
            rumps.MenuItem("Сбросить привязку chatId", callback=self.on_clear_chat_bind),
            None,
            rumps.MenuItem("Добавить реплику интервьюера…", callback=self.on_add_interviewer),
            rumps.MenuItem("Добавить мою реплику…", callback=self.on_add_self),
            None,
            rumps.MenuItem("Начать прослушивание (интервьюер + я)", callback=self.on_listen_start),
            rumps.MenuItem("Остановить прослушивание", callback=self.on_listen_stop),
            None,
            rumps.MenuItem(f"Ответ на последний вопрос ({HOTKEY})", callback=self.on_answer),
            rumps.MenuItem("Отменить SDK запрос", callback=self.on_cancel_sdk),
            None,
            rumps.MenuItem("Открыть data/transcript.md", callback=self.on_open_transcript),
            rumps.MenuItem("Открыть последний ответ", callback=self.on_open_last_answer),
            rumps.MenuItem("Открыть Cursor-агента", callback=self.on_open_cursor_agent),
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

    def on_start(self, _: object) -> None:
        from .stt import warmup_local_model

        self.session_active = True
        set_interview_active(True)
        self._set_status("интервью")
        warmup_local_model()
        self._start_hotkey()
        bound = resolve_bound_chat_id()
        hint = (
            f"Привязан чат {bound[:8]}…"
            if bound
            else "Создай агента в Cursor (New Agent), при желании привяжи chatId"
        )
        notify(
            "Copilot",
            "Интервью",
            f"⌘↩ → ответ в терминале. {hint}",
        )

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

    def _on_transcript_interviewer(self, text: str) -> None:
        if interview_active() and terminal_show_interviewer_stt():
            print_interviewer_transcript(text)
        append_line("interviewer", text)

    def _on_transcript_self(self, text: str) -> None:
        line = append_line("self", text)

        def show() -> None:
            notify("Транскрипт", "Я", line[:100])

        run_on_main(show)

    def _stop_all_audio(self) -> None:
        self._audio_interviewer.stop()
        self._audio_self.stop()

    def _audio_any_running(self) -> bool:
        return self._audio_interviewer.running or self._audio_self.running

    def _pause_audio_for_sdk(self) -> None:
        self._resume_listening_after_sdk = self._audio_any_running()
        self._stop_all_audio()

    def _resume_audio_if_needed(self) -> None:
        if not self._resume_listening_after_sdk:
            return
        self._resume_listening_after_sdk = False
        ok_lines, err_lines = self._start_listening_channels()
        if ok_lines:
            status = ok_lines[0] if len(ok_lines) == 1 else f"{len(ok_lines)} канала"
            self._set_status(f"слушаю ({status})")
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
        return ok_lines, err_lines

    def on_listen_start(self, _: object) -> None:
        self._resume_listening_after_sdk = False
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
        self._stop_all_audio()
        if self.session_active:
            self._set_status("интервью")
        else:
            self._set_status("ожидание")
        notify("STT", "Остановлено", "Прослушивание выключено")

    def on_stop(self, _: object) -> None:
        if self._sdk_busy:
            cancel_active_sdk()
            self._sdk_busy = False
        self._resume_listening_after_sdk = False
        self.session_active = False
        set_interview_active(False)
        self._stop_all_audio()
        self._stop_hotkey()
        append_line("interviewer", "[система] sidecar: сессия остановлена")
        self._set_status("ожидание")
        notify("Copilot", "Сессия", "Остановлена")

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
        if not self._sdk_busy:
            notify("Copilot", "SDK", "Нет активного запроса.")
            return
        if cancel_active_sdk():
            self._sdk_busy = False
            self._set_status("интервью" if self.session_active else "ожидание")
            notify("Copilot", "Отменено", "Запрос к SDK прерван.")
            self._resume_audio_if_needed()
        else:
            notify("Copilot", "SDK", "Запрос уже завершился.")

    def on_answer(self, _: object) -> None:
        if self._sdk_busy:
            notify("Copilot", "Подожди", "Уже идёт запрос к SDK (⌘↩ или «Отменить SDK»).")
            return
        if not last_interviewer_line():
            rumps.alert("Нет вопроса", "Добавь реплику [Интервьюер] в транскрипт.")
            return
        self._sdk_busy = True
        if answer_pause_audio():
            self._pause_audio_for_sdk()
        provider = answer_provider()
        label = {
            "openai": "OpenAI",
            "deepseek": "DeepSeek",
            "cursor": "Cursor",
        }.get(provider, provider)
        self._set_status(f"генерация ({label})…")
        log("[copilot] answer: provider=", provider)
        threading.Thread(target=self._answer_worker, daemon=True).start()

    def _answer_worker(self) -> None:
        try:
            result = dispatch_answer()
            text = (result.get("text") or result.get("raw") or "").strip()
            question = last_interviewer_line() or ""
            provider = result.get("provider") or answer_provider()
            model = result.get("model") or ""
            if text and question and not result.get("terminal"):
                print_interview_answer(
                    question, text, provider=provider, model=model
                )
            preview = text[:500] + ("…" if len(text) > 500 else "")

            def on_ok() -> None:
                self._sdk_busy = False
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
                self._sdk_busy = False
                rumps.alert("Ошибка ответа", str(e))
                self._set_status("интервью" if self.session_active else "ожидание")
                self._resume_audio_if_needed()

            run_on_main(on_err)

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
        set_interview_active(False)
        try:
            cancel_active_sdk()
        except Exception:
            pass
        self._sdk_busy = False
        self._stop_all_audio()
        self._stop_hotkey()
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

            listener = keyboard.GlobalHotKeys({HOTKEY: on_activate})
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
copilot — macOS menubar sidecar

Запуск:
  source .venv/bin/activate   # или: source scripts/activate-venv.sh
  copilot

После старта в menubar справа появится «CP». Терминал «молчит» — это нормально, процесс работает.
Остановка: меню «CP» → Выход (надёжнее, чем Ctrl+C). Зависший процесс: kill $(cat data/sidecar.lock)
Повторный запуск, пока sidecar жив, завершится с ошибкой.

Проверка, что вызывается наш бинарник:
  which copilot   # должен быть …/_copilot/.venv/bin/copilot
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
        "Терминал занят, пока sidecar работает. Выход: CP → Выход "
        "(Ctrl+C может не сработать в GUI-режиме).",
        flush=True,
    )
    print(
        "[copilot] CP → Начать интервью; ⌘↩ → ответ в этом терминале "
        "(+ data/last-answer.md)",
        flush=True,
    )

    def _quit_on_signal(*_args: object) -> None:
        cancel_active_sdk()
        shutdown_resources()
        lock.release()
        print("\nВыход (Ctrl+C).", flush=True)
        os._exit(0)

    signal.signal(signal.SIGINT, _quit_on_signal)
    signal.signal(signal.SIGTERM, _quit_on_signal)

    try:
        CopilotApp(lock).run()
    except Exception as exc:
        lock.release()
        print(f"Ошибка запуска sidecar: {exc}", file=sys.stderr, flush=True)
        return 1
    lock.release()
    return 0
