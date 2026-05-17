# Copilot sidecar

macOS menubar: STT, `data/transcript.md`, hotkey `⌘↩`, ответ в **терминале** (см. `copilot/terminal_display.py`).

Опционально: привязка chatId Agents (`cursor_ide_chat.py`), SDK (`scripts/cursor-agent`) для `ANSWER_PROVIDER=cursor`.

```bash
pip install -e ".[audio,openai]"
copilot   # из Terminal.app, не из терминала Cursor
```
