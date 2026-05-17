from __future__ import annotations

from copilot.cursor_bridge import _extract_sdk_error


def test_extract_sdk_error_from_tail() -> None:
    stderr = "x" * 10000 + '\nConfigurationError: Cannot use this model: bad-model\n'
    msg = _extract_sdk_error(stderr, "")
    assert "Cannot use this model" in msg
    assert len(msg) < 900
