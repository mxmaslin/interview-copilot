from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
TRANSCRIPT_PATH = DATA_DIR / "transcript.md"
ANSWERS_PATH = DATA_DIR / "answers.log"
CURSOR_AGENT_DIR = REPO_ROOT / "scripts" / "cursor-agent"
AGENT_STATE_PATH = DATA_DIR / "agent-state.json"

_dotenv_loaded = False


def load_dotenv() -> None:
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        _dotenv_loaded = True
        return
    try:
        from dotenv import load_dotenv as _load

        _load(env_file)
    except ImportError:
        pass
    _dotenv_loaded = True


def _env(name: str, default: str = "") -> str:
    if not _dotenv_loaded:
        load_dotenv()
    return os.environ.get(name, default).strip()


def cursor_api_key() -> str | None:
    key = _env("CURSOR_API_KEY")
    return key or None


def openai_api_key() -> str | None:
    key = _env("OPENAI_API_KEY")
    return key or None


def screenshot_openai_base_url() -> str | None:
    """OpenAI-compatible endpoint (ProxyAPI, OpenRouter, …) для vision-скринов."""
    url = _env("SCREENSHOT_OPENAI_BASE_URL") or _env("OPENAI_BASE_URL")
    return url or None


def anthropic_api_key() -> str | None:
    return _env("ANTHROPIC_API_KEY") or None


def anthropic_base_url() -> str | None:
    """Опционально: прокси с Anthropic API (если понадобится)."""
    return _env("ANTHROPIC_BASE_URL") or None


def audio_device_hint_interviewer() -> str:
    """Zoom/Meet/Telemost → BlackHole (или Multi-Output). Подстрока имени устройства."""
    return _env("AUDIO_INPUT_INTERVIEWER") or _env("AUDIO_INPUT_DEVICE", "BlackHole")


def audio_device_hint_self() -> str:
    """Твой микрофон (Brio и т.п.). Подстрока имени устройства."""
    return _env("AUDIO_INPUT_SELF", "Brio")


def audio_listen_interviewer() -> bool:
    return _env("AUDIO_ENABLE_INTERVIEWER", "1").lower() not in ("0", "false", "no")


def audio_listen_self() -> bool:
    return _env("AUDIO_ENABLE_SELF", "1").lower() not in ("0", "false", "no")


def answer_self_questions_mode() -> str:
    """
    Когда отвечать на реплики [Я] по ⌘↩.
    auto — соло (нет [Интервьюер] в транскрипте), CALL_MIC_MUTED=1
         или AUDIO_ENABLE_INTERVIEWER=0;
    always | never.
    """
    return _env("ANSWER_SELF_QUESTIONS", "auto").lower()


def call_mic_muted_on_call() -> bool:
    """Микрофон выключен в Zoom/Telegram — отвечать и на свои вопросы ([Я])."""
    return _env("CALL_MIC_MUTED", "0").lower() in ("1", "true", "yes")


def answer_interviewer_merge_max() -> int:
    """Сколько последних сегментов [Интервьюер] склеивать (BlackHole иначе тащит весь звонок)."""
    try:
        return max(1, int(_env("ANSWER_INTERVIEWER_MERGE_MAX", "2")))
    except ValueError:
        return 2


def answer_self_merge_max() -> int:
    try:
        return max(1, int(_env("ANSWER_SELF_MERGE_MAX", "1")))
    except ValueError:
        return 3


def answer_barge_in_speakers() -> frozenset[str]:
    """Каналы, при старте речи которых отменять in-flight ответ (voice-agent barge-in).

    0/false — выкл; interviewer — только [Интервьюер]; 1/all — оба канала.
    """
    raw = _env("ANSWER_BARGE_IN_ON_SPEECH", "interviewer").strip().lower()
    if raw in ("0", "false", "no", "off", ""):
        return frozenset()
    if raw in ("1", "true", "yes", "all", "both"):
        return frozenset({"interviewer", "self"})
    if raw == "interviewer":
        return frozenset({"interviewer"})
    if raw == "self":
        return frozenset({"self"})
    return frozenset()


