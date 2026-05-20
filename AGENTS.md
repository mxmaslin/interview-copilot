# Copilot Agent

Правило Cursor: `.cursor/rules/copilot.mdc` (всегда в этом репозитории).

Помощник на **собеседованиях** (HR, менеджер, техэтап, coding). Пользователь один; ответы — кратко и по делу.

## Резюме кандидата

- Файл: **`context/resume.md`** (в чате: `@context/resume.md`).
- Обновление с hh.ru: `pbpaste | python scripts/import-resume.py` — см. `docs/resume-context.md`.
- На вопросы про опыт, проекты, стек — **только факты из резюме**, без выдуманных мест работ и технологий.

## Как запускается сессия

Интервью ведёт **menubar sidecar** (`copilot` в **Terminal.app** / iTerm), не фразы в чате:

1. **`copilot`** → иконка **CP** в menubar; сессия интервью и `⌘↩` / `⌘G` **сразу**; **диалог в RAM сбрасывается** при старте.
2. Реплики: STT (BlackHole + **Начать прослушивание**), **Telegram-бот** (в RAM).
3. **`⌘↩`** — в терминале **только вопрос и ответ** (ответ **по чанкам**, `TERMINAL_ANSWER_STREAM=1`) + `data/last-answer.md`.
4. **`⌘G`** — очистить реплики `[Интервьюер]` и `[Я]` в памяти (новый вопрос с чистого листа).
5. **`⌘⌃⇧4`** — скриншот в буфер → решение задачи в терминал (`SCREENSHOT_SOLVE_ENABLED=1`, см. `docs/screenshot-solve.md`).
6. **Выход:** **CP → Выход** или **Ctrl+C** в терминале с `copilot` (или `./scripts/kill-sidecar.sh`).

Шпаргалка по меню CP: [docs/copilot-workflow.md](docs/copilot-workflow.md).

**Telegram:** бот = только **текст**; **звонок** = BlackHole + Multi-Output (см. `docs/telegram-input.md`). Звонок можно начать после «Начать прослушивание».

**Agents в Cursor:** New Agent — только вручную в IDE. Sidecar **не** переключает фокус. Эксперимент: `CURSOR_AGENT_CHAT_ID` + `CURSOR_AGENT_MIRROR=1` в `.env` (push ответа в чат).

## Провайдер ответа (`.env`)

| `ANSWER_PROVIDER` | Поведение |
|-------------------|-----------|
| `deepseek` | DeepSeek API → терминал + `data/last-answer.md` |
| `openai` | То же через OpenAI Chat API |
| `cursor` | Cursor SDK (`node agent.mjs answer`) |

Ключи: `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`; `CURSOR_API_KEY` — для `cursor` и для **скриншотов** (в т.ч. auto-fallback при `ANSWER_PROVIDER=deepseek`).

Скриншоты (`docs/screenshot-solve.md`): `deepseek-chat` **без vision** → при `CURSOR_API_KEY` скрин идёт в Cursor SDK; `CURSOR_MODEL=auto` читает `~/.cursor/cli-config.json`. Очередь кадров (несколько ⌘⌃⇧4 подряд), один SDK-агент (`SCREENSHOT_REUSE_AGENT=1`). Ответ по скрину — **без** секции «Теория».

Полезные флаги:

- `CURSOR_OPEN_ANSWER_FILE=1` — ещё открывать `last-answer.md` в Cursor (по умолчанию **выкл**).
- `TERMINAL_ANSWER_STREAM=1` — печатать ответ в терминал по мере генерации (по умолчанию **вкл**).
- `CURSOR_AGENT_MIRROR=0` — не дергать `cursor agent` при ответе (рекомендуется).
- `ANSWER_REQUEST_TIMEOUT=120` — таймаут DeepSeek/OpenAI (сек), если меню CP «зависло» на ⌘↩.
- `SCREENSHOT_SOLVE_ENABLED=1` — watcher буфера после ⌘⌃⇧4; `SCREENSHOT_ANSWER_PROVIDER` — переопределить vision-провайдер.
- `CURSOR_MODEL=auto` — модель Cursor SDK из cli-config (`selectedModel`).
- `ANSWER_SELF_QUESTIONS=auto` — ⌘↩ на `[Я]` при соло, `CALL_MIC_MUTED=1` или меню «Микрофон на созвоне выкл».
- `ANSWER_SELF_MERGE_MAX=1` — для `[Я]` по умолчанию **один** последний сегмент (не склеивать серию разных вопросов); `>1` только если одна фраза режется STT на паузах.
- `ANSWER_INTERVIEWER_MERGE_MAX=2` — не склеивать весь звонок BlackHole в один вопрос.
- `ANSWER_AUTO=1` — ответ сразу после **финальной** реплики в transcript (`ANSWER_AUTO_DELAY_SEC=0`); обрезок `[Я]` после `STT_PENDING_FLUSH_SEC` тоже триггерит авто-ответ; **⌘↩** прерывает и перезапускает. Мусор STT (эхо prompt, «Смешка») **не** запускает ответ.
- `ANSWER_BARGE_IN_ON_SPEECH=interviewer` — новая речь на канале отменяет in-flight ответ (как повторный ⌘↩); `0` — выкл; `all` — оба канала.

