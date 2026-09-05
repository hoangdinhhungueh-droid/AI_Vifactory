"""
MPT-G1-2 - Safe path enforcement. 5 zones.
"""
from pathlib import Path
BASE = Path("/root/video_factory")
SAFE_ZONES = {
    "storage": BASE / "assets",
    "models":  Path("/var/vf/models"),
    "tmp":     Path("/tmp/vf"),
    "bgm":     BASE / "assets" / "bgm",
    "fonts":   Path("/usr/share/fonts"),
}
FORBIDDEN = [".env", "secrets", ".."]

def safe_path(path, zone=None):
    resolved = Path(path).resolve()
    raw = str(resolved)
    for pat in FORBIDDEN:
        if pat in raw:
            raise ValueError(f"[safe_path] Forbidden pattern in path: {raw}")
    if zone:
        allowed = SAFE_ZONES.get(zone)
        if not allowed: raise ValueError(f"Unknown zone: {zone}")
        if not raw.startswith(str(allowed.resolve())):
            raise ValueError(f"{raw} outside zone {zone}")
        return resolved
    for _, base in SAFE_ZONES.items():
        if raw.startswith(str(base.resolve())):
            return resolved
    raise ValueError(f"{raw} outside all safe zones")
