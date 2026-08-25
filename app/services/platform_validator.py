""""platform_validator.py — Pre-upload platform constraint validator (Phase 4.1).

Runs BEFORE any upload attempt. Validates that the video file, SEO payload,
and metadata meet each target platform's hard constraints. Returns a
structured PASS/FAIL result with a list of violations — never raises.

This is the executable gate codifying the platform rules already spec'd in
seo_metadata.py PLATFORM_SEO_RULES + YouTube API limits + Content Spec v1.1
(min 8 min for long-form mid-roll). It does NOT duplicate SEO generation —
it only VALIDATES the output of seo_metadata.write_seo_payloads().

Public API:
    validate_for_platform(platform, episode_dir, payload, notify=None) -> ValidationResult
    validate_upload(episode_dir, platform, notify=None) -> ValidationResult
    ValidationResult: {passed: bool, violations: list[Violation], warnings: list[str]}

Env:
    VF_PLATFORM_VALIDATOR=1  (default on; set 0 to disable)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vf.platform_validator")


def _env(n: str, d: str) -> str:
    v = os.getenv(n)
    return v if v is not None else d

def _enabled() -> bool:
    return _env("VF_PLATFORM_VALIDATOR", "1") == "1"


# ---- Platform constraint tables (Q2/2026, page 22 SoT + YouTube API docs) ----

PLATFORM_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "youtube": {
        "title_min": 1,
        "title_max": 100,
        "desc_max": 5000,
        "tags_max_count": 7,
        "tags_max_chars": 500,
        "hashtag_max": 5,
        "video_min_duration_s": 480,   # ≥8 min for mid-roll (Content Spec v1.1)
        "video_max_duration_s": 900,   # ≤15 min practical cap
        "category_id_required": True,
        "ai_disclosure_required": True,
        "srt_supported": True,
        "file_extensions": (".mp4",),
    },
    "youtube_shorts": {
        "title_min": 1,
        "title_max": 100,
        "desc_max": 5000,
        "tags_max_count": 7,
        "tags_max_chars": 500,
        "hashtag_max": 5,
        "video_min_duration_s": 15,
        "video_max_duration_s": 180,  # Shorts ≤3 min
        "category_id_required": True,
        "ai_disclosure_required": True,
        "srt_supported": True,
        "file_extensions": (".mp4",),
    },
    "dailymotion": {
        "title_min": 1,
        "title_max": 255,
        "desc_max": 3000,
        "tags_max_count": 10,
        "tags_max_chars": 1000,
        "hashtag_max": 10,
        "video_min_duration_s": 60,
        "video_max_duration_s": 1200,
        "category_id_required": False,
        "ai_disclosure_required": True,
        "srt_supported": False,
        "file_extensions": (".mp4",),
    },
    "facebook_reels": {
        "title_min": 1,
        "title_max": 125,
        "desc_max": 2200,
        "tags_max_count": 0,       # FB uses hashtags only
        "tags_max_chars": 0,
        "hashtag_max": 5,
        "video_min_duration_s": 3,
        "video_max_duration_s": 90,
        "category_id_required": False,
        "ai_disclosure_required": True,
        "srt_supported": False,
        "file_extensions": (".mp4",),
    },
    "instagram_reels": {
        "title_min": 1,
        "title_max": 150,
        "desc_max": 2200,
        "tags_max_count": 0,
        "tags_max_chars": 0,
        "hashtag_max": 15,
        "video_min_duration_s": 3,
        "video_max_duration_s": 90,
        "category_id_required": False,
        "ai_disclosure_required": True,
        "srt_supported": False,
        "file_extensions": (".mp4",),
    },
}


class Violation:
    """A single constraint violation."""
    def __init__(self, field: str, message: str, severity: str = "error"):
        self.field = field
        self.message = message
        self.severity = severity  # "error" = blocks upload, "warning" = allows but flags

    def to_dict(self) -> dict:
        return {"field": self.field, "message": self.message, "severity": self.severity}


class ValidationResult:
    """Structured validation outcome — never raises."""
    def __init__(self):
        self.violations: List[Violation] = []
        self.warnings: List[str] = []

    @property
    def passed(self) -> bool:
        return not any(v.severity == "error" for v in self.violations)

    def add_error(self, field: str, message: str):
        self.violations.append(Violation(field, message, "error"))

    def add_warning(self, field: str, message: str):
        self.warnings.append(f"[{field}] {message}")

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
        }


# ---- ffprobe duration check --------------------------------------------------

def _probe_duration(video_path: str) -> Optional[float]:
    """Return duration in seconds via ffprobe, or None on failure."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", video_path],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
        info = json.loads(r.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception as e:
        logger.warning("[validator] ffprobe failed for %s: %s", video_path, e)
        return None


# ---- Main validation ---------------------------------------------------------

def validate_for_platform(
    platform: str,
    episode_dir: str,
    payload: Dict[str, Any],
    notify=None,
) -> ValidationResult:
    """Validate a single platform's upload payload against its constraints.

    Args:
        platform: one of PLATFORM_CONSTRAINTS keys.
        episode_dir: absolute path to the episode output directory.
        payload: the per-platform payload dict (from seo_payloads.json or
                youtube_upload_payload.json).
        notify: optional callable(str) for Telegram alerts on violations.

    Returns:
        ValidationResult — .passed == True means upload may proceed.
    """
    result = ValidationResult()
    if not _enabled():
        logger.info("[validator] disabled via VF_PLATFORM_VALIDATOR=0")
        return result

    rules = PLATFORM_CONSTRAINTS.get(platform)
    if not rules:
        result.add_error("platform", f"Unknown platform: {platform}")
        return result

    # --- 1. Title ---
    title = payload.get("title", "")
    if len(title) < rules["title_min"]:
        result.add_error("title", f"Title too short: {len(title)} < {rules['title_min']}")
    if len(title) > rules["title_max"]:
        result.add_error("title", f"Title too long: {len(title)} > {rules['title_max']}")

    # --- 2. Description ---
    desc = payload.get("description", "")
    if len(desc) > rules["desc_max"]:
        result.add_error("description", f"Description too long: {len(desc)} > {rules['desc_max']}")

    # --- 3. Tags (hidden SEO tags, not hashtags) ---
    tags = payload.get("tags", [])
    if rules["tags_max_count"] > 0:
        if len(tags) > rules["tags_max_count"]:
            result.add_error("tags", f"Too many tags: {len(tags)} > {rules['tags_max_count']}")
        total_tag_chars = sum(len(t) for t in tags)
        if total_tag_chars > rules["tags_max_chars"]:
            result.add_error("tags", f"Tag chars exceed: {total_tag_chars} > {rules['tags_max_chars']}")

    # --- 4. Hashtags ---
    hashtags = payload.get("hashtags", [])
    if len(hashtags) > rules["hashtag_max"]:
        result.add_error("hashtags", f"Too many hashtags: {len(hashtags)} > {rules['hashtag_max']}")

    # --- 5. AI disclosure ---
    if rules.get("ai_disclosure_required"):
        if "altered" not in desc.lower() and "ai" not in desc.lower() and "disclosure" not in desc.lower():
            result.add_error("ai_disclosure", "AI disclosure not found in description")

    # --- 6. Category ID ---
    if rules.get("category_id_required"):
        cat = payload.get("category_id")
        if not cat:
            result.add_error("category_id", "category_id required but missing")

    # --- 7. Video file exists + duration ---
    export = payload.get("export", {})
    target_file = export.get("target_file", "final_169.mp4")
    video_path = os.path.join(episode_dir, target_file)
    if not os.path.exists(video_path):
        result.add_error("video_file", f"Video file not found: {video_path}")
    else:
        ext = os.path.splitext(video_path)[1].lower()
        if ext not in rules["file_extensions"]:
            result.add_error("video_file", f"Unsupported extension: {ext}")
        duration = _probe_duration(video_path)
        if duration is not None:
            if duration < rules["video_min_duration_s"]:
                result.add_error(
                    "duration",
                    f"Video too short: {duration:.0f}s < {rules['video_min_duration_s']}s "
                    f"(min {rules['video_min_duration_s'] // 60}min for {platform})",
                )
            if duration > rules["video_max_duration_s"]:
                result.add_warning(
                    "duration",
                    f"Video exceeds recommended max: {duration:.0f}s > {rules['video_max_duration_s']}s",
                )
        else:
            result.add_warning("duration", "Could not probe video duration (ffprobe failed)")

    # --- 8. SRT file (if applicable) ---
    if rules.get("srt_supported") and payload.get("srt_independent_upload"):
        srt_path = payload.get("srt_path")
        if srt_path and not os.path.exists(srt_path):
            result.add_warning("srt", f"SRT file not found: {srt_path} — caption upload will skip")

    # --- Notify on violations ---
    if not result.passed and notify:
        try:
            errs = "; ".join(v.message for v in result.violations if v.severity == "error")
            notify(f"PLATFORM VALIDATOR FAIL [{platform}]: {errs}")
        except Exception:
            pass

    logger.info(
        "[validator] %s -> %s (%d errors, %d warnings)",
        platform, "PASS" if result.passed else "FAIL",
        sum(1 for v in result.violations if v.severity == "error"),
        len(result.warnings),
    )
    return result


def validate_upload(
    episode_dir: str,
    platform: str = "youtube",
    notify=None,
) -> ValidationResult:
    """Convenience: load payload from episode_dir and validate.

    Looks for youtube_upload_payload.json (YouTube) or seo_payloads.json
    (multi-platform) in episode_dir.
    """
    # Try platform-specific payload first
    payload_file = os.path.join(episode_dir, "youtube_upload_payload.json")
    if os.path.exists(payload_file) and platform in ("youtube", "youtube_shorts"):
        with open(payload_file) as f:
            payload = json.load(f)
        return validate_for_platform(platform, episode_dir, payload, notify)

    # Fall back to seo_payloads.json (multi-platform)
    seo_file = os.path.join(episode_dir, "seo_payloads.json")
    if os.path.exists(seo_file):
        with open(seo_file) as f:
            all_payloads = json.load(f)
        payload = all_payloads.get(platform, {})
        if not payload:
            result = ValidationResult()
            result.add_error("payload", f"No payload for platform '{platform}' in seo_payloads.json")
            return result
        return validate_for_platform(platform, episode_dir, payload, notify)

    result = ValidationResult()
    result.add_error("payload", f"No upload payload found in {episode_dir}")
    return result
