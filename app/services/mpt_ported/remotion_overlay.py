"""Remotion stat-card renderer (Moc 2, item 2.6c).

Renders a scene clip = still image + animated stat card, driven ONLY by the
`scene.remotion` block that S2/Notion authored in brain_input.json. The VPS
never invents remotion values: if the block is missing or invalid, this module
returns None and S5 falls back to plain Ken Burns (render unchanged).
"""
import asyncio
import hashlib
import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)

PROJ_DIR = os.getenv("VF_REMOTION_DIR", "/root/video_factory/remotion")
ENTRY = "src/index.tsx"
COMP_ID = "SceneCard"
FPS = int(os.getenv("VF_REMOTION_FPS", "30"))

_SIZES = {"16:9": (1536, 864), "9:16": (864, 1536), "1:1": (1080, 1080)}
_BEATS = ("rise", "peak", "collapse", "aftermath")
_ZONES = ("top_left", "top_right", "bottom_left", "bottom_right")


def remotion_enabled() -> bool:
    return os.getenv("VF_REMOTION_CARDS", "1") not in ("0", "false", "False", "")


def scene_card_props(scene) -> dict | None:
    """Map scene.remotion -> Remotion props, or None when not applicable."""
    if not isinstance(scene, dict):
        return None
    r = scene.get("remotion")
    if not isinstance(r, dict):
        return None
    if not r.get("enabled", True):
        return None
    stat_value = str(r.get("stat_value") or "").strip()
    beat = str(r.get("story_beat") or "").strip()
    zone = str(r.get("safe_zone") or "").strip()
    if not stat_value or beat not in _BEATS or zone not in _ZONES:
        logger.warning("[remotion] bo qua block khong hop le: stat=%r beat=%r zone=%r",
                       stat_value[:24], beat, zone)
        return None
    accent = r.get("accent_override")
    if not (isinstance(accent, str) and len(accent) == 7 and accent.startswith("#")):
        accent = None
    return {
        "statValue": stat_value,
        "statLabel": str(r.get("stat_label") or "").strip(),
        "storyBeat": beat,
        "hasChartInBg": bool(r.get("has_chart_in_bg", False)),
        "safeZone": zone,
        "accentOverride": accent,
    }


async def render_scene_card(*, image_path: str, props: dict, out_path: str,
                            dur_sec: float = 5.0, aspect: str = "16:9",
                            timeout: float | None = None) -> str | None:
    """Render one scene clip with Remotion. Returns out_path or None on failure."""
    if not os.path.isdir(PROJ_DIR) or not os.path.exists(os.path.join(PROJ_DIR, ENTRY)):
        logger.warning("[remotion] project missing at %s", PROJ_DIR)
        return None
    if not image_path or not os.path.exists(image_path):
        logger.warning("[remotion] background image missing: %s", image_path)
        return None
    pub = os.path.join(PROJ_DIR, "public")
    os.makedirs(pub, exist_ok=True)
    ext = os.path.splitext(image_path)[1] or ".jpg"
    bg_file = "bg_" + hashlib.sha1(image_path.encode()).hexdigest()[:12] + ext
    try:
        shutil.copyfile(image_path, os.path.join(pub, bg_file))
    except Exception as e:
        logger.warning("[remotion] cannot stage background (%s): %s", image_path, e)
        return None
    w, h = _SIZES.get(aspect, _SIZES["16:9"])
    frames = max(15, int(round(float(dur_sec) * FPS)))
    full = dict(props)
    full.update({"bgFile": bg_file, "durationInFrames": frames,
                 "width": w, "height": h})
    props_path = out_path + ".props.json"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False)
    cmd = ["npx", "remotion", "render", ENTRY, COMP_ID, out_path,
           "--props=" + props_path, "--log=error",
           "--concurrency=" + os.getenv("VF_REMOTION_CONCURRENCY", "1")]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=PROJ_DIR,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except Exception as e:
        logger.warning("[remotion] cannot spawn npx: %s", e)
        return None
    limit = timeout or float(os.getenv("VF_REMOTION_TIMEOUT", "300"))
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=limit)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        logger.warning("[remotion] timeout %.0fs rendering %s", limit, out_path)
        return None
    if proc.returncode != 0 or not os.path.exists(out_path):
        logger.warning("[remotion] render rc=%s: %s", proc.returncode,
                       (err or b"").decode(errors="ignore")[-400:])
        return None
    return out_path
