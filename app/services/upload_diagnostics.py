""""upload_diagnostics.py — Failure diagnosis module for upload errors (Phase 4.2).

Maps YouTube Data API v3 error responses to human-readable diagnoses with
actionable fix suggestions. Logs every failure to a JSON log for pattern
tracking over time. Never raises — always returns a Diagnosis dict.

Public API:
    diagnose_error(platform, error, context=None, notify=None) -> Diagnosis
    get_failure_history(limit=50) -> list[dict]
    get_error_patterns() -> dict[str, int]
    Diagnosis: {platform, error_code, error_type, diagnosis, fix_suggestion, logged: bool}

Env:
    VF_UPLOAD_DIAGNOSTICS=1  (default on)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vf.upload_diagnostics")

_LOG_FILE = Path(os.getenv(
    "UPLOAD_DIAGNOSTICS_LOG",
    "/root/video_factory/db/upload_diagnostics.json",
))


def _enabled() -> bool:
    return os.getenv("VF_UPLOAD_DIAGNOSTICS", "1") == "1"


# ---- YouTube API error mapping (Data API v3 docs + real-world) ----

YOUTUBE_ERROR_MAP: Dict[str, Dict[str, str]] = {
    "quotaExceeded": {
        "error_type": "quota",
        "diagnosis": "YouTube API daily upload quota exhausted (default 6 uploads/day).",
        "fix_suggestion": "Wait until 1:30 AM PT (quota resets at midnight PT) or request quota extension via YouTube Studio. Reduce upload frequency.",
    },
    "invalidCredentials": {
        "error_type": "auth",
        "diagnosis": "OAuth refresh token expired or revoked.",
        "fix_suggestion": "Re-consent OAuth at yt_oauth_setup.py with scope youtube.upload + youtube.force-ssl. Update YT_OAUTH_REFRESH_TOKEN in /root/secrets/.env then pm2 restart vf-api.",
    },
    "invalid_grant": {
        "error_type": "auth",
        "diagnosis": "OAuth refresh token invalid (expired 7-day test app or revoked by user).",
        "fix_suggestion": "Publish OAuth app to In production in Google Cloud Console to prevent 7-day token expiry. Re-consent and update refresh token.",
    },
    "forbidden": {
        "error_type": "permission",
        "diagnosis": "YouTube API returned 403 Forbidden — channel may have upload restrictions or API not enabled.",
        "fix_suggestion": "Check Google Cloud Console: YouTube Data API v3 enabled for project vf-youtube-en. Verify channel has no upload restrictions in YouTube Studio.",
    },
    "videoNotFound": {
        "error_type": "resource",
        "diagnosis": "Video ID not found — may have been deleted or is private from another channel.",
        "fix_suggestion": "Verify video ID belongs to the current channel. Use channel.list to confirm ownership.",
    },
    "invalidParameters": {
        "error_type": "validation",
        "diagnosis": "One or more request parameters are invalid (title, description, tags, category).",
        "fix_suggestion": "Run platform_validator.validate_upload() to check all constraints. Check title length (100 max), tags count (7 max), description length (5000 max).",
    },
    "badRequest": {
        "error_type": "validation",
        "diagnosis": "YouTube API rejected the request — malformed body or unsupported video format.",
        "fix_suggestion": "Verify video file is valid MP4 (ffprobe). Check payload JSON structure matches videos.insert schema. Run platform_validator first.",
    },
    "uploadAborted": {
        "error_type": "network",
        "diagnosis": "Resumable upload was aborted — network timeout or server-side interruption.",
        "fix_suggestion": "Retry upload (youtube_upload.py has built-in 5xx retry with exponential backoff). Check VPS network stability. If persistent, reduce chunksize.",
    },
    "rateLimitExceeded": {
        "error_type": "rate",
        "diagnosis": "API rate limit hit — too many requests in short window.",
        "fix_suggestion": "Increase delay between uploads (rate_risk_controller enforces min 10 min gap). Check if other processes are also calling YouTube API.",
    },
    "insufficientPermissions": {
        "error_type": "permission",
        "diagnosis": "OAuth token lacks required scope for this operation.",
        "fix_suggestion": "Re-consent with youtube.force-ssl scope (needed for videos.update + captions.insert). Current SCOPES in youtube_upload.py already include both.",
    },
}

# ---- Dailymotion error mapping (simplified) ----

DAILYMOTION_ERROR_MAP: Dict[str, Dict[str, str]] = {
    "401": {
        "error_type": "auth",
        "diagnosis": "Dailymotion API key invalid or expired.",
        "fix_suggestion": "Regenerate API key in Dailymotion Partner HQ. Update DAILYMOTION_API_KEY in /root/secrets/.env.",
    },
    "403": {
        "error_type": "permission",
        "diagnosis": "Dailymotion account not verified or upload restricted.",
        "fix_suggestion": "Complete account verification in Dailymotion Partner HQ. Check if 1,000 view threshold has been met.",
    },
    "429": {
        "error_type": "rate",
        "diagnosis": "Dailymotion rate limit exceeded.",
        "fix_suggestion": "Wait 15 min and retry. Reduce concurrent upload count.",
    },
}


def _extract_error_reason(error: Any) -> str:
    """Extract a machine-readable error reason from various error shapes."""
    if isinstance(error, dict):
        errors = error.get("error", {}).get("errors", [])
        if errors:
            return errors[0].get("reason", "unknown")
        return str(error.get("error", {}).get("code", "unknown"))
    content = getattr(error, "content", None)
    if content:
        try:
            if isinstance(content, bytes):
                content = content.decode()
            data = json.loads(content)
            errors = data.get("error", {}).get("errors", [])
            if errors:
                return errors[0].get("reason", "unknown")
            return str(data.get("error", {}).get("code", "unknown"))
        except Exception:
            pass
    reason = getattr(error, "reason", None)
    if reason:
        return str(reason)
    status = getattr(getattr(error, "resp", None), "status", None)
    if status:
        return str(status)
    return "unknown"


def _get_error_status(error: Any) -> Optional[int]:
    """Extract HTTP status code if available."""
    status = getattr(getattr(error, "resp", None), "status", None)
    if status:
        try:
            return int(status)
        except (ValueError, TypeError):
            pass
    if isinstance(error, dict):
        code = error.get("error", {}).get("code")
        if code:
            try:
                return int(code)
            except (ValueError, TypeError):
                pass
    return None


def diagnose_error(
    platform: str,
    error: Any,
    context: Optional[Dict[str, Any]] = None,
    notify=None,
) -> Dict[str, Any]:
    """Diagnose an upload error and return a structured diagnosis.

    Args:
        platform: youtube, youtube_shorts, dailymotion, etc.
        error: the exception object, HttpError, or parsed error dict.
        context: optional dict with episode_id, video_path, etc.
        notify: optional callable(str) for Telegram alert.

    Returns:
        Diagnosis dict with keys: platform, error_code, error_type,
        diagnosis, fix_suggestion, http_status, context, timestamp, logged.
    """
    reason = _extract_error_reason(error)
    status = _get_error_status(error)

    if platform in ("youtube", "youtube_shorts"):
        error_map = YOUTUBE_ERROR_MAP
    elif platform == "dailymotion":
        error_map = DAILYMOTION_ERROR_MAP
        reason = str(status) if status else reason
    else:
        error_map = {}

    info = error_map.get(reason, {})
    if not info:
        info = {
            "error_type": "unknown",
            "diagnosis": f"Unknown {platform} error: {reason} (HTTP {status or 'N/A'})",
            "fix_suggestion": "Check platform API docs for this error code. Run platform_validator.validate_upload() to rule out constraint violations.",
        }

    diagnosis = {
        "platform": platform,
        "error_code": reason,
        "error_type": info["error_type"],
        "diagnosis": info["diagnosis"],
        "fix_suggestion": info["fix_suggestion"],
        "http_status": status,
        "context": context or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "logged": False,
    }

    if _enabled():
        diagnosis["logged"] = _log_failure(diagnosis)

    if notify:
        try:
            msg = (
                f"UPLOAD FAIL [{platform}] {info['error_type']}: "
                f"{info['diagnosis']}\n"
                f"Fix: {info['fix_suggestion']}"
            )
            notify(msg)
        except Exception:
            pass

    logger.warning(
        "[diagnostics] %s error: %s -> %s",
        platform, reason, info["diagnosis"],
    )
    return diagnosis


def _log_failure(diagnosis: Dict[str, Any]) -> bool:
    """Append diagnosis to JSON log. FAIL-SAFE."""
    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if _LOG_FILE.exists():
            history = json.loads(_LOG_FILE.read_text())
            if not isinstance(history, list):
                history = []
        history.append(diagnosis)
        if len(history) > 200:
            history = history[-200:]
        _LOG_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2))
        return True
    except Exception as e:
        logger.warning("[diagnostics] log write failed: %s", e)
        return False


def get_failure_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent failure entries (most recent first)."""
    try:
        if not _LOG_FILE.exists():
            return []
        history = json.loads(_LOG_FILE.read_text())
        if not isinstance(history, list):
            return []
        return list(reversed(history[-limit:]))
    except Exception:
        return []


def get_error_patterns() -> Dict[str, int]:
    """Aggregate error_code counts for pattern analysis."""
    history = get_failure_history(limit=200)
    counts: Dict[str, int] = {}
    for h in history:
        code = h.get("error_code", "unknown")
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
