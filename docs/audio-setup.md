# Звук Zoom / Telemost / Meet на macOS

Чтобы sidecar слышал **интервьюера** из созвона, звук приложения должен идти на виртуальное устройство **BlackHole**, а sidecar записывает с BlackHole.

## 1. Установка BlackHole

- [BlackHole 2ch](https://existential.audio/blackhole/) (бесплатно)
- После установки перезагрузи Mac или перelogинься, если устройство не видно

## 2. Zoom

1. **Zoom → Настройки → Аудио**
2. **Динамик:** `BlackHole 2ch`
3. **Микрофон:** твой обычный микрофон (чтобы тебя слышали)

Ты будешь слышать собеседника в наушниках через **Multi-Output Device** (см. ниже), иначе в Zoom будет тишина в ушах.

## 3. Multi-Output (слышать и писать одновременно)

1. Открой **Audio MIDI Setup** (`/Applications/Utilities/`)
2. **+** → **Create Multi-Output Device**
3. Отметь: **BlackHole 2ch** + **наушники / встроенные динамики**
4. В Zoom в качестве динамика выбери этот Multi-Output (или настрой маршрутизацию по гайдам BlackHole)

## 4. Yandex Telemost / Google Meet / Telegram (звонок)

Аналогично: **вывод звука** созвона → BlackHole (или **Multi-Output** с BlackHole + наушники).

**Telegram:** только **голосовой звонок** (не бот). Если в Telegram выбран только BlackHole — copilot слышит, **ты нет** → нужен Multi-Output. Подробно: [telegram-input.md](telegram-input.md).

## 5. Два входа в sidecar

| Кто | Устройство в `.env` | Транскрипт |
|-----|---------------------|------------|
| Интервьюер (созвон) | `AUDIO_INPUT_INTERVIEWER=BlackHole` | `[Интервьюер]:` |
| Ты | `AUDIO_INPUT_SELF=Brio` | `[Я]:` |

**CP → Начать прослушивание** включает оба канала. Без BlackHole канал интервьюера не заработает — установи по шагам 1–4 выше.

## 6. Sidecar и локальный Whisper (по умолчанию)

**Зависимости:**

```bash
brew install ffmpeg
cd /path/to/_copilot && source .venv/bin/activate
pip install -e "./sidecar[audio]"
```

В `.env` (рекомендуется для MacBook Air M4, 24 GB):

```bash
STT_PROVIDER=local
STT_LATENCY=balanced      # fast | balanced | quality
STT_ROLLING=1             # транскрипт в терминал по ходу речи
# AUDIO_ROLLING_SEC=2     # срез монолога без паузы (сек)
WHISPER_PROMPT_MODE=tech  # tech — латиница для IT; general — HR; interview — макс.
WHISPER_MODEL_SIZE=small  # пресет fast/balanced; quality → large-v3
WHISPER_COMPUTE_TYPE=int8
WHISPER_DEVICE=cpu
AUDIO_INPUT_INTERVIEWER=BlackHole
AUDIO_INPUT_SELF=Brio
AUDIO_PREFER_16K=1
```

Первый запуск скачает модель **small** (пресет `fast`/`balanced`, ~500 MB) — один раз. Дальше сегменты на машине, **без API-ключей**.

Сообщение `unauthenticated requests to the HF Hub` — от библиотеки Hugging Face при скачивании модели; на работу не влияет. Sidecar приглушает его в терминале. По желанию: `HF_TOKEN=hf_…` в `.env` ([токен на huggingface.co](https://huggingface.co/settings/tokens)).

### Задержка STT и вывод в терминал

**Rolling STT** (`STT_ROLLING=1`, по умолчанию): пока интервьюер говорит, каждые ~2 с речи сегмент уходит в Whisper с **быстрым decode** (`beam=1`) → в терминал строка **«Интервьюер (live)»**. В `transcript.md` и авто-ответ попадает **только финал** после паузы (~0.45 с), с глоссарием и `beam=3`.

| Переменная | `fast` | `balanced` (собес) | Назначение |
|------------|--------|---------------------|------------|
| `STT_ROLLING` | `1` | `1` | Частичный текст во время речи; `0` — только после паузы |
| `AUDIO_ROLLING_SEC` | ~1.8 | ~2.0 | Срез монолога без паузы (при `STT_ROLLING=1`) |
| `STT_LATENCY` | `fast` | `balanced` | Пресет; `quality` — длинные паузы + VAD |
| `AUDIO_SILENCE_SEC` | ~0.38 | ~0.45 | Тишина перед **финальным** сегментом |
| `AUDIO_SILENCE_SEC_SELF` | ~0.72 | ~0.85 | Микрофон `[Я]` — дольше, чтобы не резать фразу |
| `AUDIO_MAX_SEGMENT_SEC_SELF` | ~6 | ~8 | Макс. длина фразы с Brio |
| `WHISPER_MODEL_SIZE` | `small` | `small` | Явно переопределяет пресет; `quality` → `large-v3` |
| `WHISPER_BEAM_SIZE` | 1 | 3 | Только финальный сегмент; live всегда `beam=1` |
| `WHISPER_VAD_FILTER` | 0 | 0 | VAD в Whisper дублирует сегментацию listener |
| `WHISPER_PROMPT_MODE` | `tech` | `tech` | `tech` — IT без списка брендов; `interview` — длинный prompt; `general` — HR |
| `TERMINAL_SHOW_SELF` | `1` | `1` | Печатать реплики `[Я]` в терминал |

STT выполняется **в фоновом потоке** — запись с BlackHole не блокируется на время Whisper.

Фильтр галлюцинаций Whisper на тишине («редактор субтитров…») — `stt_filter.py`, не попадает в транскрипт.

### Пайплайн (интервьюер → DeepSeek)

1. BlackHole / вход → rolling ~2 с (live в терминал) + финал по паузе ~0.45 с.
2. **faster-whisper** (async) → live в терминал; финал → `transcript.md`.
3. **⌘↩** → последний вопрос интервьюера (хвостовые `[Я]` с микрофона **игнорируются**) → DeepSeek **stream** → терминал.
4. **⌘G** → очистить все реплики `[Интервьюер]` и `[Я]` (новый вопрос с нуля).

### Пауза STT на время SDK

| Событие | STT |
|---------|-----|
| **⌘↩** + `ANSWER_PROVIDER=deepseek` | **не** глушится (`ANSWER_PAUSE_AUDIO=auto`) |
| **⌘↩** + `ANSWER_PROVIDER=cursor` | пауза до конца ответа |
| **⌘⌃⇧4** (скриншот) | **всегда** пауза; после ответа — **автовозобновление**, если было **Начать прослушивание** |

В терминале после скрина: `[copilot] STT возобновлено: …`. Вложенные паузы (⌘↩ + скрин подряд) — счётчик, STT не «теряется».

`ANSWER_PAUSE_AUDIO=always` — глушить STT и на ⌘↩ с DeepSeek.

### Пределы задержки (честно)

| Этап | Типично | Узкое место |
|------|---------|------------|
| Rolling-срез | ~2 с речи | Live-текст в терминал, не ждём конца вопроса |
| Пауза до финала | ~0.45 с | Только запись в `transcript.md` |
| Whisper `small` int8 | ~0.5–1.5 с live, 1–2 с финал | CPU; `STT_LATENCY=fast` ещё быстрее |
| Сеть DeepSeek TTFT | 0.3–1.5 с | API; `deepseek-chat`, не `reasoner` |
| Генерация ответа | 2–8 с | `ANSWER_MAX_TOKENS`, длина ответа |

Дальше без смены модели/железа выигрыш — единицы процентов. Для собеса: BlackHole на **интервьюера**, `STT_LATENCY=balanced`, `WHISPER_PROMPT_MODE=tech`, `DEEPSEEK_MODEL=deepseek-chat`.

**Совет:** при старте `copilot` модель греется в фоне; **Начать прослушивание** — включает каналы STT.

Если тормозит: `WHISPER_MODEL_SIZE=small` или `STT_LATENCY=fast` + `WHISPER_BEAM_SIZE=1`.

| `WHISPER_MODEL_SIZE` | Когда |
|----------------------|--------|
| `small` | пресет `fast` / `balanced` (по умолчанию) |
| `medium` | если `small` путает слова |
| `large-v3` | `STT_LATENCY=quality`, максимум точности |
| `base` / `tiny` | только для экспериментов, хуже RU |

### Русская речь + английские термины (Kafka, GIL, Redis, …)

Whisper склонен писать термины **кириллицей** («кавка», «гил»). В sidecar **без хардкода** отдельных брендов:

1. **`WHISPER_PROMPT_MODE=tech`** (дефолт) — короткий prompt: IT-контекст, термины **латиницей**, без списка Kafka/Redis (длинный список эхоится на тишине).
2. **`STT_ROLLING=1`** — видишь текст по ходу; финал с `beam=3` + `WHISPER_GLOSSARY_FIXES`.
3. **`WHISPER_GLOSSARY_FIXES=1`** — пост-замена частых RU-искажений (GIL, Redis, …), не отдельных брендов.
4. Свой prompt: `WHISPER_INITIAL_PROMPT="…"` — короткая фраза, без перечисления слов.
5. Если мало: `WHISPER_PROMPT_MODE=interview` (длинный prompt) или `WHISPER_MODEL_SIZE=medium` / `STT_LATENCY=quality`.
6. Отключить глоссарий: `WHISPER_GLOSSARY_FIXES=0` — только сырой Whisper.

Облачный вариант (если нужен): `STT_PROVIDER=openai`, `OPENAI_API_KEY=…`, `pip install -e ".[audio,openai]"`.

Проверка устройств:

```bash
python -c "from copilot.audio_devices import list_input_devices; print(*list_input_devices(), sep='\n')"
```

### Пресеты endpointing (`AUDIO_PRESET`)

Практика voice agents: подстраивать **silence / EOU** под сценарий, а не один порог на всё.

| Пресет | Когда | `[Я]` silence | BlackHole silence |
|--------|--------|---------------|-------------------|
| `call` | Созвон, Brio + BlackHole | ~1.05 с | ~0.55 с |
| `solo` | Только микрофон | ~0.72 с | — |
| `fast` | Минимальная пауза | ~0.65 с | ~0.38 с |

```bash
AUDIO_PRESET=call
# STT_FINAL_DEBOUNCE_SEC=4      # не дублировать одинаковый финал
# STT_MIN_WORDS_FINAL_SELF=3    # или фраза с «?»
```

Явные `AUDIO_SILENCE_SEC_SELF` / `AUDIO_SILENCE_SEC` **перебивают** пресет.

### Тайминги пайплайна (тюнинг latency)

После каждого ответа (⌘↩ / auto) можно печатать разложение задержек:

```bash
COPILOT_TIMING=1
# COPILOT_TIMING_JSONL=1   # опционально → data/session-timing.jsonl
```

Пример: `[copilot] timing: stt=420ms llm_ttft=890ms total=1.3s (deepseek, hotkey, self)`.

Метрики также попадают в `data/sessions/<stamp>/turns.jsonl` при каждом ответе (см. [copilot-workflow.md](copilot-workflow.md#архив-сессий)).

Подробнее: [voice-pipeline.md](voice-pipeline.md), план работ: [voice-pipeline-roadmap.md](voice-pipeline-roadmap.md).

## 6. Разрешения macOS

- **Микрофон** — для процесса Python/Terminal, если записываешь с микрофона
- Для BlackHole обычно достаточно доступа к аудиоустройству при первом запуске `sounddevice`

## 7. Пока без BlackHole

Sidecar запишет **системный ввод по умолчанию** (часто только микрофон). Реплики интервьюера из Zoom **не попадут** в транскрипт — только то, что слышит микрофон (эхо/твой голос). Для собеса нужен BlackHole.
