# Скриншот → решение задачи (vision)

После **⌘⌃⇧4** (выделение → **в буфер**) Copilot отправляет картинку в vision API и печатает решение в терминал (текст или код). После успешного ответа буфер **очищается** (`SCREENSHOT_CLEAR_CLIPBOARD=1`).

## Провайдеры

| `ANSWER_PROVIDER` | ⌘↩ (транскрипт) | ⌘⌃⇧4 (скриншот) |
|-------------------|-----------------|-----------------|
| `cursor` | Cursor SDK | Cursor SDK (`solve-screenshot`) |
| `openai` | Chat API | Chat API + `image_url` |
| `deepseek` | DeepSeek Chat API | **не vision** → авто **cursor** (если `CURSOR_API_KEY`), иначе **openai** |

`deepseek-chat` **не принимает** `image_url` — без fallback будет 400. При наличии `CURSOR_API_KEY` sidecar сам переключает скриншот на Cursor.

Явно: `SCREENSHOT_ANSWER_PROVIDER=cursor|openai|deepseek` (для `deepseek` на скриншоте — ошибка).

## Модель Cursor

```env
ANSWER_PROVIDER=cursor          # или deepseek для ⌘↩ + cursor для скринов (auto)
CURSOR_API_KEY=...
CURSOR_MODEL=auto               # ~/.cursor/cli-config.json → selectedModel
# CURSOR_MODEL=composer-2
```

`auto` подхватывает `modelId` и `parameters` (например `fast=true`) из cli-config. Это **не** 100% синхрон с выпадашкой Agents в IDE.

## Как пользоваться

1. `copilot` в терминале, `SCREENSHOT_SOLVE_ENABLED=1`.
2. **⌘⌃⇧4** → ответ в терминале (~0.35 с debounce).
3. Файлы: `data/last-screenshot-answer.md`, при `SCREENSHOT_SOLVE_ALSO_LAST_ANSWER=1` — ещё `data/last-answer.md`.

Ручной запуск: **CP → Решить скриншот из буфера (⌘⌃⇧4)**.

## Переменные `.env`

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SCREENSHOT_SOLVE_ENABLED` | `1` | Watcher буфера |
| `SCREENSHOT_ANSWER_PROVIDER` | см. таблицу выше | Переопределить провайдер vision |
| `SCREENSHOT_CLEAR_CLIPBOARD` | `1` | Очистить буфер после ответа |
| `SCREENSHOT_DEBOUNCE_SEC` | `0.35` | Пауза после смены pasteboard |
| `SCREENSHOT_SOLVE_ALSO_LAST_ANSWER` | `1` | Дублировать в `last-answer.md` |
| `CURSOR_MODEL` | `composer-2` | Для cursor-скринов: `auto` → cli-config |

## Типичный `.env` (DeepSeek + скриншоты)

```env
ANSWER_PROVIDER=deepseek
DEEPSEEK_API_KEY=...
CURSOR_API_KEY=...              # для скриншотов (auto-fallback)
CURSOR_MODEL=auto
SCREENSHOT_SOLVE_ENABLED=1
# SCREENSHOT_ANSWER_PROVIDER=cursor   # опционально, явно
```

## Ограничения

- Скриншот через Cursor — отдельный ephemeral SDK-агент (не нужен `agent.mjs start` для интервью).
- Copilot **не перехватывает** ⌘⌃⇧4 — только читает буфер после macOS.
- Accessibility для скриншотов **не нужен**; для ⌘↩ / ⌘G (pynput) — нужен.
