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

## 4. Yandex Telemost / Google Meet

Аналогично: **вывод звука** созвона → BlackHole (или Multi-Output с BlackHole).

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
WHISPER_MODEL_SIZE=small
WHISPER_COMPUTE_TYPE=int8
WHISPER_DEVICE=cpu
AUDIO_INPUT_INTERVIEWER=BlackHole
AUDIO_INPUT_SELF=Brio
# AUDIO_SAMPLE_RATE — опционально; sidecar сам берёт native rate устройства (обычно 48000)
```

Первый запуск скачает модель **small** (~500 MB) — один раз, 1–3 минуты. Дальше сегменты распознаются на машине, **без API-ключей**.

| `WHISPER_MODEL_SIZE` | Когда |
|----------------------|--------|
| `small` | баланс скорость/качество (рекомендуется) |
| `base` | ещё быстрее, чуть хуже RU |
| `medium` | если путает термины, Air может греться |

Облачный вариант (если нужен): `STT_PROVIDER=openai`, `OPENAI_API_KEY=…`, `pip install -e ".[audio,openai]"`.

В menubar **CP → Начать прослушивание (STT)** — при старте модель подгружается в фоне.

Проверка устройств:

```bash
python -c "from copilot.audio_devices import list_input_devices; print(*list_input_devices(), sep='\n')"
```

## 6. Разрешения macOS

- **Микрофон** — для процесса Python/Terminal, если записываешь с микрофона
- Для BlackHole обычно достаточно доступа к аудиоустройству при первом запуске `sounddevice`

## 7. Пока без BlackHole

Sidecar запишет **системный ввод по умолчанию** (часто только микрофон). Реплики интервьюера из Zoom **не попадут** в транскрипт — только то, что слышит микрофон (эхо/твой голос). Для собеса нужен BlackHole.