def telegram_input_enabled() -> bool:
    return _env("TELEGRAM_INPUT_ENABLED", "0").lower() not in ("0", "false", "no")


def telegram_bot_token() -> str | None:
    key = _env("TELEGRAM_BOT_TOKEN")
    return key or None


def telegram_allowed_chat_ids() -> set[int]:
    """Список chat_id через запятую (личный чат с @userinfobot)."""
    raw = _env("TELEGRAM_CHAT_IDS") or _env("TELEGRAM_CHAT_ID")
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


def audio_device_hint() -> str:
    """Устаревшее имя — интервьюер."""
    return audio_device_hint_interviewer()


def stt_provider() -> str:
    """local = faster-whisper на Mac (без ключей); openai = Whisper API."""
    return _env("STT_PROVIDER", "local").lower()


def hf_hub_token() -> str | None:
    """Опционально: токен Hugging Face (скачивание Whisper, выше лимиты HF Hub)."""
    key = _env("HF_TOKEN") or _env("HUGGING_FACE_HUB_TOKEN")
    return key or None


def whisper_api_model() -> str:
    return _env("WHISPER_MODEL", "whisper-1")


def stt_latency_preset() -> str:
    """fast | balanced | quality — пресет задержки STT (см. docs/audio-setup.md)."""
    return _env("STT_LATENCY", "fast").lower()


def whisper_local_size() -> str:
    """tiny | base | small | medium | large-v3 …"""
    explicit = _env("WHISPER_MODEL_SIZE")
    if explicit:
        return explicit
    preset = stt_latency_preset()
    if preset == "quality":
        return "large-v3"
    if preset == "balanced":
        return "small"
    return "small"


def whisper_compute_type() -> str:
    """int8 быстрее на Apple Silicon; float16 если хватает RAM."""
    return _env("WHISPER_COMPUTE_TYPE", "int8")


def whisper_device() -> str:
    return _env("WHISPER_DEVICE", "cpu")


def whisper_cpu_threads() -> int:
    try:
        return int(_env("WHISPER_CPU_THREADS", "0"))
    except ValueError:
        return 0


def stt_rolling_enabled() -> bool:
    """Частичный STT во время речи (короткие сегменты + быстрый decode)."""
    return _env("STT_ROLLING", "1").lower() not in ("0", "false", "no")


def whisper_beam_size(*, live: bool = False) -> int:
    if live:
        return 1
    if stt_fast_final_decode():
        return 1
    explicit = _env("WHISPER_BEAM_SIZE")
    if explicit:
        try:
            return int(explicit)
        except ValueError:
            pass
    preset = stt_latency_preset()
    if preset == "quality":
        return 5
    if preset == "balanced":
        return 3
    return 1


def whisper_patience(*, live: bool = False) -> float:
    """Beam search patience (>0 точнее на редких словах, чуть медленнее)."""
    if live:
        return 0.0
    explicit = _env("WHISPER_PATIENCE")
    if explicit:
        try:
            return max(0.0, float(explicit))
        except ValueError:
            pass
    preset = stt_latency_preset()
    if preset == "quality":
        return 1.2
    if preset == "balanced":
        return 0.0
    return 0.0


def whisper_temperature(*, live: bool = False) -> float | tuple[float, ...]:
    if live:
        return 0.0
    """0.0 — жадно; (0.0, 0.2) — fallback при низкой уверенности (лучше EN-термины)."""
    explicit = _env("WHISPER_TEMPERATURE")
    if explicit:
        parts = [p.strip() for p in explicit.split(",") if p.strip()]
        if len(parts) > 1:
            return tuple(float(p) for p in parts)
        if parts:
            return float(parts[0])
    preset = stt_latency_preset()
    if preset == "quality":
        return (0.0, 0.2)
    return 0.0


def whisper_prompt_mode() -> str:
    """general | tech | interview — см. stt_prompt.py."""
    return _env("WHISPER_PROMPT_MODE", "tech").lower()


def whisper_initial_prompt() -> str:
    """Полная замена дефолтного prompt (см. stt_prompt.py)."""
    return _env("WHISPER_INITIAL_PROMPT")


