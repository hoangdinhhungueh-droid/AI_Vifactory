"""Upload mode state (anonymous <-> public) for the Telegram toggle button.

FAIL-SAFE: any error falls back to the anonymous/default mode so we never
accidentally publish. Stores a single JSON file: {"mode": "anonymous"|"public"}.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_MODE_FILE = Path(os.getenv("UPLOAD_MODE_FILE", "/root/video_factory/db/upload_mode.json"))
_VALID = ("anonymous", "public")
_PRIVACY = {"anonymous": "unlisted", "public": "public"}
_DEFAULT = "anonymous"


def get_mode() -> str:
    """Current upload mode ('anonymous' default). FAIL-SAFE."""
    try:
        m = json.loads(_MODE_FILE.read_text()).get("mode", _DEFAULT)
    except Exception:  # noqa: BLE001
        m = _DEFAULT
    return m if m in _VALID else _DEFAULT


def set_mode(mode: str) -> str:
    """Persist `mode` (validated) and return the stored value. FAIL-SAFE."""
    m = mode if mode in _VALID else _DEFAULT
    try:
        _MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MODE_FILE.write_text(json.dumps({"mode": m}))
    except Exception:  # noqa: BLE001
        pass
    return m


def toggle_mode() -> str:
    """Flip anonymous <-> public and return the new mode."""
    return set_mode("public" if get_mode() == "anonymous" else "anonymous")


def privacy_status() -> str:
    """privacyStatus string to use at videos.insert for the current mode."""
    return _PRIVACY.get(get_mode(), "unlisted")


def label() -> str:
    """VN label for the Telegram toggle button reflecting the CURRENT mode."""
    if get_mode() == "public":
        return "🌐 Đang: PUBLIC → bấm để chuyển ẨN DANH"
    return "🕶️ Đang: ẨN DANH → bấm để chuyển PUBLIC"
