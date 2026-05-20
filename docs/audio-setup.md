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
WHISPER_PROMPT_MODE=tech  # tech — латиница для IT; general — HR; interview — макс.
WHISPER_BEAM_SIZE=5
WHISPER_CONDITION_PREVIOUS=1
WHISPER_PATIENCE=1.0
WHISPER_TEMPERATURE=0,0.2
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

Критичный путь: **пауза в речи → сегмент → Whisper → `print_interviewer_transcript`**.

| Переменная | `fast` | `balanced` (собес) | Назначение |
|------------|--------|---------------------|------------|
| `STT_LATENCY` | `fast` | `balanced` | Пресет; `quality` — длинные паузы + VAD |
| `AUDIO_SILENCE_SEC` | ~0.42 | ~0.55 | Тишина перед STT (интервьюер / BlackHole) |
| `AUDIO_SILENCE_SEC_SELF` | ~0.72 | ~0.85 | Микрофон `[Я]` — дольше, чтобы не резать фразу |
| `AUDIO_MAX_SEGMENT_SEC_SELF` | ~6 | ~8 | Макс. длина фразы с Brio |
| `AUDIO_MAX_SEGMENT_SEC` | ~3.5 | ~5 | Срез длинного монолога без паузы |
| `WHISPER_MODEL_SIZE` | `small` | `small` | Явно переопределяет пресет; `quality` → `large-v3` |
| `WHISPER_BEAM_SIZE` | 3 | 5 | Больше beam → точнее EN-термины в русской речи |
| `WHISPER_CONDITION_PREVIOUS` | 0 | 1 | Контекст между сегментами — стабильнее латиница |
| `WHISPER_PATIENCE` | 0 | 1.0 | Точнее beam search на редких словах |
| `WHISPER_TEMPERATURE` | `0` | `0,0.2` | Fallback при низкой уверенности |
| `WHISPER_VAD_FILTER` | 0 | 0 | VAD в Whisper дублирует сегментацию listener |
| `WHISPER_PROMPT_MODE` | `tech` | `tech` | `tech` — IT без списка брендов; `interview` — длинный prompt; `general` — HR |
| `TERMINAL_SHOW_SELF` | `1` | `1` | Печатать реплики `[Я]` в терминал |

STT выполняется **в фоновом потоке** — запись с BlackHole не блокируется на время Whisper.

Фильтр галлюцинаций Whisper на тишине («редактор субтитров…») — `stt_filter.py`, не попадает в транскрипт.

### Пайплайн (интервьюер → DeepSeek)

1. BlackHole / вход → сегмент по паузе (~0.42 с) или срез ~3.5 с речи.
2. **faster-whisper** (async) → `transcript.md` + терминал («Интервьюер»).
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
| Пауза до сегмента | ~0.4 с | Физика речи; меньше — обрезка слов |
| Whisper `small` int8 | 1–3 с / сегмент | CPU; `medium` точнее, медленнее |
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
2. **`STT_LATENCY=balanced`** — `beam_size=5`, `condition_on_previous`, `patience`, `temperature=(0,0.2)`.
3. **`WHISPER_GLOSSARY_FIXES=1`** — пост-замена частых RU-искажений (GIL, Redis, …), не отдельных брендов.
4. Свой prompt: `WHISPER_INITIAL_PROMPT="…"` — короткая фраза, без перечисления слов.
5. Если мало: `WHISPER_PROMPT_MODE=interview` (длинный prompt) или `WHISPER_MODEL_SIZE=medium` / `STT_LATENCY=quality`.
6. Отключить глоссарий: `WHISPER_GLOSSARY_FIXES=0` — только сырой Whisper.

Облачный вариант (если нужен): `STT_PROVIDER=openai`, `OPENAI_API_KEY=…`, `pip install -e ".[audio,openai]"`.

Проверка устройств:

```bash
python -c "from copilot.audio_devices import list_input_devices; print(*list_input_devices(), sep='\n')"
```

## 6. Разрешения macOS

- **Микрофон** — для процесса Python/Terminal, если записываешь с микрофона
- Для BlackHole обычно достаточно доступа к аудиоустройству при первом запуске `sounddevice`

## 7. Пока без BlackHole

Sidecar запишет **системный ввод по умолчанию** (часто только микрофон). Реплики интервьюера из Zoom **не попадут** в транскрипт — только то, что слышит микрофон (эхо/твой голос). Для собеса нужен BlackHole.
