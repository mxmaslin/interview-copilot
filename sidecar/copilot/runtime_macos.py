from __future__ import annotations

import plistlib
import sys
from pathlib import Path


def _info_plist_paths() -> list[Path]:
    """Paths rumps may use (dirname(sys.executable), without resolving symlinks)."""
    paths: list[Path] = []
    if sys.executable:
        paths.append(Path(sys.executable).parent / "Info.plist")
    if sys.argv and sys.argv[0]:
        paths.append(Path(sys.argv[0]).parent / "Info.plist")
    return paths


def ensure_info_plist(bundle_id: str = "com.copilot.sidecar") -> None:
    """rumps needs CFBundleIdentifier in Info.plist next to sys.executable."""
    if sys.platform != "darwin":
        return
    payload = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleName": "Copilot",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0",
    }
    for plist_path in _info_plist_paths():
        if plist_path.exists():
            try:
                with plist_path.open("rb") as f:
                    data = plistlib.load(f)
                if data.get("CFBundleIdentifier"):
                    continue
            except Exception:
                pass
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        with plist_path.open("wb") as f:
            plistlib.dump(payload, f)
