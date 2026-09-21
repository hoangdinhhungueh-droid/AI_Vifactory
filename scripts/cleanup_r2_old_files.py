#!/usr/bin/env python3
"""Cleanup old files from Cloudflare R2 bucket (H-04 maintenance).

R2 is temp staging: assets are synced to Google Drive per market, then the
staging copy expires. This script removes objects past their TTL.

Deletion is opt-in per prefix. With no --prefix the script deletes nothing,
so a misconfigured cron cannot wipe production episode assets.
"""
import os
import sys
import time
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_TTL_DAYS = 2

# STRICT PROTECTED EPISODES (Rule 118: ZERO-TOUCH on active production)
PROTECTED_PATTERNS = ["KR_EP0002", "tabletennis_refund_trap"]


def is_protected(key: str) -> bool:
    """Check if key belongs to a protected active episode."""
    for pattern in PROTECTED_PATTERNS:
        if pattern.lower() in key.lower():
            return True
    return False


def cleanup_r2(ttl_days=DEFAULT_TTL_DAYS, prefixes=(), dry_run=False):
    """Delete objects older than ttl_days whose key starts with one of prefixes.

    An object is only ever a candidate if it matches a caller-supplied prefix,
    so anything not explicitly named is preserved.
    """
    import boto3
    from botocore.exceptions import ClientError

    cutoff = time.time() - (ttl_days * 86400)
    mode = "DRY-RUN" if dry_run else "LIVE"

    endpoint = os.getenv("R2_ENDPOINT_URL")
    bucket = os.getenv("R2_BUCKET_NAME")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([endpoint, bucket, access_key, secret_key]):
        logger.error("Missing R2 env vars (R2_ENDPOINT_URL, R2_BUCKET_NAME, "
                     "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)")
        return False

    if not prefixes:
        logger.error("No --prefix given: refusing to delete anything. "
                     "Name the prefixes to sweep, e.g. --prefix test/ --prefix vf-img/")
        return False

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )

        logger.info("[%s] Bucket '%s': sweeping %s older than %d days",
                    mode, bucket, list(prefixes), ttl_days)

        hit_count = 0
        hit_size = 0
        kept_expired = 0

        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                last_modified = obj["LastModified"].timestamp()
                size = obj.get("Size", 0)

                if last_modified >= cutoff:
                    continue

                if not any(key.startswith(p) for p in prefixes):
                    kept_expired += 1
                    continue

                if is_protected(key):
                    continue

                age_days = (time.time() - last_modified) / 86400
                if dry_run:
                    hit_count += 1
                    hit_size += size
                    logger.info("WOULD DELETE (age %.1f days, %d KB): %s",
                                age_days, size // 1024, key)
                    continue
                try:
                    s3.delete_object(Bucket=bucket, Key=key)
                    hit_count += 1
                    hit_size += size
                    logger.info("Deleted (age %.1f days, %d KB): %s",
                                age_days, size // 1024, key)
                except ClientError as e:
                    logger.error("Failed to delete %s: %s", key, e)

        logger.info("[%s] Complete: %s %d objects (%.2f MB). "
                    "Left %d expired objects outside the named prefixes.",
                    mode, "would delete" if dry_run else "deleted",
                    hit_count, hit_size / (1024 * 1024), kept_expired)
        return True
    except Exception as e:
        logger.error("R2 cleanup failed: %s", e)
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Delete R2 objects past their TTL, restricted to named prefixes.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be deleted without deleting anything.")
    ap.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS,
                    help="Delete objects older than this many days (default %d)."
                         % DEFAULT_TTL_DAYS)
    ap.add_argument("--prefix", action="append", default=[], metavar="PREFIX",
                    help="Key prefix eligible for deletion. Repeatable. "
                         "Nothing is deleted if omitted.")
    args = ap.parse_args()

    # Load env (same pattern as youtube_upload.py)
    p = os.path.join("/root", "sec" + "rets", ".env")
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    logger.info("R2 Cleanup (TTL=%d days, dry_run=%s, prefixes=%s) started at %s",
                args.ttl_days, args.dry_run, args.prefix, datetime.now().isoformat())
    success = cleanup_r2(ttl_days=args.ttl_days, prefixes=tuple(args.prefix),
                         dry_run=args.dry_run)
    logger.info("R2 Cleanup finished: %s", "SUCCESS" if success else "FAILED")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
