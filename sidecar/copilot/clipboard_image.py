from __future__ import annotations

import hashlib

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8"


def pasteboard_change_count() -> int:
    from AppKit import NSPasteboard

    return int(NSPasteboard.generalPasteboard().changeCount())


def _read_raw() -> tuple[bytes, str] | None:
    from AppKit import NSPasteboard

    pb = NSPasteboard.generalPasteboard()
    for uti, mime in (
        ("public.png", "image/png"),
        ("public.jpeg", "image/jpeg"),
        ("public.tiff", "image/tiff"),
    ):
        data = pb.dataForType_(uti)
        if data is not None and len(data) > 0:
            return bytes(data), mime
    return None


def _tiff_to_png(data: bytes) -> bytes | None:
    from AppKit import NSBitmapImageRep

    rep = NSBitmapImageRep.imageRepWithData_(data)
    if rep is None:
        return None
    png = rep.representationUsingType_properties_(
        NSBitmapImageRep.NSPNGFileType, None
    )
    if png is None:
        return None
    return bytes(png)


def normalize_clipboard_image(data: bytes, mime: str) -> tuple[bytes, str]:
    if data.startswith(_PNG):
        return data, "image/png"
    if data.startswith(_JPEG):
        return data, "image/jpeg"
    if mime == "image/tiff" or data[:4] in (b"II*\x00", b"MM\x00*"):
        png = _tiff_to_png(data)
        if png:
            return png, "image/png"
    return data, mime


def read_clipboard_image() -> tuple[bytes, str] | None:
    """PNG/JPEG/TIFF из буфера (⌘⌃⇧4 на macOS)."""
    raw = _read_raw()
    if raw is None:
        return None
    data, mime = raw
    return normalize_clipboard_image(data, mime)


def image_fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clear_clipboard() -> bool:
    """Очистить общий буфер обмена (после обработки скриншота)."""
    from AppKit import NSPasteboard

    pb = NSPasteboard.generalPasteboard()
    return bool(pb.clearContents())