def whisper_glossary_fixes() -> bool:
    """Пост-правка типичных RU-искажений терминов (GIL, Redis, …)."""
    return _env("WHISPER_GLOSSARY_FIXES", "1").lower() not in ("0", "false", "no")


def whisper_condition_on_previous(*, live: bool = False) -> bool:
    """Контекст между сегментами — стабильнее латиница в терминах."""
    if live:
        return False
    explicit = _env("WHISPER_CONDITION_PREVIOUS", "")
    if explicit:
        return explicit.lower() not in ("0", "false", "no")
    return stt_latency_preset() == "quality"


def whisper_vad_filter() -> bool:
    explicit = _env("WHISPER_VAD_FILTER", "")
    if explicit:
        return explicit.lower() not in ("0", "false", "no")
    return stt_latency_preset() == "quality"


def sample_rate() -> int:
    try:
        return int(_env("AUDIO_SAMPLE_RATE", "16000"))
    except ValueError:
        return 16000


def audio_preset() -> str:
    """call | solo | fast | interview — пресеты endpointing (см. docs/audio-setup.md)."""
    return _env("AUDIO_PRESET", "").strip().lower()


def stt_pending_flush_sec() -> float:
    """Через столько с после обрезка STT ([Я]) — дописать в transcript без новой речи."""
    try:
        return max(0.0, float(_env("STT_PENDING_FLUSH_SEC", "1.2")))
    except ValueError:
        return 1.2


def stt_fast_final_decode() -> bool:
    """Финальный Whisper с beam=1 (быстрее, чуть грубее)."""
    explicit = _env("STT_FAST_FINAL", "")
    if explicit:
        return explicit.lower() not in ("0", "false", "no")
    return stt_latency_preset() == "fast"


def stt_final_debounce_sec() -> float:
    try:
        return max(0.5, float(_env("STT_FINAL_DEBOUNCE_SEC", "4")))
    except ValueError:
        return 4.0


def stt_min_words_final_self() -> int:
    try:
        return max(1, int(_env("STT_MIN_WORDS_FINAL_SELF", "2")))
    except ValueError:
        return 3


def silence_seconds(*, speaker: str = "interviewer") -> float:
    preset = audio_preset()
    if speaker == "self":
        explicit_self = _env("AUDIO_SILENCE_SEC_SELF")
        if explicit_self:
            try:
                return float(explicit_self)
            except ValueError:
                pass
        if preset == "call":
            return 0.78
        if preset == "solo":
            return 0.68
        if preset == "fast":
            return 0.58
        if preset == "interview":
            return 0.62
        preset_latency = stt_latency_preset()
        if preset_latency == "quality":
            return 1.1
        if preset_latency == "balanced":
            return 0.68
        return 0.62

    explicit = _env("AUDIO_SILENCE_SEC")
    if explicit:
        try:
            return float(explicit)
        except ValueError:
            pass
    if preset == "call":
        return 0.55
    if preset == "solo":
        return 0.42
    latency = stt_latency_preset()
    if latency == "quality":
        return 1.0
    if latency == "balanced":
        return 0.45
    return 0.38  # fast: короче пауза → раньше финальный сегмент


def min_speech_seconds() -> float:
    try:
        return float(_env("AUDIO_MIN_SPEECH_SEC", "0.25"))
    except ValueError:
        return 0.25


def audio_block_ms() -> int:
    try:
        return max(20, int(_env("AUDIO_BLOCK_MS", "50")))
    except ValueError:
        return 50


def max_segment_seconds(*, speaker: str = "interviewer") -> float:
    """Макс. длина непрерывной речи без паузы — принудительный STT (0 = выкл)."""
    if speaker == "self":
        explicit_self = _env("AUDIO_MAX_SEGMENT_SEC_SELF")
        if explicit_self:
            try:
                return float(explicit_self)
            except ValueError:
                pass
        preset = stt_latency_preset()
        if preset == "quality":
            return 0.0
        if preset == "balanced":
            return 8.0
        return 6.0

    explicit = _env("AUDIO_MAX_SEGMENT_SEC")
    if explicit:
        try:
            return float(explicit)
        except ValueError:
            pass
    preset = stt_latency_preset()
    if preset == "quality":
        return 0.0
    if stt_rolling_enabled():
        rolling = _env("AUDIO_ROLLING_SEC")
        if rolling:
            try:
                return max(1.0, float(rolling))
            except ValueError:
                pass
        if preset == "balanced":
            return 2.0
        return 1.8
    if preset == "balanced":
        return 5.0
    return 3.5


