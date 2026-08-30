"""Pending-publish ledger for the Telegram "video chua public" notifier.

Tracks videos uploaded as private/unlisted so a single Telegram message can
list ALL pending videos at once (one Public button per video + one Public
ALL button), instead of only the single video handled by
scripts/send_publish_button.py.

FAIL-SAFE (mirrors upload_mode.py): any read/write error is swallowed and
returns an empty/no-op result -- a ledger bug must never break an upload or
block a Telegram publish action.

Stores JSON records:
  {"video_id": str, "title": str, "episode_dir": str,
   "uploaded_at": ISO str, "status": "private"|"public"|"unlisted",
   "published_at": ISO str | None}
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_LEDGER_FILE = Path(os.getenv("PUBLISH_LEDGER_FILE", "/root/video_factory/db/publish_ledger.json"))
_VAR_LEDGER_FILE = Path("/var/vf/data/publish_ledger.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_records(raw: Any) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("video_id"):
                records.append(item)
    elif isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict) and v.get("video_id"):
                records.append({
                    "video_id": v.get("video_id"),
                    "title": v.get("title", ""),
                    "episode_dir": v.get("episode_dir") or (f"/var/vf/episodes/{k}" if not k.startswith("http") else ""),
                    "uploaded_at": v.get("uploaded_at") or _now(),
                    "status": "public" if v.get("privacy_status") == "public" else "private",
                    "published_at": v.get("published_at"),
                })
    return records


def _load() -> List[Dict[str, Any]]:
    seen_vids = set()
    records: List[Dict[str, Any]] = []

    # 1. Primary DB file
    if _LEDGER_FILE.exists():
        try:
            raw = json.loads(_LEDGER_FILE.read_text(encoding="utf-8"))
            for r in _normalize_records(raw):
                vid = r.get("video_id")
                if vid and vid not in seen_vids:
                    seen_vids.add(vid)
                    records.append(r)
        except Exception:  # noqa: BLE001
            pass

    # 2. Secondary fallback /var/vf/data file if present
    if _VAR_LEDGER_FILE.exists() and _VAR_LEDGER_FILE != _LEDGER_FILE:
        try:
            raw = json.loads(_VAR_LEDGER_FILE.read_text(encoding="utf-8"))
            for r in _normalize_records(raw):
                vid = r.get("video_id")
                if vid and vid not in seen_vids:
                    seen_vids.add(vid)
                    records.append(r)
        except Exception:  # noqa: BLE001
            pass

    return records


def _save(records: List[Dict[str, Any]]) -> bool:
    try:
        _LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LEDGER_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        # Keep secondary path in sync if directory exists
        if _VAR_LEDGER_FILE.parent.exists():
            try:
                _VAR_LEDGER_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        return True
    except Exception:  # noqa: BLE001
        return False


def record_upload(video_id: str, title: str = "", episode_dir: str = "",
                   privacy_status: str = "private") -> bool:
    """Upsert a just-uploaded video into the ledger. FAIL-SAFE.
    
    Pre-check: if same episode_dir uploaded <5min ago, skip (dedup).
    """
    if not video_id:
        return False
    
    records = _load()
    
    # DEDUP: if episode_dir exists and was uploaded within last 5 min, skip
    if episode_dir:
        now_ts = datetime.now(timezone.utc).timestamp()
        for r in records:
            r_ep = r.get("episode_dir", "")
            if r_ep == episode_dir and r.get("status") in ("private", "unlisted"):
                try:
                    r_ts = datetime.fromisoformat(r.get("uploaded_at", "")).timestamp()
                    if now_ts - r_ts < 300:  # < 5 min
                        # Already uploaded recently, skip
                        return True  # FAIL-SAFE: pretend success
                except:
                    pass
    
    status = "public" if privacy_status == "public" else "private"
    for r in records:
        if r.get("video_id") == video_id:
            r["title"] = title or r.get("title", "")
            r["episode_dir"] = episode_dir or r.get("episode_dir", "")
            r["status"] = status
            if status == "public" and not r.get("published_at"):
                r["published_at"] = _now()
            return _save(records)
    records.append({
        "video_id": video_id,
        "title": title,
        "episode_dir": episode_dir,
        "uploaded_at": _now(),
        "status": status,
        "published_at": _now() if status == "public" else None,
    })
    return _save(records)


def mark_public(video_id: str) -> bool:
    """Mark a video as public (call after a successful videos.update). FAIL-SAFE."""
    if not video_id:
        return False
    records = _load()
    found = False
    for r in records:
        if r.get("video_id") == video_id:
            r["status"] = "public"
            r["published_at"] = _now()
            found = True
    if not found:
        records.append({
            "video_id": video_id, "title": "", "episode_dir": "",
            "uploaded_at": _now(), "status": "public", "published_at": _now(),
        })
    return _save(records)


def load_all() -> List[Dict[str, Any]]:
    return _load()


def list_recent(limit: int = 200) -> List[Dict[str, Any]]:
    all_rec = _load()
    return all_rec[-limit:] if limit > 0 else all_rec


def load_pending() -> List[Dict[str, Any]]:
    return [r for r in _load() if r.get("status") != "public"]

def check_already_uploaded(task_id: str) -> bool:
    """Check if task_id already has a recorded upload in ledger."""
    try:
        records = _load()
        for r in records:
            ep_dir = r.get("episode_dir", "")
            if task_id == os.path.basename(ep_dir).strip() or r.get("task_id") == task_id:
                return True
        return False
    except Exception:
        return False
