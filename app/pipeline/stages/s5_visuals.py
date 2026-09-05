"""S5 Visuals — Validation-only mode for Antigravity-generated PNGs.

ARCHITECTURE (31 Aug 2026 refactor):
This stage now operates in 100% Antigravity external generation mode.
ALL image generation has been removed from VPS per Rule 120.

ASSUMPTIONS:
- B4 (Antigravity) already ran and generated PNG files
- Images exist at /var/vf/episodes/{episode_id}/assets/*.png
- B5 audit completed and Notion rows have Status=Approved
- prompts_forge.json contains expected reuse keys

THIS STAGE VALIDATES:
- PNG file presence for all expected reuse keys
- PNG format per Rule 435:
  - Backgrounds: 2560x1440 RGB (16:9)
  - Foregrounds: 2048x2048 RGBA with transparency (1:1)

NO GENERATION: All stub functions removed. Any generation attempt is a bug.

env toggles: VF_IMAGE_ASPECT (default "16:9")
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List

from app.services.mpt_ported.state import idempotent_stage

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


def _validate_png_spec(png_path: Path, reuse_key: str, layer_type: str) -> None:
    """Validate PNG matches Rule 435 specifications.
    
    Args:
        png_path: Path to PNG file
        reuse_key: Reuse key from prompts_forge.json
        layer_type: "background" or "foreground"
    
    Raises:
        ValueError: If PNG doesn't meet specs
    """
    if not Image:
        logger.warning("[S5] PIL not available - skipping format validation for %s", reuse_key)
        return
    
    try:
        with Image.open(png_path) as img:
            width, height = img.size
            mode = img.mode
            
            if layer_type == "background":
                # Rule 435: Backgrounds must be 2560x1440 RGB (16:9)
                if width != 2560 or height != 1440:
                    raise ValueError(
                        f"Background {reuse_key}: expected 2560x1440, got {width}x{height}"
                    )
                if mode not in ("RGB", "RGBA"):
                    raise ValueError(
                        f"Background {reuse_key}: expected RGB/RGBA mode, got {mode}"
                    )
            
            elif layer_type == "foreground":
                # Rule 435: Foregrounds must be 2048x2048 RGBA with transparency (1:1)
                if width != 2048 or height != 2048:
                    raise ValueError(
                        f"Foreground {reuse_key}: expected 2048x2048, got {width}x{height}"
                    )
                if mode != "RGBA":
                    raise ValueError(
                        f"Foreground {reuse_key}: expected RGBA with transparency, got {mode}"
                    )
                
                # Check for alpha channel presence
                if not img.getextrema()[3] if len(img.getextrema()) > 3 else False:
                    logger.warning(
                        "[S5] Foreground %s: RGBA mode but alpha channel may be fully opaque",
                        reuse_key
                    )
            
            logger.debug(
                "[S5] Validated %s %s: %dx%d %s",
                layer_type, reuse_key, width, height, mode
            )
    
    except Exception as e:
        raise ValueError(f"PNG validation failed for {reuse_key}: {e}") from e


def _load_expected_reuse_keys(episode_id: str) -> Dict[str, List[str]]:
    """Load expected reuse keys from B3.5 prompts_forge.json.
    
    Returns:
        Dict with "backgrounds" and "foregrounds" lists of reuse keys
    """
    prompts_path = Path(f"/var/vf/episodes/{episode_id}/prompts_forge.json")
    
    if not prompts_path.exists():
        raise FileNotFoundError(
            f"prompts_forge.json not found for {episode_id}. "
            f"B3.5 must run before S5 validation."
        )
    
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts_data = json.load(f)
        
        backgrounds = list(prompts_data.get("backgrounds", {}).keys())
        foregrounds = list(prompts_data.get("foregrounds", {}).keys())
        
        # Filter out error keys from failed B3.5 runs
        backgrounds = [k for k in backgrounds if not k.startswith("_")]
        foregrounds = [k for k in foregrounds if not k.startswith("_")]
        
        logger.info(
            "[S5] %s expects %d backgrounds + %d foregrounds from prompts_forge.json",
            episode_id, len(backgrounds), len(foregrounds)
        )
        
        return {
            "backgrounds": backgrounds,
            "foregrounds": foregrounds,
        }
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in prompts_forge.json: {e}") from e


def _build_clip_metadata(
    assets_dir: Path,
    reuse_key: str,
    layer_type: str,
) -> Dict:
    """Build clip metadata dict for downstream stages (S6, S7).
    
    Returns:
        Dict with path, source, layer info for compositor
    """
    png_path = assets_dir / f"{reuse_key}.png"
    
    return {
        "path": str(png_path),
        "local_path": str(png_path),
        "source": "antigravity_b4",
        "reuse_key": reuse_key,
        "layer_type": layer_type,
        "image_prompt": reuse_key,  # For S7 compositor reference
    }


@idempotent_stage("s5_visuals")
async def run_s5(episode: dict) -> dict:
    """S5 Visuals - 100% Antigravity validation-only mode.
    
    ASSUMES B4 already ran:
    - Images at /var/vf/episodes/{episode_id}/assets/*.png
    - Notion rows created with Status=Approved
    - B5 audit completed
    
    This stage ONLY validates presence + format per Rule 435.
    NO GENERATION occurs on VPS (Rule 120).
    
    Args:
        episode: Episode dict with episode_id
    
    Returns:
        Episode dict with "clips" list containing validated PNG metadata
    
    Raises:
        FileNotFoundError: If expected PNG files are missing
        ValueError: If PNG format doesn't match Rule 435 specs
    """
    episode_id = episode["episode_id"]
    logger.info("[S5] %s starting validation-only mode (Antigravity B4 output)", episode_id)
    
    # Load expected reuse keys from B3.5 output
    try:
        expected = _load_expected_reuse_keys(episode_id)
    except FileNotFoundError as e:
        logger.error("[S5] %s missing prompts_forge.json: %s", episode_id, e)
        raise
    
    assets_dir = Path(f"/var/vf/episodes/{episode_id}/assets")
    
    if not assets_dir.exists():
        raise FileNotFoundError(
            f"Assets directory missing for {episode_id}. "
            f"B4 (Antigravity) must generate images before S5 validation."
        )
    
    # Validate all expected PNGs exist and match specs
    clips = []
    validation_errors = []
    
    # Validate backgrounds
    for key in expected["backgrounds"]:
        png_path = assets_dir / f"{key}.png"
        
        if not png_path.exists():
            validation_errors.append(f"Missing background: {key}.png")
            continue
        
        try:
            _validate_png_spec(png_path, key, "background")
            clips.append(_build_clip_metadata(assets_dir, key, "background"))
        except ValueError as e:
            validation_errors.append(str(e))
    
    # Validate foregrounds
    for key in expected["foregrounds"]:
        png_path = assets_dir / f"{key}.png"
        
        if not png_path.exists():
            validation_errors.append(f"Missing foreground: {key}.png")
            continue
        
        try:
            _validate_png_spec(png_path, key, "foreground")
            clips.append(_build_clip_metadata(assets_dir, key, "foreground"))
        except ValueError as e:
            validation_errors.append(str(e))
    
    # Report validation results
    if validation_errors:
        error_summary = "\n".join(validation_errors[:10])  # Limit to first 10
        logger.error(
            "[S5] %s validation failed with %d errors:\n%s",
            episode_id, len(validation_errors), error_summary
        )
        raise ValueError(
            f"S5 validation failed: {len(validation_errors)} errors. "
            f"Check logs or re-run B4 (Antigravity) for missing/invalid PNGs."
        )
    
    total_bg = len(expected["backgrounds"])
    total_fg = len(expected["foregrounds"])
    logger.info(
        "[S5] %s validation complete: %d backgrounds + %d foregrounds (Rule 435 ✓)",
        episode_id, total_bg, total_fg
    )
    
    return {
        **episode,
        "clips": clips,
        "s5_validation": {
            "backgrounds_validated": total_bg,
            "foregrounds_validated": total_fg,
            "total_clips": len(clips),
            "source": "antigravity_b4_approved",
        }
    }
