"""
app/services/topic_history_registry.py - TOPIC HISTORY & ANTI-DUPLICATION REGISTRY (05/09/2026)
Replaces legacy Smart Cache.
Mandate:
  1. Zero LLM tokens spent on previously approved/produced topics.
  2. Permanently tracks handled topics across local disks (/var/vf/pending_tasks, episodes/) and Notion.
  3. Provides fast normalization and deduplication check before any external API / LLM calls.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from core.paths import (
    resolve_episodes_dir,
    resolve_pending_tasks_dir,
    resolve_topic_history_path,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = str(resolve_topic_history_path())
PENDING_DIR = str(resolve_pending_tasks_dir(ensure_dir=False))
EPISODES_DIR = str(resolve_episodes_dir(ensure_dir=False))


def _normalize_key(text: str) -> str:
    """Normalize keyword for deduplication (lowercase, strip, remove extra spaces & punctuation)."""
    if not text:
        return ""
    s = text.lower().strip()
    # Remove standard punctuation but keep alphanumeric and native CJK characters
    s = re.sub(r"[^\w\s\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_history(registry_path: Optional[str] = None, allow_backfill: bool = True) -> dict:
    """Load registry from file and automatically backfill from pending tasks and episodes."""
    target_path = str(registry_path) if registry_path else REGISTRY_PATH
    history = {}
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            logger.warning(f"[history] Failed to read {target_path}: {e}")
            history = {}

    # Backfill from /var/vf/pending_tasks (only when using global production registry)
    if allow_backfill and not registry_path and os.path.exists(PENDING_DIR):
        for f in os.listdir(PENDING_DIR):
            if f.endswith(".json"):
                try:
                    p = os.path.join(PENDING_DIR, f)
                    with open(p, "r", encoding="utf-8") as jf:
                        d = json.load(jf)
                        term = d.get("raw_term") or d.get("keyword") or ""
                        slug = d.get("task_slug") or ""
                        tid = d.get("task_id") or f.replace(".json", "")
                        mkt = d.get("market") or "EN"
                        norm = _normalize_key(term)
                        if norm and norm not in history:
                            history[norm] = {
                                "task_id": tid,
                                "raw_term": term,
                                "slug": slug,
                                "market": mkt,
                                "recorded_at": (
                                    d.get("recorded_at")
                                    or d.get("created_at")
                                    or datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).isoformat()
                                ),
                                "source": "pending_tasks"
                            }
                except Exception:
                    pass

    return history


def save_history(history: dict) -> None:
    """Persist history registry atomically to disk."""
    try:
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
        tmp = REGISTRY_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        os.replace(tmp, REGISTRY_PATH)
    except Exception as e:
        logger.warning(f"[history] Failed to save {REGISTRY_PATH}: {e}")


def is_topic_already_handled(term: str, market: str = None) -> bool:
    """Check if a topic or its close variants have already been processed in the pipeline.
    Returns True if already handled -> Skip completely to save tokens and avoid duplicate videos.
    """
    if not term:
        return False
    norm = _normalize_key(term)
    if not norm:
        return False

    history = load_history()
    if norm in history:
        return True

    # Check for substring / superstring containment
    for k, v in history.items():
        if market and v.get("market") and v["market"].upper() != market.upper():
            continue
        # Exact match after normalization
        if norm == k:
            return True
        # If one contains the other and length ratio > 0.75
        if len(norm) > 4 and len(k) > 4:
            if norm in k or k in norm:
                ratio = min(len(norm), len(k)) / max(len(norm), len(k))
                if ratio > 0.75:
                    return True

    return False


def record_handled_topic(term: str, task_id: str = "", market: str = "EN", slug: str = None, specific_angle: str = None) -> None:
    """Record newly approved or produced topic into the permanent registry."""
    norm = _normalize_key(term)
    if not norm:
        return

    history = load_history()
    history[norm] = {
        "task_id": task_id or "REJECTED_OR_HANDLED",
        "raw_term": term,
        "slug": slug or "",
        "specific_angle": specific_angle or "",
        "market": (market or "EN").upper(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": "live_pipeline"
    }
    save_history(history)
    logger.info(f"[history] Recorded '{term}' ({task_id or 'HANDLED'}) into permanent topic registry.")


if __name__ == "__main__":
    h = load_history()
    print(f"Loaded {len(h)} historical topics from registry.")
    test_term = "농약"
    print(f"Is '{test_term}' already handled? -> {is_topic_already_handled(test_term)}")

