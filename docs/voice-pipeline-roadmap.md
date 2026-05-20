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
| Presets VAD/silence | `AUDIO_PRESET=call\|solo\|fast` | **3c ✓** |
| Colocated STT (local Whisper) | `STT_PROVIDER=local` | есть |
| TTS / sub-300ms e2e | не применимо (нет TTS) | — |

## Фазы

| Фаза | Статус | Содержание |
|------|--------|------------|
| **0** | Ручная | Чеклист на живом `copilot` |
| **1** | ✓ | `COPILOT_TIMING=1`, `session-timing.jsonl`, `turns.jsonl` в `data/sessions/` |
| **2** | ✓ | `voice-pipeline.md`, fixtures, pytest |
| **3** | ✓ | `endpointing.py`, debounce, semantic-lite, `AUDIO_PRESET` |
| **4** | ✓ | `answer_turn`, `pin_answer_target`, rolling ⌘↩ |
| **5** | Далее | Latency по метрикам (`llm_ttft` vs `stt`) |
| **6** | ✓ | README, AGENTS, skill, rules, audio-setup, copilot-workflow |

### Фаза 0 — верификация

- [ ] Тишина — нет нарастания prompt-echo в live
- [ ] Одна фраза → одна строка в `transcript.md`
- [ ] ⌘↩ на live «про Kafka» — вопрос не «Привет…»
- [ ] Повторный ⌘↩ — не пишет устаревший ответ в `last-answer.md`
- [ ] `timing:` после ответа

### Фаза 3 — endpointing (реализовано)

- `sidecar/copilot/endpointing.py`
- `STT_FINAL_DEBOUNCE_SEC` (по умолчанию 4 с)
- `STT_MIN_WORDS_FINAL_SELF` (по умолчанию 3 слова или `?`)
- `AUDIO_PRESET=call` — длиннее пауза на Brio, короче риск обрубка

### Фаза 5 — когда смотреть timing

| Симптом | Действие |
|---------|----------|
| Большой `llm_ttft` | модель / `ANSWER_PROVIDER` / таймаут |
| Большой `stt` | `AUDIO_PRESET`, `AUDIO_SILENCE_SEC_*`, Whisper |
| Нет `stt` при ⌘↩ на live | норма; смотри финал после паузы |

## Что не делаем

Pipecat/LiveKit, speech-to-speech, TTS в звонок, ML turn-detector.

См. [voice-pipeline.md](voice-pipeline.md), [audio-setup.md](audio-setup.md).
