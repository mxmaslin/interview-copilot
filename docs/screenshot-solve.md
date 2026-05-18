# Скриншот → решение задачи (vision)

После **⌘⌃⇧4** (выделение → **в буфер**) Copilot захватывает кадр в **очередь**, отправляет в vision API и печатает решение в терминал. При `SCREENSHOT_CLEAR_CLIPBOARD=1` буфер очищается **сразу после захвата** (PNG уже в памяти очереди).

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

1. `copilot` в терминале, `SCREENSHOT_SOLVE_ENABLED=1` (в логе: `очередь скриншотов: worker запущен`).
2. **⌘⌃⇧4** → кадр в очередь → ответ в терминале по мере готовности. **Несколько скринов подряд** — в логе `скриншот #N в очереди (ожидают: …)`, обработка строго по одному.
3. На время обработки очереди STT **пауза**; когда очередь пуста — **STT возобновлено** (если было **Начать прослушивание**). **⌘↩** (Telegram / транскрипт) **не блокируется** скриншотами — DeepSeek/OpenAI идут параллельно очереди Cursor-скринов.
4. Файлы: `data/last-screenshot-answer.md`, при `SCREENSHOT_SOLVE_ALSO_LAST_ANSWER=1` — ещё `data/last-answer.md`.

**Формат ответа:** код/вариант + 1–3 предложения пояснения. **Без** секции «Теория» и без блока «определение → пример → оговорки» (это только для ⌘↩ по транскрипту).

Ручной запуск: **CP → Решить скриншот из буфера (⌘⌃⇧4)**.

## Переменные `.env`

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SCREENSHOT_SOLVE_ENABLED` | `1` | Watcher буфера |
| `SCREENSHOT_ANSWER_PROVIDER` | см. таблицу выше | Переопределить провайдер vision |
| `SCREENSHOT_CLEAR_CLIPBOARD` | `1` | Очистить буфер после захвата в очередь |
| `SCREENSHOT_REUSE_AGENT` | `1` | Один Cursor SDK-агент на все скрины сессии |
| `SCREENSHOT_DEBOUNCE_SEC` | `0.08` (fast) / `0.25` (balanced) | Пауза после смены pasteboard |
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

## Параллельно с ⌘↩ / Telegram

| Канал | Провайдер (типично) | Блокирует другие? |
|-------|---------------------|-------------------|
| ⌘↩, вопрос из транскрипта / Telegram | `deepseek` / `openai` | Только повторный ⌘↩ |
| ⌘⌃⇧4, очередь скринов | `cursor` / `anthropic` | Не блокирует ⌘↩ |

STT на время обработки очереди скринов **пауза**; текст из Telegram в транскрипт попадает всегда.

## Очередь и один агент

Несколько ⌘⌃⇧4 подряд **не теряются**:

1. Watcher видит новый кадр в буфере → `enqueue_clipboard()` **сразу** читает PNG в память.
2. Очередь обрабатывает кадры **по одному**; ответы выходят по мере готовности.
3. Буфер можно очистить сразу после захвата (`SCREENSHOT_CLEAR_CLIPBOARD=1`) — следующий скрин не затирает предыдущий.

**Один Cursor SDK-агент** на все скриншоты сессии (`SCREENSHOT_REUSE_AGENT=1` по умолчанию): `resume` из `data/screenshot-agent-state.json`, без `dispose` после каждого кадра. Отключить: `SCREENSHOT_REUSE_AGENT=0` (медленнее, но «чистый» агент каждый раз).

## Скорость (без смены модели)

По умолчанию `SCREENSHOT_LATENCY=fast`:

- watcher: poll **0.12 с**, debounce **0.08 с**;
- сжатие до **1024px** + JPEG q≈0.78 (`SCREENSHOT_OPTIMIZE=1`);
- агент в **пустом temp cwd** (не видит файлы проекта);
- промпт: «только картинка, без инструментов»;
- **прогрев** при старте (`SCREENSHOT_WARM_AGENT=1`).

При `solve-screenshot`: `local.force: true`; при `already has active run` — сброс `screenshot-agent-state.json` и повтор.

Точнее: `SCREENSHOT_LATENCY=balanced` (debounce 0.25 с, 1920px).

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

- Скриншот через Cursor — отдельный SDK-агент для vision (`data/screenshot-agent-state.json`), не тот же, что `agent.mjs start` для ⌘↩.
- Copilot **не перехватывает** ⌘⌃⇧4 — только читает буфер после macOS.
- Accessibility для скриншотов **не нужен**; для ⌘↩ / ⌘G (pynput) — нужен.
