# Voice pipeline roadmap (Interview Copilot)

Copilot — **voice-augmented sidecar**: STT → LLM → текст. План привязан к практикам voice agents ([Twilio](https://www.twilio.com/en-us/blog/developers/best-practices/guide-core-latency-ai-voice-agents), [LiveKit turn detection](https://www.livekit.io/blog/turn-detection-voice-agents-vad-endpointing-model-based-detection), [NVIDIA](https://github.com/NVIDIA/voice-agent-examples/blob/main/docs/BEST_PRACTICES.md)).

## Маппинг практик → copilot

| Voice-agent практика | В copilot | Фаза |
|----------------------|-----------|------|
| Per-stage latency metrics | `COPILOT_TIMING`, `pipeline_timing.py` | 1 ✓ |
| STT hallucination filter | `stt_filter`, `stt_live` | до плана + 2 |
| Streaming partials + final | `STT_ROLLING` | есть |
| **Semantic / smart endpointing** | `endpointing.is_semantically_complete` | **3 ✓** |
| **Debounce false EOU** | `endpointing.is_duplicate_final` | **3 ✓** |
| **Barge-in / cancel in-flight** | `answer_turn`, `pin_answer_target`, cancel SDK | **4 ✓** |
| Orchestration: question pin | `pin_answer_target`, rolling на ⌘↩ | 4 ✓ |
| Presets VAD/silence | `AUDIO_PRESET=call\|solo\|fast\|interview` | **3c ✓** |
| Colocated STT (local Whisper) | `STT_PROVIDER=local` | есть |
| **STT QoS: final before rolling** | `stt_worker` PriorityQueue | **8 ✓** |
| **Barge-in on new speech** | `ANSWER_BARGE_IN_ON_SPEECH`, `listener.on_speech_start` | **9 ✓** |
| TTS / sub-300ms e2e | не применимо (нет TTS) | — |

## Фазы

| Фаза | Статус | Содержание |
|------|--------|------------|
| **0** | Ручная | Чеклист на живом `copilot` |
| **1** | ✓ | `COPILOT_TIMING=1`, `session-timing.jsonl`, `turns.jsonl` в `data/sessions/` |
| **2** | ✓ | `voice-pipeline.md`, fixtures, pytest |
| **3** | ✓ | `endpointing.py`, debounce, semantic-lite, `AUDIO_PRESET` |
| **4** | ✓ | `answer_turn`, `pin_answer_target`, rolling ⌘↩ |
| **5** | ✓ | `COPILOT_TIMING_HINTS`, `scripts/analyze-session-timing.py`, `STT_LIVE_MIN_WORDS` |
| **6** | ✓ | README, AGENTS, skill, rules, audio-setup, copilot-workflow |
| **7** | ✓ | `normalize_question_text`, Kafka variants, LLM STT-tolerance в prompt |
| **8** | ✓ | STT QoS: `PriorityQueue` (финал раньше rolling), `STT_FAST_FINAL`, `AUDIO_PRESET=interview`, `STT_PENDING_FLUSH_SEC`, `RLock` в transcript |
| **9** | ✓ | Barge-in: `ANSWER_BARGE_IN_ON_SPEECH=interviewer` — отмена in-flight ответа при новой речи |

### Фаза 0 — верификация

- [ ] Тишина — нет нарастания prompt-echo в live
- [x] Одна фраза → одна строка в RAM-диалоге
- [ ] ⌘↩ на live «про Kafka» — вопрос не «Привет…»
- [ ] Повторный ⌘↩ — не пишет устаревший ответ в `last-answer.md`
- [ ] `timing:` после ответа

### Фаза 3 — endpointing (реализовано)

- `sidecar/copilot/endpointing.py`
- `STT_FINAL_DEBOUNCE_SEC` (по умолчанию 4 с)
- `STT_MIN_WORDS_FINAL_SELF` (по умолчанию 3 слова или `?`)
- `AUDIO_PRESET=call` — длиннее пауза на Brio, короче риск обрубка

### Фаза 5 — latency по метрикам (реализовано)

После ответа при `COPILOT_TIMING=1` и `COPILOT_TIMING_HINTS=1` (по умолчанию вместе с timing):

```text
[copilot] timing: stt=420ms llm_ttft=890ms total=1.3s (deepseek, hotkey, self)
[copilot] hint: LLM TTFT 2100ms ≥ 1500ms: deepseek-chat, ANSWER_MINIMAL_CONTEXT=1, ...
```

Сводка по сессиям:

```bash
python scripts/analyze-session-timing.py
python scripts/analyze-session-timing.py 2026-05-20_18-22-52
```

Пороги: `COPILOT_STT_SLOW_MS=800`, `COPILOT_LLM_SLOW_MS=1500`.

**Live UX:** `STT_LIVE_MIN_WORDS=2` — не печатать rolling, пока < 2 слов (меньше мусора в терминале).

| Симптом | Действие |
|---------|----------|
| Большой `llm_ttft` | модель / `ANSWER_MINIMAL_CONTEXT` / `ANSWER_MAX_TOKENS` |
| Большой `stt` | `AUDIO_PRESET`, `AUDIO_SILENCE_SEC_*`, `STT_LATENCY=fast` |
| Нет `stt` при ⌘↩ на live | норма; hint в терминале |

### Фаза 8 — STT QoS (реализовано)

- Очередь Whisper: **финал** (`live=False`) обрабатывается раньше **rolling** (`live=True`).
- `STT_FAST_FINAL=1` — `beam=1` на финале (быстрее decode на CPU).
- `AUDIO_PRESET=interview` — короче пауза `[Я]` (~0.62 с).
- `STT_PENDING_FLUSH_SEC` — обрезок «…про» дописывается в transcript без новой речи.
- `transcript.py`: `RLock` — без deadlock при склейке pending + финал.

### Фаза 9 — barge-in по речи (реализовано)

Пока идёт ответ (`ANSWER_AUTO` или предыдущий ход), **новая речь** на канале из `ANSWER_BARGE_IN_ON_SPEECH` отменяет SDK (как повторный ⌘↩). По умолчанию только **interviewer**; `0` — выкл; `all` — оба канала.

```bash
ANSWER_BARGE_IN_ON_SPEECH=interviewer   # по умолчанию
# ANSWER_BARGE_IN_ON_SPEECH=0
# ANSWER_BARGE_IN_ON_SPEECH=all
```

В архиве сессии: `source=barge-in`, `status=cancelled`.

## Что не делаем

Pipecat/LiveKit, speech-to-speech, TTS в звонок, ML turn-detector.

См. [voice-pipeline.md](voice-pipeline.md), [audio-setup.md](audio-setup.md).
