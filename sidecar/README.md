# Copilot sidecar

macOS menubar: STT (`STT_LATENCY=fast`, Whisper `small`), `data/transcript.md`, hotkey `⌘↩`. Подряд `[Интервьюер]` без `[Я]` между ними = один вопрос. Ответ в **терминале по чанкам** (`TERMINAL_ANSWER_STREAM`).

Опционально: привязка chatId Agents (`cursor_ide_chat.py`), SDK (`scripts/cursor-agent`) для `ANSWER_PROVIDER=cursor`.

```bash
pip install -e ".[audio,openai]"
copilot   # из Terminal.app, не из терминала Cursor
```
