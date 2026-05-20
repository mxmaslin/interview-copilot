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

Переменные: `STT_LATENCY`, `WHISPER_GLOSSARY_FIXES`, `AUDIO_PRESET=call`, `COPILOT_TIMING=1`, `COPILOT_TIMING_HINTS=1`, `STT_LIVE_MIN_WORDS=2`. Анализ latency: `python scripts/analyze-session-timing.py`. Доки: `docs/voice-pipeline.md`, `docs/stt-glossary.md`.

Не хардкодить отдельные бренды в бизнес-логику — только `stt_glossary.py` / prompt / фильтры (`stt_filter`, `stt_live`).

## Архив сессий

`data/sessions/<stamp>/` — `turns.jsonl` (source, status, timing), `review.md`, `meta.json`. Пишется на каждый ответ и при **CP → Выход**. Статусы: `completed`, `cancelled` (повторный ⌘↩), `superseded` (устаревший worker).

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
| Rolling / live / merge | `stt_segment.py`, `stt_live.py`, `transcript.py` |
| Whisper / glossary | `stt.py`, `stt_prompt.py`, `stt_glossary.py`, `config.py` |
| Endpointing | `endpointing.py` |
| Тайминги / ходы ответа | `pipeline_timing.py`, `answer_turn.py` |
| Архив сессий | `session_archive.py` |
| Правила Cursor | `.cursor/rules/copilot.mdc`, `AGENTS.md` |

## Разработка

```bash
pip install -e "./sidecar[audio,dev,openai]"
pytest sidecar/tests -q
```

Не коммитить `.env`, `context/resume.md`, `data/`. См. `SECURITY.md`.