## STT (локальный Whisper)

| Переменная | Назначение |
|------------|------------|
| `STT_ROLLING=1` | Live-текст в терминал во время речи; в RAM — только финал после паузы |
| `AUDIO_ROLLING_SEC` | Срез монолога без паузы (по умолчанию ~2 с) |
| `STT_LATENCY` | `fast` \| `balanced` \| `quality` |
| `WHISPER_PROMPT_MODE` | `tech` (собес), `general` (HR), `interview` (длинный prompt) |
| `WHISPER_BEAM_SIZE` | Точность финального сегмента; live всегда beam=1 |
| `WHISPER_GLOSSARY_FIXES=1` | RU→EN: GIL, Redis, Kafka (кавка→Kafka) — `stt_glossary.py` |
| `COPILOT_TIMING=1` | `stt` / `llm_ttft` / `total` в терминал и в архив сессии |
| `COPILOT_TIMING_HINTS=1` | Подсказки по тюнингу после timing; `scripts/analyze-session-timing.py` |
| `STT_LIVE_MIN_WORDS=2` | Не печатать live, пока в rolling < N слов |
| `AUDIO_PRESET` | `interview` \| `call` \| `solo` \| `fast` — паузы VAD |
| `STT_FAST_FINAL` | `1` — финальный Whisper beam=1 (быстрее на CPU) |
| `STT_PENDING_FLUSH_SEC` | Дописать обрезок STT в transcript без новой речи |
| `STT_FINAL_DEBOUNCE_SEC` | Не дублировать одинаковый финал |
| `STT_MIN_WORDS_FINAL_SELF` | Мин. слов (или `?`) для финала `[Я]` |

Подробно: [docs/audio-setup.md](docs/audio-setup.md), [docs/voice-pipeline.md](docs/voice-pipeline.md). Skill: `.cursor/skills/interview-copilot/SKILL.md`.

## Архив сессий (разбор качества)

При **CP → Выход** (или новый `copilot`) — `data/sessions/<YYYY-MM-DD_HH-MM-SS>/`: `transcript.md`, `review.md`, `turns.jsonl`, `meta.json`. На ход: `source` (`hotkey` / `auto` / `barge-in`), `status` (`completed` / `cancelled` / `superseded`), `timing` при `COPILOT_TIMING=1`. См. [docs/copilot-workflow.md](docs/copilot-workflow.md#архив-сессий).

## Формат ответов (⌘↩ / транскрипт)

- Отвечай **только на заданный вопрос**; не подменяй тему шаблоном про стек.
- Язык: **русский**; EN-термины как принято.
- Учитывай контекст диалога sidecar (RAM; снимок в `data/sessions/…/transcript.md` при выходе).
- Про опыт и проекты — **только факты из резюме**.
- 5–10 предложений; для live coding — шаги и сложность, если спросили задачу.

## Транскрипт

- `[Интервьюер]:` — звук созвона (BlackHole) и/или **Telegram** (`TELEGRAM_INPUT_ENABLED=1`, см. `docs/telegram-input.md`); в терминал при `TERMINAL_SHOW_INTERVIEWER=1`; STT — **Начать прослушивание**
- `[Я]:` — микрофон (`AUDIO_INPUT_SELF`); в терминал при `TERMINAL_SHOW_SELF=1`

На **⌘↩** — последние сегменты с конца (`ANSWER_INTERVIEWER_MERGE_MAX=2`): обычно `[Интервьюер]`; `[Я]` — **одна** последняя реплика (`ANSWER_SELF_MERGE_MAX=1`). **⌘↩** на `[Я]` сначала режет буфер микрофона и делает синхронный финальный STT (не stale live). Диалог хранится **в RAM** (`transcript.py`); на диск не пишется на каждую реплику — только архив при выходе и **CP → Открыть транскрипт** (снимок в `data/transcript.md`). Старт `copilot` / **⌘G** — очистка RAM. STT: live в терминал; финал в RAM после паузы. См. `docs/audio-setup.md`.

**STT и скриншот:** скрин **⌘⌃⇧4** глушит микрофон, пока очередь скриншотов не пуста; затем STT снова включается, если было **Начать прослушивание**. **⌘↩** (в т.ч. после Telegram) **не блокируется** очередью скринов — ответ и скриншоты параллельно. **⌘↩** с `deepseek` STT не глушит. Telegram polling с момента запуска `copilot`. См. `docs/audio-setup.md`, `docs/telegram-input.md`.

## Разработка проекта copilot

Помогай с sidecar, STT, macOS audio — как обычный инженерный ассистент.
