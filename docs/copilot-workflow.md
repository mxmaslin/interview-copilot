# Copilot: menubar CP и hotkeys

Краткая шпаргалка после упрощения меню (2026).

## Запуск и выход

```bash
source scripts/activate-venv.sh
copilot   # Terminal.app / iTerm, не терминал Cursor
```

- При старте: сессия интервью **сразу** (hotkeys активны), `data/transcript.md` **сбрасывается**.
- Выход: **CP → Выход** или **Ctrl+C** в терминале с `copilot`.
- Зависший процесс: `./scripts/kill-sidecar.sh`

## Меню CP

| Пункт | Действие |
|--------|----------|
| **Начать прослушивание** | STT: BlackHole (интервьюер) + микрофон (я) |
| **Остановить прослушивание** | Выключить STT |
| **Ответ на последний вопрос (⌘↩)** | DeepSeek / OpenAI / Cursor → терминал + `data/last-answer.md` |
| **Микрофон на созвоне выкл** | ⌘↩ на **одну** последнюю реплику `[Я]` (не склеивать старые вопросы); `[Интервьюер]` игнорируется; флаг в `data/call-mic-muted` |
| **Очистить транскрипт (⌘G)** | Новый вопрос без старых реплик |
| **Решить скриншот (⌘⌃⇧4)** | Vision из буфера (или авто-watcher) |
| **Открыть transcript / ответы** | Файлы в редакторе |
| **Выход** | Остановить sidecar |

Ручной ввод реплик, привязка Agents chatId, отмена SDK — только через `.env` / правку `transcript.md` (см. `AGENTS.md`).

## Hotkeys

| Клавиши | Назначение |
|---------|------------|
| **⌘↩** | Ответ на последний вопрос (2 последних сегмента `[Интервьюер]` или `[Я]` в solo-режиме) |
| **⌘G** | Очистить транскрипт в сессии |
| **⌘⌃⇧4** | Скриншот в буфер → очередь vision (STT на паузе, пока очередь не пуста) |

⌘↩ и скриншоты **параллельно** (при `ANSWER_PROVIDER=deepseek`).

## Реплики

- `[Интервьюер]:` — BlackHole (звонок), Telegram-бот
- `[Я]:` — микрофон (Brio и т.п.)

Подробнее: [audio-setup.md](audio-setup.md), [telegram-input.md](telegram-input.md).

## Архив сессий

После **CP → Выход** (или нового `copilot`) сессия сохраняется в `data/sessions/<дата-время>/`:

- `transcript.md` — полный диалог
- `review.md` — вопросы и ответы Copilot по ходам
- `meta.json` — время начала/конца

Папка в `.gitignore` — для разбора, насколько ответы попадали в вопрос.

## Полезные `.env`

```env
ANSWER_PROVIDER=deepseek
ANSWER_SELF_QUESTIONS=auto      # solo / CALL_MIC_MUTED / меню «микрофон выкл»
ANSWER_SELF_MERGE_MAX=1         # [Я]: один сегмент; >1 — только если одна фраза рвётся на паузах
ANSWER_INTERVIEWER_MERGE_MAX=2  # не склеивать весь звонок в один «вопрос»
CALL_MIC_MUTED=0
SCREENSHOT_SOLVE_ENABLED=1
TELEGRAM_INPUT_ENABLED=1
```

Полный список: `.env.example`, [AGENTS.md](../AGENTS.md).