def audio_prefer_16k() -> bool:
    return _env("AUDIO_PREFER_16K", "1").lower() not in ("0", "false", "no")


def answer_auto_enabled() -> bool:
    """После готовой реплики в транскрипте — ответ без ⌘↩."""
    return _env("ANSWER_AUTO", "1").lower() not in ("0", "false", "no")


def answer_auto_delay_sec() -> float:
    """Пауза после STT перед авто-ответом (сбрасывается при новой реплике)."""
    try:
        return max(0.0, float(_env("ANSWER_AUTO_DELAY_SEC", "0.2")))
    except ValueError:
        return 0.2


def copilot_timing_enabled() -> bool:
    """Печать stt/llm таймингов в терминал после ответа (см. docs/voice-pipeline.md)."""
    return _env("COPILOT_TIMING", "0").lower() in ("1", "true", "yes", "on")


def copilot_timing_jsonl_enabled() -> bool:
    """Append таймингов в data/session-timing.jsonl."""
    if not copilot_timing_enabled():
        return False
    return _env("COPILOT_TIMING_JSONL", "0").lower() in ("1", "true", "yes", "on")


def copilot_timing_hints_enabled() -> bool:
    """Подсказки по тюнингу после timing (фаза 5)."""
    if not copilot_timing_enabled():
        return False
    return _env("COPILOT_TIMING_HINTS", "1").lower() not in ("0", "false", "no")


def copilot_stt_slow_ms() -> int:
    try:
        return max(200, int(_env("COPILOT_STT_SLOW_MS", "800")))
    except ValueError:
        return 800


def copilot_llm_slow_ms() -> int:
    try:
        return max(300, int(_env("COPILOT_LLM_SLOW_MS", "1500")))
    except ValueError:
        return 1500


def stt_live_min_words() -> int:
    """Не печатать live в терминал, пока в rolling < N слов (0 = без порога)."""
    try:
        return max(0, int(_env("STT_LIVE_MIN_WORDS", "2")))
    except ValueError:
        return 2


def answer_provider() -> str:
    """cursor | openai | deepseek."""
    return _env("ANSWER_PROVIDER", "cursor").lower()


def deepseek_api_key() -> str | None:
    key = _env("DEEPSEEK_API_KEY")
    return key or None


def deepseek_api_base() -> str:
    return _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def deepseek_answer_model() -> str:
    """deepseek-chat = V3 без chain-of-thought (быстрее). deepseek-reasoner = R1 (медленнее)."""
    return _env("DEEPSEEK_MODEL", "deepseek-chat")


def cursor_model() -> str:
    """Slug для логов; auto → ~/.cursor/cli-config.json (selectedModel)."""
    from .cursor_model_resolve import cursor_model_label

    return cursor_model_label()


def answer_context_chars() -> int:
    try:
        return int(_env("CURSOR_ANSWER_CONTEXT_CHARS", "800"))
    except ValueError:
        return 800


def answer_minimal_context() -> bool:
    """Меньше токенов в промпте → быстрее первый токен DeepSeek/OpenAI."""
    explicit = _env("ANSWER_MINIMAL_CONTEXT", "")
    if explicit:
        return explicit.lower() not in ("0", "false", "no")
    legacy = _env("CURSOR_ANSWER_MINIMAL", "")
    if legacy:
        return legacy.lower() not in ("0", "false", "no")
    return True


def answer_pause_audio() -> bool:
    """
    Останавливать STT на время ⌘↩.
    auto (default): только ANSWER_PROVIDER=cursor (локальный SDK).
    always | never — принудительно.
    """
    mode = _env("ANSWER_PAUSE_AUDIO", "auto").lower()
    if mode in ("0", "false", "no", "never"):
        return False
    if mode in ("1", "true", "yes", "always"):
        return True
    return answer_provider() == "cursor"


