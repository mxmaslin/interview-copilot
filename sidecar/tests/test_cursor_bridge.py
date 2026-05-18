from __future__ import annotations

import copilot.cursor_bridge as bridge
from copilot.config import DATA_DIR
from copilot.cursor_bridge import _extract_sdk_error


def test_extract_sdk_error_from_tail() -> None:
    stderr = "x" * 10000 + '\nConfigurationError: Cannot use this model: bad-model\n'
    msg = _extract_sdk_error(stderr, "")
    assert "Cannot use this model" in msg
    assert len(msg) < 900


def test_extract_sdk_error_skips_minified_bundle() -> None:
    bundle = "function parseJSXAttributes(){}" + "x" * 50000
    stderr = bundle + "\nc [ConfigurationError]: Agent agent-1 not found\n"
    msg = _extract_sdk_error(stderr, "")
    assert "not found" in msg
    assert "parseJSX" not in msg
    assert len(msg) < 900


def test_solve_screenshot_stream_removes_payload(monkeypatch) -> None:
    payload_path = DATA_DIR / "screenshot-cursor-payload.json"
    if payload_path.exists():
        payload_path.unlink()

    def fake_stream(*_args, **_kwargs):
        assert payload_path.exists()
        return {"status": "finished", "text": "ok"}

    monkeypatch.setattr(bridge, "_run_node_stream", fake_stream)

    result = bridge.solve_screenshot_stream(b"png", on_delta=lambda _d: None)

    assert result["text"] == "ok"
    assert not payload_path.exists()
