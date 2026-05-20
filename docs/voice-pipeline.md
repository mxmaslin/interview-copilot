# Voice pipeline (как устроен copilot)

## Каскад

```
Микрофон / BlackHole → сегментация (тишина, min speech, max segment)
    → Whisper STT (live без initial_prompt, финал с prompt)
    → transcript.md ([Интервьюер] / [Я])
    → ⌘↩ или ANSWER_AUTO → LLM → терминал + data/last-answer.md
```

Это тот же **STT → LLM → act**, что у voice agents, только **act = текст**, не TTS.

## Два режима STT

| Режим | Когда | Куда |
|--------|--------|------|
| **Rolling** (`STT_ROLLING=1`) | Каждые ~2 с речи | «Интервьюер/Я (live)» в терминал |
| **Финал** | Пауза (`AUDIO_SILENCE_SEC*`) | `data/transcript.md` |

Подробно: [audio-setup.md](audio-setup.md).

## Endpointing (VAD + semantic-lite)

1. **VAD / тишина** — `listener.py`, `AUDIO_SILENCE_SEC*` (+ пресет `AUDIO_PRESET`).
2. **Semantic-lite** — `endpointing.is_semantically_complete`: не писать обрубок «Расскажи про» или эхо prompt в transcript.
3. **Debounce** — `endpointing.is_duplicate_final`: не дублировать тот же финал за `STT_FINAL_DEBOUNCE_SEC`.

Переменные:

```bash
AUDIO_PRESET=call          # созвон: Brio + BlackHole
STT_FINAL_DEBOUNCE_SEC=4
STT_MIN_WORDS_FINAL_SELF=3
```

⌘↩: вопрос из **rolling** (`pin_answer_target`), если live новее файла — практика orchestration / human-in-the-loop.

## Тайминги (фаза 1)

В `.env`:

```bash
COPILOT_TIMING=1
# COPILOT_TIMING_JSONL=1
```

После ответа в терминале:

```text
[copilot] timing: stt=420ms llm_ttft=890ms total=1.3s (deepseek, hotkey, self)
```

| Поле | Смысл |
|------|--------|
| `stt` | от конца речи (enqueue финала) до финального текста STT |
| `llm_ttft` | от старта ответа до первого токена LLM |
| `total` | от старта ответа до конца генерации |

## Практики из voice agents (что уже есть)

- Streaming partials + финал
- Фильтр галлюцинаций на тишине
- Human-in-the-loop (⌘↩)
- Cancel in-flight answer (повторное ⌘↩)
- Два спикера и политика «чей вопрос»

## Turn-taking ответа (фаза 4)

- Повторный **⌘↩** отменяет SDK и инвалидирует generation (`answer_turn`) — прерванный ответ **не** перезаписывает `last-answer.md`.
- `pin_answer_target` — LLM видит тот же вопрос, что показан в терминале.

## Архив сессий (аналитика)

Каждый ответ (и прерванный ход) пишется в активную папку `data/sessions/<stamp>/`:

| Файл | Назначение |
|------|------------|
| `turns.jsonl` | JSONL: `source`, `status`, `timing`, `question`, `answer` |
| `review.md` | То же для чтения |
| `meta.json` | `turns_completed`, `turns_cancelled`, `turns_superseded` |

`status`: `completed` | `cancelled` (повторный ⌘↩) | `superseded` (устаревший generation).

Опционально глобально: `COPILOT_TIMING_JSONL=1` → `data/session-timing.jsonl`.

См. [copilot-workflow.md](copilot-workflow.md#архив-сессий).

## Glossary STT

`WHISPER_GLOSSARY_FIXES=1` — пост-правка в `stt_glossary.py` на финале transcript, commit и в live (`stt_live.sanitize_live_transcript`). Примеры: `кавка`→Kafka, `редис`→Redis, `гил`→GIL. Не дублировать списом в `WHISPER_PROMPT`.

Дальше: [voice-pipeline-roadmap.md](voice-pipeline-roadmap.md) фаза 5 (latency по метрикам).