def answer_openai_model() -> str:
    return _env("OPENAI_ANSWER_MODEL", "gpt-4o-mini")


def answer_openai_max_tokens() -> int:
    return answer_max_tokens()


def answer_max_tokens() -> int:
    try:
        return int(_env("ANSWER_MAX_TOKENS") or _env("OPENAI_ANSWER_MAX_TOKENS", "450"))
    except ValueError:
        return 450


def answer_request_timeout() -> float:
    """Секунды на запрос DeepSeek/OpenAI (зависший запрос не блокирует меню навсегда)."""
    try:
        return float(_env("ANSWER_REQUEST_TIMEOUT", "120"))
    except ValueError:
        return 120.0


def cursor_agent_chat_id_env() -> str | None:
    """UUID чата Agents, который пользователь создал вручную (New Agent)."""
    val = _env("CURSOR_AGENT_CHAT_ID")
    return val or None


def cursor_agent_mirror() -> bool:
    """
    Экспериментально: push ответа в привязанный чат (cursor agent --resume).
    Нужен chatId от пользователя; sidecar не создаёт агента в UI.
    """
    return _env("CURSOR_AGENT_MIRROR", "0").lower() not in ("0", "false", "no")


def cursor_agent_auto_start() -> bool:
    """Устарело: автосоздание агента в UI не поддерживается. Оставлено для совместимости."""
    return _env("CURSOR_AGENT_AUTO_START", "0").lower() not in ("0", "false", "no")


def cursor_agent_fresh_each_run() -> bool:
    """При запуске copilot сбросить привязку chatId в agent-state.json."""
    return _env("CURSOR_AGENT_FRESH", "0").lower() not in ("0", "false", "no")


def cursor_open_answer_file() -> bool:
    """Открывать data/last-answer.md в редакторе (по умолчанию выкл — ответ в терминале)."""
    return _env("CURSOR_OPEN_ANSWER_FILE", "0").lower() not in ("0", "false", "no")


def terminal_show_interviewer_stt() -> bool:
    """Печатать реплики интервьюера в терминал по мере STT (во время интервью)."""
    return _env("TERMINAL_SHOW_INTERVIEWER", "1").lower() not in ("0", "false", "no")


def terminal_show_self_stt() -> bool:
    """Печатать свои реплики (микрофон) в терминал — иначе только уведомление macOS."""
    return _env("TERMINAL_SHOW_SELF", "1").lower() not in ("0", "false", "no")


def audio_rms_threshold(speaker: str) -> float:
    """Порог громкости для сегментации (ниже для self — тихий микрофон)."""
    key = (
        "AUDIO_RMS_THRESHOLD_SELF"
        if speaker == "self"
        else "AUDIO_RMS_THRESHOLD_INTERVIEWER"
    )
    default = "0.008" if speaker == "self" else "0.012"
    try:
        return float(_env(key) or _env("AUDIO_RMS_THRESHOLD", default))
    except ValueError:
        return 0.008 if speaker == "self" else 0.012


def terminal_answer_stream() -> bool:
    """Печатать ответ ⌘↩ в терминал по чанкам (OpenAI/DeepSeek stream)."""
    return _env("TERMINAL_ANSWER_STREAM", "1").lower() not in ("0", "false", "no")


def copilot_session_warmup_enabled() -> bool:
    """При старте menubar copilot — фоновый прогрев STT / API / SDK."""
    return _env("COPILOT_SESSION_WARMUP", "1").lower() not in ("0", "false", "no")


def screenshot_solve_enabled() -> bool:
    """⌘⌃⇧4 → буфер → vision API (pasteboard watcher)."""
    return _env("SCREENSHOT_SOLVE_ENABLED", "1").lower() not in ("0", "false", "no")


def screenshot_latency_preset() -> str:
    """fast (default) | balanced — задержка watcher и сжатие картинки."""
    return _env("SCREENSHOT_LATENCY", "fast").lower()


def screenshot_poll_sec() -> float:
    explicit = _env("SCREENSHOT_POLL_SEC")
    if explicit:
        try:
            return float(explicit)
        except ValueError:
            pass
    if screenshot_latency_preset() == "balanced":
        return 0.35
    return 0.12


