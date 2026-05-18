from __future__ import annotations

import copilot.stt as stt


def test_release_local_model_noop() -> None:
    stt._local_model = None
    stt.release_local_model()
