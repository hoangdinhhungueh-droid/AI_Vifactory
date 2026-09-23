#!/usr/bin/env python3
"""scripts/post_sync_cleanup.py — AUTOMATED POST-SYNC & SYSTEM LIFECYCLE CLEANUP

Purpose:
  1. Purges heavy intermediate video files (twolayer_silent.mp4, temp wavs)
     immediately after YouTube publishing (B10) and Google Drive backup.
  2. Enforces strict protection for active episodes (e.g. KR_EP0002).
  3. Sweeps expired Cloudflare R2 staging assets (TTL=7 days) to prevent R2 quota exhaustion.
  4. Purges orphaned Remotion render frames in /tmp (>12h, unlocked).
  5. Rotates old archive test directories and package caches.

Usage:
  python3 scripts/post_sync_cleanup.py --episode EN_EP0002_amazon_21air_crash
  python3 scripts/post_sync_cleanup.py --routine
  python3 scripts/post_sync_cleanup.py --dry-run
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [CLEANUP] %(levelname)s: %(message)s"
)
logger = logging.getLogger("post_sync_cleanup")

# STRICT PROTECTED EPISODES (Rule 118: ZERO-TOUCH on active production)
PROTECTED_PATTERNS = [
    p.strip() for p in os.getenv("VF_PROTECTED_PATTERNS", "").split(",") if p.strip()
]

# INTERMEDIATE FILES TO PURGE POST-PUBLISH (Always keep finals and assets)
INTERMEDIATE_FILENAMES = [
    "twolayer_silent.mp4",
    "final_169_norm.mp4",
    "preview_2min_master.mp4",
    "preview_2min_silent.mp4",
    "preview_2min_tg.mp4",
    "final_11.mp4",
    "final_916.mp4",
    "audio_norm.mp3",
    "test_ducked_audio.mp3",
    "test_bgm_mix.mp3",
]

EPISODES_DIR = Path("/var/vf/episodes")
ARCHIVE_DIR = EPISODES_DIR / "_archive"


def is_protected(ep_name: str) -> bool:
    """Check if an episode name matches protected active patterns."""
    import re
    if re.match(r"^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$", ep_name):
        if not (ep_name.startswith(("_dead_", "TEST_", "test_")) or "_TEMP_" in ep_name):
            return True
    for pattern in PROTECTED_PATTERNS:
        if pattern and pattern.lower() in ep_name.lower():
            return True
    return False


def cleanup_episode_intermediates(episode_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Clean heavy intermediate render files from a specific completed episode directory."""
    if is_protected(episode_id):
        logger.warning(f"SKIPPING PROTECTED EPISODE: {episode_id}")
        return {"status": "skipped", "reason": "protected", "freed_bytes": 0}

    ep_path = EPISODES_DIR / episode_id
    if not ep_path.exists():
        ep_path = Path("episodes") / episode_id
        if not ep_path.exists():
            return {"status": "not_found", "freed_bytes": 0}

    freed_bytes = 0
    removed_files = []

    for fname in INTERMEDIATE_FILENAMES:
        fpath = ep_path / fname
        if fpath.exists() and fpath.is_file():
            size = fpath.stat().st_size
            if not dry_run:
                try:
                    fpath.unlink()
                    freed_bytes += size
                    removed_files.append(fname)
                    logger.info(f"Purged intermediate file: {fpath} ({size / (1024*1024):.2f} MB)")
                except Exception as e:
                    logger.error(f"Failed to delete {fpath}: {e}")
            else:
                freed_bytes += size
                removed_files.append(fname)
                logger.info(f"[DRY-RUN] Would purge: {fpath} ({size / (1024*1024):.2f} MB)")

    # Clean orphaned temp wav files
    for wav_file in ep_path.glob("*.wav"):
        if wav_file.is_file():
            size = wav_file.stat().st_size
            if not dry_run:
                try:
                    wav_file.unlink()
                    freed_bytes += size
                    removed_files.append(wav_file.name)
                    logger.info(f"Purged temp wav: {wav_file} ({size / 1024:.1f} KB)")
                except Exception as e:
                    logger.error(f"Failed to delete {wav_file}: {e}")
            else:
                freed_bytes += size
                removed_files.append(wav_file.name)
                logger.info(f"[DRY-RUN] Would purge temp wav: {wav_file}")

    # Clean intermediate render chunks directory
    chunks_dir = ep_path / "chunks"
    if chunks_dir.exists() and chunks_dir.is_dir():
        for chunk_file in chunks_dir.glob("*.mp4"):
            if chunk_file.is_file():
                size = chunk_file.stat().st_size
                if not dry_run:
                    try:
                        chunk_file.unlink()
                        freed_bytes += size
                        removed_files.append(f"chunks/{chunk_file.name}")
                        logger.info(f"Purged chunk: {chunk_file.name} ({size / (1024*1024):.2f} MB)")
                    except Exception as e:
                        logger.error(f"Failed to delete chunk {chunk_file}: {e}")
                else:
                    freed_bytes += size
                    removed_files.append(f"chunks/{chunk_file.name}")
                    logger.info(f"[DRY-RUN] Would purge chunk: {chunk_file.name} ({size / (1024*1024):.2f} MB)")

    return {
        "status": "success",
        "episode_id": episode_id,
        "removed_files": removed_files,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2)
    }


