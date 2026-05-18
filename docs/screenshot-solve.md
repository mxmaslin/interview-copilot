# Скриншот → решение задачи (vision)

После **⌘⌃⇧4** (выделение → **в буфер**) Copilot отправляет картинку в vision API и печатает решение в терминал (текст или код). После успешного ответа буфер **очищается** (`SCREENSHOT_CLEAR_CLIPBOARD=1`).

## Провайдеры

| `ANSWER_PROVIDER` | ⌘↩ (транскрипт) | ⌘⌃⇧4 (скриншот) |
|-------------------|-----------------|-----------------|
| `cursor` | Cursor SDK | Cursor SDK (`solve-screenshot`) |
| `openai` | Chat API | Chat API + `image_url` (или прокси `SCREENSHOT_OPENAI_BASE_URL`) |
| `anthropic` | — | Claude Messages API + vision (`ANTHROPIC_API_KEY`) |
| `deepseek` | DeepSeek Chat API | **не vision** → авто **anthropic** / **cursor** / **openai** |

`deepseek-chat` **не принимает** `image_url` — без fallback будет 400. При наличии `CURSOR_API_KEY` sidecar сам переключает скриншот на Cursor.

Явно: `SCREENSHOT_ANSWER_PROVIDER=cursor|openai|anthropic|deepseek` (для `deepseek` на скриншоте — ошибка).

### Anthropic (Claude vision)

```env
SCREENSHOT_ANSWER_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
SCREENSHOT_ANTHROPIC_MODEL=claude-3-5-haiku-latest   # быстро; sonnet — точнее
SCREENSHOT_WARM_AGENT=0
```

Ключ: [console.anthropic.com](https://console.anthropic.com/). Зависимость: `pip install -e 'sidecar/[llm]'` (пакет `anthropic`).

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
2. **⌘⌃⇧4** → ответ в терминале (~debounce). **Второй скрин** во время обработки первого **не теряется** — обработается сразу после ответа (в логе: «ждём завершения текущего SDK»).
3. На время скрина STT **пауза**; после ответа — **STT возобновлено** (нужно было **Начать прослушивание**).
4. Файлы: `data/last-screenshot-answer.md`, при `SCREENSHOT_SOLVE_ALSO_LAST_ANSWER=1` — ещё `data/last-answer.md`.

Блок «Я / редактор субтитров» в терминале при скрине — это **не** vision, а мусор STT с микрофона; сейчас отфильтровано + STT глушится на скрин.

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

## Скорость (без смены модели)

По умолчанию `SCREENSHOT_LATENCY=fast`:

- watcher: poll **0.12 с**, debounce **0.08 с**;
- сжатие до **1024px** + JPEG q≈0.78 (`SCREENSHOT_OPTIMIZE=1`);
- **новый SDK-агент на каждый скрин** (`SCREENSHOT_REUSE_AGENT=0`) — без накопленной истории и без tool-loop по репо `_copilot`;
- агент в **пустом temp cwd** (не видит файлы проекта);
- промпт: «только картинка, без инструментов»;
- **прогрев** при старте (`SCREENSHOT_WARM_AGENT=1`).

При `solve-screenshot`: `local.force: true`; при `already has active run` — сброс `screenshot-agent-state.json` и повтор.

Точнее / с переиспользованием агента: `SCREENSHOT_LATENCY=balanced` (debounce 0.25 с, 1920px, `SCREENSHOT_REUSE_AGENT=1`).

Отдельная модель только для скринов (не трогая ⌘↩):

```env
# SCREENSHOT_CURSOR_MODEL=auto
# SCREENSHOT_CURSOR_MODEL=composer-2
```

### OpenAI недоступен в стране

| Вариант | Настройка | Скорость | Заметки |
|---------|-----------|----------|---------|
| **Cursor SDK** | `SCREENSHOT_ANSWER_PROVIDER=cursor` + `CURSOR_API_KEY` | Средняя | Уже работает, без OpenAI |
| **OpenAI-совместимый прокси** | `SCREENSHOT_ANSWER_PROVIDER=openai` + `SCREENSHOT_OPENAI_BASE_URL` + ключ прокси | Обычно быстрее Cursor | ProxyAPI, OpenRouter и т.п. — тот же `image_url`, другой `base_url` |
| **DeepSeek** | — | — | `deepseek-chat` **без** картинок; для скринов не подходит |

Пример прокси (подставь свой URL и модель из доки провайдера):

```env
SCREENSHOT_ANSWER_PROVIDER=openai
OPENAI_API_KEY=ключ_от_прокси
SCREENSHOT_OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
SCREENSHOT_VISION_MODEL=gpt-4o-mini
SCREENSHOT_WARM_AGENT=0
```

⌘↩ может оставаться `ANSWER_PROVIDER=cursor` или `deepseek` — скриншоты настраиваются отдельно.

## Ограничения

- Скриншот через Cursor — отдельный ephemeral SDK-агент (не нужен `agent.mjs start` для интервью).
- Copilot **не перехватывает** ⌘⌃⇧4 — только читает буфер после macOS.
- Accessibility для скриншотов **не нужен**; для ⌘↩ / ⌘G (pynput) — нужен.
