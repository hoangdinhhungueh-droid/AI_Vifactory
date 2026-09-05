#!/usr/bin/env python3
"""
Quota manager for Antigravity image generation.
Tracks 429 errors and retry windows.
"""
import json
import os
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

QUOTA_FILE = "/tmp/vf/antigravity_quota.json"

class QuotaState:
    def __init__(self, episode_id, target_count=30):
        self.episode_id = episode_id
        self.target_count = target_count
        self.status = "PENDING"
        self.images_generated = 0
        self.quota_exhausted_at = None
        self.quota_reset_at = None
        self.retry_count = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "episode_id": self.episode_id,
            "status": self.status,
            "images_generated": self.images_generated,
            "target_count": self.target_count,
            "quota_exhausted_at": self.quota_exhausted_at,
            "quota_reset_at": self.quota_reset_at,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def from_dict(cls, d):
        q = cls(d.get("episode_id", ""), d.get("target_count", 30))
        q.status = d.get("status", "PENDING")
        q.images_generated = d.get("images_generated", 0)
        q.quota_exhausted_at = d.get("quota_exhausted_at")
        q.quota_reset_at = d.get("quota_reset_at")
        q.retry_count = d.get("retry_count", 0)
        q.created_at = d.get("created_at", q.created_at)
        return q

def read_quota():
    """Read quota state from disk."""
    if not os.path.exists(QUOTA_FILE):
        return None
    try:
        with open(QUOTA_FILE) as f:
            return QuotaState.from_dict(json.load(f))
    except Exception as e:
        logger.warning(f"Failed to read quota state: {e}")
        return None

def write_quota(state):
    """Write quota state to disk."""
    try:
        os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
        with open(QUOTA_FILE, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to write quota state: {e}")
        return False

def record_exhaustion(episode_id, images_gen, target, reset_minutes=290):
    """Record quota exhaustion."""
    state = QuotaState(episode_id, target)
    state.status = "QUOTA_EXHAUSTED"
    state.images_generated = images_gen
    now = datetime.now(timezone.utc)
    state.quota_exhausted_at = now.isoformat()
    state.quota_reset_at = (now + timedelta(minutes=reset_minutes)).isoformat()
    write_quota(state)
    return state

def is_quota_available(state):
    """Check if quota has reset."""
    if not state or state.status != "QUOTA_EXHAUSTED":
        return True
    
    reset_at_str = state.quota_reset_at
    if not reset_at_str:
        return True
    
    try:
        reset_at = datetime.fromisoformat(reset_at_str.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= reset_at
    except:
        return True

def get_retry_wait_seconds(state):
    """Get seconds to wait before retry."""
    if not state or state.status != "QUOTA_EXHAUSTED":
        return 0
    
    reset_at_str = state.quota_reset_at
    if not reset_at_str:
        return 0
    
    try:
        reset_at = datetime.fromisoformat(reset_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if now >= reset_at:
            return 0
        return max(0, int((reset_at - now).total_seconds()))
    except:
        return 0

def mark_resumed(state):
    """Mark quota as resumed after reset."""
    state.status = "RESUMED"
    state.retry_count += 1
    write_quota(state)
    return state
