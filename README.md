# Copilot

Личный копилот для технических интервью: **спец-агент в Cursor** + **menubar sidecar** на macOS.

Подробнее: [vision.md](vision.md).

## Быстрый старт (MVP)

### 1. Cursor — спец-агент

1. Открой этот репозиторий в Cursor.
2. Правило **Copilot** (`.cursor/rules/copilot.mdc`) подключается автоматически — ответы на вопросы идут из sidecar/SDK (см. ниже).

### 2. API-ключ

```bash
cp .env.example .env
# Вставь CURSOR_API_KEY из https://cursor.com/dashboard/integrations
```

### 3. Node (Cursor SDK)

```bash
cd scripts/cursor-agent
npm install
```

### 4. Python (venv в корне проекта)

```bash
# из корня репозитория (Cursor подхватит .venv автоматически)
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e "./sidecar[audio]"
```

Интерпретатор и venv подхватываются автоматически (`.vscode/settings.json`): в **новом** терминале Cursor активируется `.venv`, `python` и `copilot` — из проекта.

После первого клона или смены настроек: **Reload Window** → новый терминал. Если venv ещё нет — создай по шагу 4 выше.

**pyenv:** в корне нет `.python-version` — иначе shims перехватывают `python` вместо `.venv`.

**Терминал как в Terminal.app (Powerlevel10k):**

1. `direnv allow` в корне (direnv уже в `~/.zshrc`).
2. **Reload Window** → новый терминал, профиль **zsh-login**.
3. Cursor **не** подменяет `ZDOTDIR` — грузится твой `~/.zshrc` + p10k. Логи direnv тихие (`~/.config/direnv/direnv.toml`).

Проверка: `typeset -f _p9k_precmd >/dev/null && echo p10k=ok` → `p10k=ok`.

Если иконки «ломаные» — шрифт `MesloLGS NF` в Cursor → Terminal.

### 5. Запуск

**Важно:** запускай `copilot` в **Terminal.app** (или iTerm), **не** во встроенном терминале Cursor. SDK дергает локальный Agent в IDE — вместе с sidecar это может подвесить Cursor; после force quit IDE снимай хвосты: `./scripts/kill-sidecar.sh`.

```bash
# из корня — лучше явно через venv (pyenv shims могут перехватить имя copilot)
source scripts/activate-venv.sh
copilot
# или
./scripts/run-sidecar.sh
# или
python -m copilot
```

**В терминале почти нет вывода** — sidecar это menubar-приложение; после старта смотри иконку **CP** справа в строке меню. Справка: `copilot --help`.

Если `which copilot` показывает `~/.pyenv/shims/copilot`:

```bash
source scripts/activate-venv.sh   # copilot: …/_copilot/.venv/bin/copilot
# или сразу:
./bin/copilot
# если which всё ещё shim — сброс кэша zsh:
hash -r && which copilot
```

Глобально `pip install` sidecar не нужен — только `pip install -e "./sidecar[audio]"` в `.venv`.

В menubar появится **CP**:

| Действие | Что делает |
|----------|------------|
| **Начать интервью** | Сессия + hotkey `⌘↩` |
| **Привязать chatId Agents…** | Опционально, если нужен `CURSOR_AGENT_MIRROR=1` |
| **Добавить реплику интервьюера** | Дописывает `[Интервьюер]:` в `data/transcript.md` |
| **Начать / остановить прослушивание** | Два входа (см. `.env`) |
| **Ответ на последний вопрос** (`⌘↩`) | Ответ в **терминале по чанкам** (`TERMINAL_ANSWER_STREAM`) + `data/last-answer.md` |
| **Открыть последний ответ** | Вручную открыть `last-answer.md` в Cursor |

### 6. Accessibility (для `⌘ + Enter`)

**Системные настройки → Конфиденциальность → Универсальный доступ** — разреши Terminal или Python, из которого запущен sidecar.

Если hotkey не работает — используй пункт меню **«Ответ на последний вопрос»**.

## Без SDK (только транскрипт)

1. **CP → Добавить реплику интервьюера…**
2. В Cursor: `@data/transcript.md` — «ответь на последний вопрос интервьюера»

## Структура

```
AGENTS.md                      # поведение спец-агента
.cursor/rules/copilot.mdc      # правило Copilot (alwaysApply)
scripts/cursor-agent/          # Node + @cursor/sdk
sidecar/                       # menubar + hotkey + транскрипт
data/transcript.md             # лог реплик
data/last-answer.md            # последний ответ (⌘↩)
data/answers.log               # архив ответов
data/agent-state.json          # опциональная привязка chatId Agents
context/                       # резюме / вакансия (опционально)
```

### Ответы (`.env`)

```env
ANSWER_PROVIDER=deepseek          # deepseek | openai | cursor
DEEPSEEK_API_KEY=...
CURSOR_API_KEY=...
# CURSOR_AGENT_MIRROR=0           # по умолчанию: только терминал, без cursor CLI
# CURSOR_OPEN_ANSWER_FILE=1       # открывать last-answer.md в Cursor
CURSOR_MODEL=composer-2
pip install -e "./sidecar[openai]"   # для DeepSeek/OpenAI
```

### Тесты (sidecar)

```bash
source .venv/bin/activate
pip install -e "./sidecar[dev,openai]"
pytest sidecar/tests -q
```

Покрыто: config, transcript, STT latency, streaming answers, audio, terminal_display, answer_delivery, cursor_bridge (45+ тестов). **Нет** e2e: DeepSeek, микрофон, `cursor agent`.

## Аудио (Zoom / Telemost / Meet)

Настройка BlackHole: **[docs/audio-setup.md](docs/audio-setup.md)**.

**STT по умолчанию — локальный Whisper** (`faster-whisper`, без ключей). Подходит для Mac M4 + 24 GB, модель `small`:

```bash
brew install ffmpeg
pip install -e ".[audio]"
# .env: STT_PROVIDER=local, WHISPER_MODEL_SIZE=small
```

Облако (опционально): `STT_PROVIDER=openai` + `pip install -e ".[audio,openai]"`.

## Дальше

- E2e-тесты SDK / DeepSeek (mock)
- Авто-`agent.send` при каждой реплике STT (сейчас только по ⌘↩)
