# Copilot sidecar

macOS menubar **CP**: с запуска `copilot` — сессия интервью, `⌘↩` / `⌘G`, сброс транскрипта. **Rolling STT** (`STT_ROLLING=1`): live-текст в терминал по ходу речи, финал в `data/transcript.md`. STT и Telegram — по пунктам меню. Hotkeys: **`⌘⌃⇧4`** (очередь скринов). **⌘↩** и скрины параллельно при `deepseek` + `cursor` для vision.

Доки: [copilot-workflow.md](../docs/copilot-workflow.md), [voice-pipeline.md](../docs/voice-pipeline.md), [audio-setup.md](../docs/audio-setup.md), [telegram-input.md](../docs/telegram-input.md), [screenshot-solve.md](../docs/screenshot-solve.md).

Тесты: `pytest tests -q` (fixtures STT в `tests/fixtures/stt/`).

Зависший процесс: `../scripts/kill-sidecar.sh`.

```bash
pip install -e ".[audio,openai]"
copilot   # из Terminal.app, не из терминала Cursor
```
