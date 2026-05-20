# Interview Copilot

macOS-приложение в menubar для собеседований (HR, техэтап, live coding): слушает созвон (STT), собирает транскрипт, по hotkey даёт ответ **строго на последний вопрос** в терминал. Опционально — vision по скриншоту задачи.

Репозиторий: [github.com/mxmaslin/interview-copilot](https://github.com/mxmaslin/interview-copilot)

## Что умеет

- **Rolling STT** — live-текст в терминал (~1.2 с); **финал** в RAM после паузы (файл `data/transcript.md` только при выходе или «Открыть транскрипт»). См. [audio-setup.md](docs/audio-setup.md).
- **Транскрипт** звонка — `[Интервьюер]:` (BlackHole) и `[Я]:` (микрофон).
- **Авто-ответ** — после финальной реплики в transcript (`ANSWER_AUTO=1`, без ⌘↩); `⌘↩` прерывает и перезапускает.
- **Фильтр мусора STT** — «Смешка», эхо Whisper prompt на тишине не уходят в transcript и не запускают ответ.
- **Ответ на последний вопрос** — `⌘↩` или **CP** → стрим в терминал + `data/last-answer.md`.
- **Скриншот задачи** — `⌘⌃⇧4` (буфер) → vision-решение без лишней «теории».
- **Telegram** — текстовые вопросы интервьюера в тот же транскрипт (см. [docs/telegram-input.md](docs/telegram-input.md)).
- **Резюме** — `context/resume.md` для фактов об опыте (локально, не в git).
- **Архив сессий** — `data/sessions/<дата>/`: транскрипт, `review.md`, `turns.jsonl` (источник, статус, тайминги) для разбора качества ответов (gitignored).
- **Voice pipeline** — endpointing, STT QoS (финал раньше rolling), barge-in по речи, тайминги (`COPILOT_TIMING`), glossary STT — см. [voice-pipeline.md](docs/voice-pipeline.md).

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
3. Говорят → **live** в терминал; после паузы — финал в RAM (и авто-ответ, если включён).
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
STT_LATENCY=fast                  # fast | balanced | quality
STT_FAST_FINAL=1                  # beam=1 на финале (быстрее transcript)
STT_ROLLING=1
STT_PENDING_FLUSH_SEC=0.8         # обрезок «…про» → в transcript (+ авто-ответ [Я])
AUDIO_ROLLING_SEC=1.5
AUDIO_SILENCE_SEC=0.30            # интервьюер (BlackHole), при fast+interview
WHISPER_MODEL_SIZE=small
WHISPER_PROMPT_MODE=tech
WHISPER_GLOSSARY_FIXES=1
AUDIO_PRESET=interview
AUDIO_SILENCE_SEC_SELF=0.48
ANSWER_AUTO=1
ANSWER_AUTO_DELAY_SEC=0
COPILOT_TIMING=1
ANSWER_BARGE_IN_ON_SPEECH=interviewer
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
