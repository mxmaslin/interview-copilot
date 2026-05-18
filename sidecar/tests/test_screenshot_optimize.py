from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

import copilot.screenshot_optimize as so


def test_jpeg_encode_props_uses_appkit_constant() -> None:
    if sys.platform != "darwin":
        pytest.skip("AppKit only on macOS")
    props = so._jpeg_encode_props(0.85)
    assert len(props) == 1
    key = next(iter(props))
    assert "Compression" in str(key) or "compression" in str(key).lower()
    assert props[key] == 0.85


def test_optimize_disabled_passthrough(monkeypatch) -> None:
    monkeypatch.setattr(so, "screenshot_optimize_enabled", lambda: False)
    data = b"\x89PNG"
    assert so.optimize_screenshot_image(data, "image/png") == (data, "image/png")


def test_optimize_import_error_passthrough(monkeypatch) -> None:
    monkeypatch.setattr(so, "screenshot_optimize_enabled", lambda: True)
    monkeypatch.setattr(so, "screenshot_max_edge_px", lambda: 1280)

    def fake_import(name, *args, **kwargs):
        if name == "AppKit":
            raise ImportError("no AppKit")
        return __import__(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        data = b"raw"
        assert so.optimize_screenshot_image(data, "image/png") == (data, "image/png")


def test_optimize_returns_original_when_encode_fails(monkeypatch) -> None:
    monkeypatch.setattr(so, "screenshot_optimize_enabled", lambda: True)
    monkeypatch.setattr(so, "screenshot_max_edge_px", lambda: 0)

    fake_img = MagicMock()
    fake_img.size.return_value = (100, 100)
    fake_img.TIFFRepresentation.return_value = b"tiff"
    fake_rep = MagicMock()
    fake_rep.representationUsingType_properties_.return_value = None
    fake_nsimage = MagicMock()
    fake_nsimage.alloc.return_value.initWithData_.return_value = fake_img
    fake_nsbr = MagicMock()
    fake_nsbr.imageRepWithData_.return_value = fake_rep
    fake_appkit = MagicMock(
        NSImage=fake_nsimage,
        NSBitmapImageRep=fake_nsbr,
        NSJPEGFileType=3,
        NSPNGFileType=4,
        NSImageCompressionFactor="compression-key",
    )

    with patch.dict("sys.modules", {"AppKit": fake_appkit}):
        data = b"x" * 100
        out, mime = so.optimize_screenshot_image(data, "image/png")
    assert out == data
    assert mime == "image/png"
