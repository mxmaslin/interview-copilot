# Interview Copilot

macOS-приложение в menubar для собеседований (HR, техэтап, live coding): слушает созвон (STT), собирает транскрипт, по hotkey даёт ответ **строго на последний вопрос** в терминал. Опционально — vision по скриншоту задачи.

Репозиторий: [github.com/mxmaslin/interview-copilot](https://github.com/mxmaslin/interview-copilot)

## Что умеет

- **Rolling STT** — пока интервьюер говорит, в терминал идёт **live-текст** (~каждые 2 с); в `data/transcript.md` — **финальная** реплика после короткой паузы (`STT_ROLLING=1`, см. [audio-setup.md](docs/audio-setup.md)).
- **Транскрипт** звонка — `[Интервьюер]:` (BlackHole) и `[Я]:` (микрофон).
- **Авто-ответ** — после финальной реплики STT (`ANSWER_AUTO=1`); `⌘↩` прерывает и перезапускает.
- **Ответ на последний вопрос** — `⌘↩` или **CP** → стрим в терминал + `data/last-answer.md`.
- **Скриншот задачи** — `⌘⌃⇧4` (буфер) → vision-решение без лишней «теории».
- **Telegram** — текстовые вопросы интервьюера в тот же транскрипт (см. [docs/telegram-input.md](docs/telegram-input.md)).
- **Резюме** — `context/resume.md` для фактов об опыте (локально, не в git).
- **Архив сессий** — `data/sessions/<дата>/`: транскрипт, `review.md`, `turns.jsonl` (источник, статус, тайминги) для разбора качества ответов (gitignored).
- **Voice pipeline** — endpointing, тайминги (`COPILOT_TIMING`), glossary STT (Kafka, Redis, …), turn-taking при повторном ⌘↩ — см. [voice-pipeline.md](docs/voice-pipeline.md).

Провайдер ответа: DeepSeek / OpenAI / Cursor SDK — через `.env` (`ANSWER_PROVIDER`).

## Требования

- **macOS** (захват аудио и menubar)
- Python **3.11+**, Node **18+** (для Cursor SDK и скриншотов)
- Для звонка: [BlackHole](https://existential.audio/blackhole/) + Multi-Output (см. [docs/audio-setup.md](docs/audio-setup.md))
- API-ключи в `.env` (шаблон — `.env.example`)

## Установка

```bash
git clone https://github.com/mxmaslin/interview-copilot.git
cd interview-copilot

cp .env.example .env
# CURSOR_API_KEY — https://cursor.com/dashboard/integrations
# DEEPSEEK_API_KEY — если ANSWER_PROVIDER=deepseek

cd scripts/cursor-agent && npm install && cd ../..

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e "./sidecar[audio,openai]"
```

Опционально для локального STT без облака:

```bash
brew install ffmpeg
# в .env: STT_PROVIDER=local (по умолчанию faster-whisper)
```

## Запуск

Запускай **`copilot` в Terminal.app или iTerm**, не во встроенном терминале Cursor (меньше конфликтов с IDE при vision/SDK).

```bash
source scripts/activate-venv.sh
copilot
```

В menubar появится **CP**. Сразу доступны `⌘↩` (ответ) и `⌘G` (очистить транскрипт). Для распознавания речи: **CP → Начать прослушивание**.

Подробная шпаргалка: [docs/copilot-workflow.md](docs/copilot-workflow.md) · `copilot --help`

### Типичный сценарий на созвоне

1. Настроить аудио ([audio-setup.md](docs/audio-setup.md)) — BlackHole на выход Zoom/Meet/Telemost.
2. `copilot` → **Начать прослушивание**.
3. Интервьюер говорит → **live** в терминал по ходу; после паузы — строка в `data/transcript.md` (и авто-ответ, если включён).
4. **`⌘↩`** — ответ на последний вопрос (или дождись авто-ответа).
5. Задача на экране → **`⌘⌃⇧4`** → решение в терминал ([screenshot-solve.md](docs/screenshot-solve.md)).
6. Новый вопрос с чистого листа → **`⌘G`**.
7. Конец — **CP → Выход** или **Ctrl+C**.

### Меню CP (кратко)

| Действие | Назначение |
|----------|------------|
| Начать / остановить прослушивание | STT с микрофона и звонка |
| Ответ на последний вопрос (`⌘↩`) | LLM → терминал + `last-answer.md` |
| Очистить транскрипт (`⌘G`) | Сброс реплик в сессии |
| Решить скриншот | Vision по буферу |
| Микрофон на созвоне выкл | `⌘↩` на реплики `[Я]` (соло-режим) |
| Выход | Остановить sidecar |

### Hotkeys и Accessibility

- **`⌘↩`** — ответ · **`⌘G`** — очистка · **`⌘⌃⇧4`** — скрин в буфер (если включён watcher).
- **Системные настройки → Конфиденциальность → Универсальный доступ** — разрешить Terminal (или Python), из которого запущен `copilot`, иначе hotkeys не сработают.

Если процесс завис: `./scripts/kill-sidecar.sh`

## Конфигурация (`.env`)

```env
ANSWER_PROVIDER=deepseek          # deepseek | openai | cursor
DEEPSEEK_API_KEY=...
CURSOR_API_KEY=...                # скриншоты и ANSWER_PROVIDER=cursor

STT_PROVIDER=local
STT_LATENCY=balanced              # fast | balanced | quality
STT_ROLLING=1                     # транскрипт по ходу речи (~2 с), не после паузы
WHISPER_MODEL_SIZE=small          # fast/balanced; quality → large-v3
WHISPER_PROMPT_MODE=tech          # tech — собес; general — HR; interview — макс. prompt
WHISPER_GLOSSARY_FIXES=1          # кавка→Kafka, редис→Redis, …
COPILOT_TIMING=1                  # stt / llm_ttft / total после ответа
# AUDIO_PRESET=call               # пресет пауз VAD на созвоне
ANSWER_AUTO=1                     # ответ после STT; ⌘↩ — сразу
SCREENSHOT_SOLVE_ENABLED=1
# SCREENSHOT_ANSWER_PROVIDER=anthropic   # см. docs/screenshot-solve.md
TERMINAL_ANSWER_STREAM=1

AUDIO_INPUT_INTERVIEWER=BlackHole
AUDIO_INPUT_SELF=Brio             # подстрока имени твоего микрофона
```

Полный список переменных — в [.env.example](.env.example) и [AGENTS.md](AGENTS.md).

## Документация

| Тема | Файл |
|------|------|
| Menubar и hotkeys | [docs/copilot-workflow.md](docs/copilot-workflow.md) |
| Voice pipeline (STT, endpointing, тайминги) | [docs/voice-pipeline.md](docs/voice-pipeline.md) · [roadmap](docs/voice-pipeline-roadmap.md) |
| Словарь STT (кавка→Kafka, …) | [docs/stt-glossary.md](docs/stt-glossary.md) |
| Аудио (BlackHole, Zoom, Meet) | [docs/audio-setup.md](docs/audio-setup.md) |
| Telegram-ввод | [docs/telegram-input.md](docs/telegram-input.md) |
| Скриншоты / vision | [docs/screenshot-solve.md](docs/screenshot-solve.md) |
| Резюме и hh.ru | [docs/resume-context.md](docs/resume-context.md) |
| Секреты и публикация | [SECURITY.md](SECURITY.md) |

## Структура репозитория

```
sidecar/                 # Python: menubar, STT, ответы, скриншоты
scripts/cursor-agent/    # Node + @cursor/sdk (cursor / vision)
data/                    # transcript, sessions/, last-answer (gitignored)
context/                 # resume.md локально; в git — *.example
.cursor/rules/           # правила Cursor (copilot.mdc)
.cursor/skills/          # skill interview-copilot для агента в IDE
```

## Разработка и тесты

```bash
source .venv/bin/activate
pip install -e "./sidecar[audio,dev,openai]"
pytest sidecar/tests -q
```

CI: GitHub Actions (`.github/workflows/ci.yml`). Перед push — [SECURITY.md](SECURITY.md), `pytest sidecar/tests/test_repo_hygiene.py`.

## Ограничения

- Только **macOS**; один пользователь на машину (`data/sidecar.lock`).
- Ответы уходят в выбранный облачный API (DeepSeek/OpenAI/Cursor) — см. [SECURITY.md](SECURITY.md).
- Не e2e-тесты: реальный микрофон, live API, UI Cursor Agents.

Концепция и roadmap: [vision.md](vision.md).
