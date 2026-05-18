from __future__ import annotations

import logging
import os
import warnings

from .config import hf_hub_token, load_dotenv

_configured = False


def configure_hf_hub() -> None:
    """Токен HF из .env и тише логи huggingface_hub (модель faster-whisper)."""
    global _configured
    if _configured:
        return
    _configured = True

    load_dotenv()
    token = hf_hub_token()
    if token:
        os.environ.setdefault("HF_TOKEN", token)
        os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", token)

    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    warnings.filterwarnings(
        "ignore",
        message=".*unauthenticated requests to the HF Hub.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=".*HF_TOKEN.*",
        module="huggingface_hub.*",
    )

    for name in ("huggingface_hub", "huggingface_hub.utils", "huggingface_hub.file_download"):
        logging.getLogger(name).setLevel(logging.ERROR)