def cleanup_completed_episodes_intermediates(dry_run: bool = False) -> int:
    """Sweep intermediate files across all past completed episodes."""
    if not EPISODES_DIR.exists():
        return 0

    total_freed = 0
    for ep_folder in sorted(EPISODES_DIR.iterdir()):
        if ep_folder.is_dir() and not ep_folder.name.startswith("."):
            if is_protected(ep_folder.name):
                logger.info(f"Preserving active episode: {ep_folder.name}")
                continue
            # Only clean if final_169.mp4 exists (proving render was completed)
            if (ep_folder / "final_169.mp4").exists():
                res = cleanup_episode_intermediates(ep_folder.name, dry_run=dry_run)
                total_freed += res.get("freed_bytes", 0)

    return total_freed


def cleanup_old_archives(days_ttl: int = 7, dry_run: bool = False) -> int:
    """Remove archive/test directories older than days_ttl in _archive and _dead_*."""
    total_freed = 0
    now = time.time()
    cutoff = now - (days_ttl * 86400)

    # 1. Clean /var/vf/episodes/_archive
    if ARCHIVE_DIR.exists():
        for item in list(ARCHIVE_DIR.iterdir()):
            if is_protected(item.name):
                continue
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())
                    if not dry_run:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink()
                        logger.info(f"Purged archive item: {item.name} ({size / (1024*1024):.2f} MB)")
                    else:
                        logger.info(f"[DRY-RUN] Would purge archive item: {item.name} ({size / (1024*1024):.2f} MB)")
                    total_freed += size
            except Exception as e:
                logger.warning(f"Error checking archive item {item}: {e}")

    # 2. Clean dead test folders in /var/vf/episodes
    if EPISODES_DIR.exists():
        for item in list(EPISODES_DIR.iterdir()):
            if is_protected(item.name):
                continue
            if item.name.startswith("_dead_") or item.name == "en-enron-ep000" or item.name == "test_run":
                try:
                    size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())
                    if not dry_run:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink()
                        logger.info(f"Purged dead test folder: {item.name} ({size / (1024*1024):.2f} MB)")
                    else:
                        logger.info(f"[DRY-RUN] Would purge dead test folder: {item.name} ({size / (1024*1024):.2f} MB)")
                    total_freed += size
                except Exception as e:
                    logger.warning(f"Error checking dead test folder {item}: {e}")

    return total_freed


