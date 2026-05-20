---
name: interview-copilot
description: >-
  macOS Interview Copilot sidecar: STT transcript, rolling live text, auto-answer,
  screenshot vision. Use when developing or debugging copilot, sidecar, Whisper STT,
  audio/BlackHole, menubar hotkeys, or answering from data/transcript.md.
---

# Interview Copilot

Проект: menubar **CP** в **Terminal.app** (не встроенный терминал Cursor). Запуск: `copilot` после `source scripts/activate-venv.sh`.

## Сессия интервью

1. `copilot` → сброс `data/transcript.md`, hotkeys `⌘↩` / `⌘G` сразу.
2. **CP → Начать прослушивание** — STT (BlackHole = `[Интервьюер]`, микрофон = `[Я]`).
3. `⌘↩` — ответ на **последний** вопрос; `ANSWER_AUTO=1` — ответ после финальной реплики STT.
4. `⌘G` — очистить реплики в сессии.
5. `⌘⌃⇧4` — скрин в буфер → vision (без секции «Теория»); STT пауза до пустой очереди скринов.
6. **CP → Выход** или Ctrl+C.

## STT (важно)

| Режим | Поведение |
|-------|-----------|
| **Rolling** (`STT_ROLLING=1`) | Каждые ~2 с речи → **«Интервьюер (live)»** в терминал (быстрый Whisper). |
| **Финал** | Пауза ~0.45 с → одна строка в `data/transcript.md` + авто-ответ. |

Переменные: `STT_LATENCY`, `AUDIO_ROLLING_SEC`, `WHISPER_PROMPT_MODE=tech` (собес, латиница без списка брендов), `WHISPER_GLOSSARY_FIXES`. Подробно: `docs/audio-setup.md`.

Не хардкодить отдельные бренды (Kafka и т.д.) в код — только prompt/decode/глоссарий.

## Ответы агента в Cursor

- Резюме: `@context/resume.md` — только факты оттуда.
- Формат: русский, EN-термины, **определение → пример → оговорки**, 5–10 предложений.
- Не подменять вопрос шаблоном про стек; учитывать хвост `data/transcript.md`.
- Скриншот: только решение задачи, без «Теории».

## Ключевые файлы

| Область | Путь |
|---------|------|
| Menubar / hotkeys | `sidecar/copilot/app.py` |
| Сегментация аудио | `sidecar/copilot/listener.py` |
| Rolling / merge | `sidecar/copilot/stt_segment.py`, `transcript.py` |
| Whisper | `sidecar/copilot/stt.py`, `stt_prompt.py`, `config.py` |
| Правила Cursor | `.cursor/rules/copilot.mdc`, `AGENTS.md` |

## Разработка

```bash
pip install -e "./sidecar[audio,dev,openai]"
pytest sidecar/tests -q
```

Не коммитить `.env`, `context/resume.md`, `data/`. См. `SECURITY.md`.
