# Copilot sidecar

macOS menubar: STT, **Telegram-бот** (polling с запуска `copilot`), `data/transcript.md`. Hotkeys: `⌘↩`, `⌘G`, **`⌘⌃⇧4`** (очередь скринов). **⌘↩** и скрины параллельно при `ANSWER_PROVIDER=deepseek` + `SCREENSHOT_ANSWER_PROVIDER=cursor`. Зависший процесс: `../scripts/kill-sidecar.sh`.

Доки: `../docs/audio-setup.md`, `../docs/telegram-input.md`, `../docs/screenshot-solve.md`.

Опционально: Agents chatId (`cursor_ide_chat.py`), Cursor SDK (`scripts/cursor-agent`) для `ANSWER_PROVIDER=cursor`.

```bash
pip install -e ".[audio,openai]"
copilot   # из Terminal.app, не из терминала Cursor
```
