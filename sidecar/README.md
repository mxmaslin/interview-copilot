# Copilot sidecar

macOS menubar **CP**: с запуска `copilot` — сессия интервью, `⌘↩` / `⌘G`, сброс транскрипта. STT и Telegram — по пунктам меню. Hotkeys: **`⌘⌃⇧4`** (очередь скринов). **⌘↩** и скрины параллельно при `deepseek` + `cursor` для vision.

Доки: [copilot-workflow.md](../docs/copilot-workflow.md), [audio-setup.md](../docs/audio-setup.md), [telegram-input.md](../docs/telegram-input.md), [screenshot-solve.md](../docs/screenshot-solve.md).

Зависший процесс: `../scripts/kill-sidecar.sh`.

```bash
pip install -e ".[audio,openai]"
copilot   # из Terminal.app, не из терминала Cursor
```