def screenshot_debounce_sec() -> float:
    """Пауза после changeCount, пока macOS допишет PNG в буфер."""
    explicit = _env("SCREENSHOT_DEBOUNCE_SEC") or _env("SCREENSHOT_SOLVE_DEBOUNCE_SEC")
    if explicit:
        try:
            return float(explicit)
        except ValueError:
            pass
    if screenshot_latency_preset() == "balanced":
        return 0.25
    return 0.08


def screenshot_max_edge_px() -> int:
    explicit = _env("SCREENSHOT_MAX_EDGE_PX")
    if explicit:
        try:
            return int(explicit)
        except ValueError:
            pass
    if screenshot_latency_preset() == "balanced":
        return 1920
    return 1024


def screenshot_jpeg_quality() -> float:
    explicit = _env("SCREENSHOT_JPEG_QUALITY")
    if explicit:
        try:
            return float(explicit)
        except ValueError:
            pass
    if screenshot_latency_preset() == "balanced":
        return 0.85
    return 0.78


def screenshot_reuse_agent() -> bool:
    """
    Один SDK-агент на все скриншоты (resume между вызовами solve-screenshot).
    SCREENSHOT_REUSE_AGENT=0 — новый агент на каждый кадр (медленнее).
    """
    explicit = _env("SCREENSHOT_REUSE_AGENT")
    if explicit:
        return explicit.lower() not in ("0", "false", "no")
    for name in ("SCREENSHOT_AGENT_FRESH", "SCREENSHOT_FRESH_AGENT"):
        fresh = _env(name)
        if fresh and fresh.lower() in ("1", "true", "yes"):
            return False
    return True


def screenshot_optimize_enabled() -> bool:
    return _env("SCREENSHOT_OPTIMIZE", "1").lower() not in ("0", "false", "no")


def screenshot_warm_agent() -> bool:
    """При старте copilot создать/восстановить SDK-агента для скриншотов."""
    return _env("SCREENSHOT_WARM_AGENT", "1").lower() not in ("0", "false", "no")


def screenshot_minimal_prompt() -> bool:
    explicit = _env("SCREENSHOT_MINIMAL_PROMPT")
    if explicit:
        return explicit.lower() not in ("0", "false", "no")
    return screenshot_latency_preset() == "fast"


def screenshot_answer_provider() -> str:
    """
    Провайдер vision для скриншота.
    deepseek-chat не принимает image_url → при ANSWER_PROVIDER=deepseek
    автоматически cursor (если CURSOR_API_KEY) или openai.
    """
    explicit = _env("SCREENSHOT_ANSWER_PROVIDER").lower()
    if explicit:
        return explicit
    base = answer_provider()
    if base != "deepseek":
        return base
    if anthropic_api_key():
        return "anthropic"
    if cursor_api_key():
        return "cursor"
    if openai_api_key():
        return "openai"
    return "deepseek"


def screenshot_vision_model(provider: str) -> str:
    explicit = _env("SCREENSHOT_VISION_MODEL") or _env("SCREENSHOT_SOLVE_MODEL")
    if explicit:
        return explicit
    if provider == "openai":
        return _env("SCREENSHOT_OPENAI_MODEL", "gpt-4o-mini")
    if provider == "anthropic":
        return _env("SCREENSHOT_ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    if provider == "deepseek":
        return _env("SCREENSHOT_DEEPSEEK_MODEL", "deepseek-chat")
    if provider == "cursor":
        return cursor_model()
    return "gpt-4o-mini"


def screenshot_solve_also_last_answer() -> bool:
    """Дублировать ответ ещё в data/last-answer.md."""
    return _env("SCREENSHOT_SOLVE_ALSO_LAST_ANSWER", "1").lower() not in (
        "0",
        "false",
        "no",
    )


def screenshot_clear_clipboard() -> bool:
    """Очистить буфер после успешного ответа по скриншоту."""
    return _env("SCREENSHOT_CLEAR_CLIPBOARD", "1").lower() not in (
        "0",
        "false",
        "no",
    )
