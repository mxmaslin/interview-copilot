from __future__ import annotations

import copilot.clipboard_image as ci


def test_image_fingerprint_stable() -> None:
    data = b"\x89PNG\r\n\x1a\nfake"
    assert ci.image_fingerprint(data) == ci.image_fingerprint(data)
    assert ci.image_fingerprint(data) != ci.image_fingerprint(data + b"x")


def test_normalize_png_unchanged() -> None:
    data = b"\x89PNG\r\n\x1a\npayload"
    out, mime = ci.normalize_clipboard_image(data, "image/png")
    assert out == data
    assert mime == "image/png"


def test_normalize_jpeg_unchanged() -> None:
    data = b"\xff\xd8\xff"
    out, mime = ci.normalize_clipboard_image(data, "image/jpeg")
    assert out == data
    assert mime == "image/jpeg"
