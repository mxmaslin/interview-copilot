from __future__ import annotations

from .config import screenshot_jpeg_quality, screenshot_max_edge_px, screenshot_optimize_enabled
from .interview_quiet import log


def _jpeg_encode_props(quality: float) -> dict:
    """NSImageCompressionFactor живёт в AppKit, не в NSBitmapImageRep (PyObjC)."""
    from AppKit import NSImageCompressionFactor

    return {NSImageCompressionFactor: quality}


def optimize_screenshot_image(data: bytes, mime: str) -> tuple[bytes, str]:
    """
    Уменьшить скриншот для vision API (быстрее upload, та же модель).
    Только macOS / AppKit.
    """
    if not screenshot_optimize_enabled() or not data:
        return data, mime

    max_edge = screenshot_max_edge_px()
    if max_edge <= 0:
        return data, mime

    try:
        from AppKit import NSBitmapImageRep, NSImage, NSJPEGFileType, NSPNGFileType
    except ImportError:
        return data, mime

    img = NSImage.alloc().initWithData_(data)
    if img is None:
        return data, mime

    w = float(img.size().width)
    h = float(img.size().height)
    if w < 1 or h < 1:
        return data, mime

    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        resized = NSImage.alloc().initWithSize_((new_w, new_h))
        resized.lockFocus()
        img.drawInRect_fromRect_operation_fraction_(
            ((0, 0), (new_w, new_h)),
            ((0, 0), (w, h)),
            2,  # SourceOver
            1.0,
        )
        resized.unlockFocus()
        img = resized

    tiff = img.TIFFRepresentation()
    if tiff is None:
        return data, mime
    rep = NSBitmapImageRep.imageRepWithData_(tiff)
    if rep is None:
        return data, mime

    quality = screenshot_jpeg_quality()
    jpeg = rep.representationUsingType_properties_(
        NSJPEGFileType, _jpeg_encode_props(quality)
    )
    if jpeg and len(jpeg) < len(data):
        log(
            f"[copilot] screenshot optimize: {len(data)} → {len(jpeg)} bytes "
            f"({max_edge}px max, jpeg q={quality})"
        )
        return bytes(jpeg), "image/jpeg"

    png = rep.representationUsingType_properties_(NSPNGFileType, None)
    if png and len(png) < len(data):
        log(f"[copilot] screenshot optimize: {len(data)} → {len(png)} bytes (png)")
        return bytes(png), "image/png"

    return data, mime
