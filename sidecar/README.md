# Copilot sidecar

macOS menubar: STT (`STT_LATENCY=fast`, Whisper `small`), опционально **Telegram-бот** (текст), `data/transcript.md`. Hotkeys: `⌘↩`, `⌘G`, **`⌘⌃⇧4`** (скриншот → vision). При `ANSWER_PROVIDER=deepseek` скриншоты → **Cursor SDK**, если задан `CURSOR_API_KEY`. Зависший процесс: `../scripts/kill-sidecar.sh`.

Доки: `../docs/audio-setup.md`, `../docs/telegram-input.md`, `../docs/screenshot-solve.md`.

Опционально: Agents chatId (`cursor_ide_chat.py`), Cursor SDK (`scripts/cursor-agent`) для `ANSWER_PROVIDER=cursor`.

```bash
pip install -e ".[audio,openai]"
copilot   # из Terminal.app, не из терминала Cursor
```
