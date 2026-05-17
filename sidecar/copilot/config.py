from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
TRANSCRIPT_PATH = DATA_DIR / "transcript.md"
ANSWERS_PATH = DATA_DIR / "answers.log"
CURSOR_AGENT_DIR = REPO_ROOT / "scripts" / "cursor-agent"
AGENT_STATE_PATH = DATA_DIR / "agent-state.json"


def load_dotenv() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv as _load

        _load(env_file)
    except ImportError:
        pass


def _env(name: str, default: str = "") -> str:
    load_dotenv()
    return os.environ.get(name, default).strip()


def cursor_api_key() -> str | None:
    key = _env("CURSOR_API_KEY")
    return key or None


def openai_api_key() -> str | None:
    key = _env("OPENAI_API_KEY")
    return key or None


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


def audio_device_hint() -> str:
    """Устаревшее имя — интервьюер."""
    return audio_device_hint_interviewer()


def stt_provider() -> str:
    """local = faster-whisper на Mac (без ключей); openai = Whisper API."""
    return _env("STT_PROVIDER", "local").lower()


def whisper_api_model() -> str:
    return _env("WHISPER_MODEL", "whisper-1")


def whisper_local_size() -> str:
    """tiny | base | small | medium | large-v3 …"""
    return _env("WHISPER_MODEL_SIZE", "small")


def whisper_compute_type() -> str:
    """int8 быстрее на Apple Silicon; float16 если хватает RAM."""
    return _env("WHISPER_COMPUTE_TYPE", "int8")


def whisper_device() -> str:
    return _env("WHISPER_DEVICE", "cpu")


def sample_rate() -> int:
    try:
        return int(_env("AUDIO_SAMPLE_RATE", "16000"))
    except ValueError:
        return 16000


def silence_seconds() -> float:
    try:
        return float(_env("AUDIO_SILENCE_SEC", "1.2"))
    except ValueError:
        return 1.2


def min_speech_seconds() -> float:
    try:
        return float(_env("AUDIO_MIN_SPEECH_SEC", "0.4"))
    except ValueError:
        return 0.4


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
    # composer-2-fast нет в Cursor API — см. Cursor.models.list()
    return _env("CURSOR_MODEL", "composer-2")


def answer_context_chars() -> int:
    try:
        return int(_env("CURSOR_ANSWER_CONTEXT_CHARS", "800"))
    except ValueError:
        return 800


def answer_minimal_context() -> bool:
    return _env("CURSOR_ANSWER_MINIMAL", "0").lower() in ("1", "true", "yes")


def answer_openai_model() -> str:
    return _env("OPENAI_ANSWER_MODEL", "gpt-4o-mini")


def answer_openai_max_tokens() -> int:
    return answer_max_tokens()


def answer_max_tokens() -> int:
    try:
        return int(_env("ANSWER_MAX_TOKENS") or _env("OPENAI_ANSWER_MAX_TOKENS", "450"))
    except ValueError:
        return 450


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