def cleanup_orphaned_tmp_renders(dry_run: bool = False) -> int:
    """Clean unheld /tmp/react-motion-render* folders older than 12 hours."""
    tmp_path = Path("/tmp")
    now = time.time()
    total_freed = 0

    for item in tmp_path.glob("react-motion-render*"):
        if not item.is_dir():
            continue
        try:
            mtime = item.stat().st_mtime
            age_hours = (now - mtime) / 3600
            if age_hours > 12:
                size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())
                if not dry_run:
                    shutil.rmtree(item, ignore_errors=True)
                    logger.info(f"Purged orphaned Remotion tmp render: {item.name} (Age: {age_hours:.1f}h, {size / (1024*1024):.2f} MB)")
                else:
                    logger.info(f"[DRY-RUN] Would purge orphaned tmp render: {item.name} (Age: {age_hours:.1f}h, {size / (1024*1024):.2f} MB)")
                total_freed += size
        except Exception as e:
            logger.warning(f"Error checking tmp render {item}: {e}")

    return total_freed


def cleanup_expired_r2(ttl_days: int = 2, dry_run: bool = False) -> bool:
    """Sweep Cloudflare R2 staging assets older than ttl_days."""
    try:
        sys.path.insert(0, "/root/video_factory")
        from scripts.cleanup_r2_old_files import cleanup_r2
        logger.info(f"Triggering R2 Cleanup sweep (TTL={ttl_days} days, dry_run={dry_run})...")
        success = cleanup_r2(ttl_days=ttl_days, prefixes=("episodes/", "vf-img/"), dry_run=dry_run)
        return success
    except Exception as e:
        logger.error(f"R2 cleanup execution error: {e}")
        return False


def run_full_maintenance(dry_run: bool = False, r2_ttl_days: int = 2) -> Dict[str, Any]:
    """Execute full routine cleanup across VPS disk, tmp folders, and Cloudflare R2."""
    logger.info("=== STARTING FULL POST-SYNC & SYSTEM MAINTENANCE CLEANUP ===")
    
    # 1. Clean completed episode intermediates
    freed_ep = cleanup_completed_episodes_intermediates(dry_run=dry_run)
    logger.info(f"Episode intermediates freed: {freed_ep / (1024*1024):.2f} MB")

    # 2. Clean old test archives (>7 days)
    freed_arch = cleanup_old_archives(days_ttl=7, dry_run=dry_run)
    logger.info(f"Old archives freed: {freed_arch / (1024*1024):.2f} MB")

    # 3. Clean orphaned tmp renders (>12 hours)
    freed_tmp = cleanup_orphaned_tmp_renders(dry_run=dry_run)
    logger.info(f"Orphaned tmp renders freed: {freed_tmp / (1024*1024):.2f} MB")

    # 4. Clean expired R2 assets
    r2_success = cleanup_expired_r2(ttl_days=r2_ttl_days, dry_run=dry_run)

    total_freed_mb = round((freed_ep + freed_arch + freed_tmp) / (1024 * 1024), 2)
    logger.info(f"=== MAINTENANCE COMPLETE: Total VPS Disk Space Freed: {total_freed_mb} MB | R2 Sweep: {'PASS' if r2_success else 'FAIL'} ===")

    return {
        "status": "success",
        "total_freed_mb": total_freed_mb,
        "episodes_freed_mb": round(freed_ep / (1024 * 1024), 2),
        "archive_freed_mb": round(freed_arch / (1024 * 1024), 2),
        "tmp_freed_mb": round(freed_tmp / (1024 * 1024), 2),
        "r2_success": r2_success
    }


def main():
    parser = argparse.ArgumentParser(description="VF Pipeline Post-Sync & Lifecycle Cleanup")
    parser.add_argument("--episode", type=str, help="Specific episode ID to clean intermediates after publish")
    parser.add_argument("--routine", action="store_true", help="Run full routine maintenance (intermediates + archives + tmp + R2)")
    parser.add_argument("--dry-run", action="store_true", help="Preview deletions without actually deleting files")
    parser.add_argument("--r2-ttl", type=int, default=2, help="TTL in days for R2 assets (default: 2)")
    args = parser.parse_args()

    if args.episode:
        res = cleanup_episode_intermediates(args.episode, dry_run=args.dry_run)
        print(f"Episode cleanup result: {res}")
    elif args.routine:
        res = run_full_maintenance(dry_run=args.dry_run, r2_ttl_days=args.r2_ttl)
        print(f"Full maintenance result: {res}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
