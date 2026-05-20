---
name: interview-copilot
description: >-
  macOS Interview Copilot sidecar: STT transcript, rolling live text, auto-answer,
  screenshot vision. Use when developing or debugging copilot, sidecar, Whisper STT,
  audio/BlackHole, menubar hotkeys, or in-memory transcript (RAM).
---

# Interview Copilot

Проект: menubar **CP** в **Terminal.app** (не встроенный терминал Cursor). Запуск: `copilot` после `source scripts/activate-venv.sh`.

## Сессия интервью

1. `copilot` → сброс диалога в RAM, hotkeys `⌘↩` / `⌘G` сразу.
2. **CP → Начать прослушивание** — STT (BlackHole = `[Интервьюер]`, микрофон = `[Я]`).
3. `⌘↩` — ответ на **последний** вопрос; `ANSWER_AUTO=1` — после финала в transcript (без ⌘↩). Мусор STT («Смешка», эхо prompt) не запускает ответ.
4. `⌘G` — очистить реплики в сессии.
5. `⌘⌃⇧4` — скрин в буфер → vision (без секции «Теория»); STT пауза до пустой очереди скринов.
6. **CP → Выход** или Ctrl+C.

## STT (важно)

| Режим | Поведение |
|-------|-----------|
| **Rolling** (`STT_ROLLING=1`) | Каждые ~2 с речи → **«Интервьюер (live)»** в терминал (быстрый Whisper). |
| **Финал** | Пауза ~0.4 с → реплика в RAM + авто-ответ; на диск не пишется. |

Переменные: `STT_LATENCY=fast`, `STT_FAST_FINAL=1`, `WHISPER_GLOSSARY_FIXES`, `AUDIO_PRESET=interview`, `ANSWER_BARGE_IN_ON_SPEECH=interviewer`, `COPILOT_TIMING=1`, `STT_LIVE_MIN_WORDS=2`. Анализ latency: `python scripts/analyze-session-timing.py`. Доки: `docs/voice-pipeline.md`, `docs/stt-glossary.md`.

Не хардкодить отдельные бренды в бизнес-логику — только `stt_glossary.py` / prompt / фильтры (`stt_filter`, `stt_live`).

## Архив сессий

`data/sessions/<stamp>/` — `turns.jsonl` (source, status, timing), `review.md`, `meta.json`. Пишется на каждый ответ и при **CP → Выход**. Статусы: `completed`, `cancelled` (повторный ⌘↩), `superseded` (устаревший worker).

## Troubleshooting (полевой UX)

| Симптом | Причина | Действие |
|---------|---------|----------|
| Каша в терминале (два ответа в одном блоке) | Повторный ⌘↩ при `ANSWER_PROVIDER=deepseek` во время стрима | Дождаться конца ответа; не дублировать ⌘↩; или `cursor` |
| `timing: … speaker=self` на все вопросы | Соло: только Brio, нет `[Интервьюер]` | Для созвона — BlackHole; см. `docs/audio-setup.md` |
| Hint «stt пуст» на ⌘↩ | Ответ по **live**, финал ещё не в RAM | Норма; можно озвучивать по live |
| Два одинаковых ответа (Kafka…) | Два ⌘↩ на тот же вопрос | Не повторять hotkey; **⌘G** при смене темы |

См. `docs/copilot-workflow.md` § «Ограничения и UX».

## Ответы агента в Cursor

- Резюме: `@context/resume.md` — только факты оттуда.
- Формат: русский, EN-термины, **определение → пример → оговорки**, 5–10 предложений.
- Не подменять вопрос шаблоном про стек; учитывать хвост диалога в RAM.
- Скриншот: только решение задачи, без «Теории».

## Ключевые файлы

| Область | Путь |
|---------|------|
| Menubar / hotkeys | `sidecar/copilot/app.py` |
| Сегментация аудио | `sidecar/copilot/listener.py` |
| Rolling / live / merge | `stt_segment.py`, `stt_live.py`, `transcript.py` (RAM only) |
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
