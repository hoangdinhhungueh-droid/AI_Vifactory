#!/usr/bin/env python3
"""Cleanup old files from Cloudflare R2 bucket (H-04 maintenance).

Removes objects older than 7 days to stay under 10GB limit and avoid overage fees.
Can be run as a cron job (e.g., daily at 2am).
"""
import os
import sys
import time
import argparse
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_TTL_DAYS = 7


def cleanup_r2(ttl_days: int = DEFAULT_TTL_DAYS, dry_run: bool = False):
    """Remove R2 objects older than ttl_days. dry_run reports without deleting."""
    cutoff = time.time() - (ttl_days * 86400)
    mode = "DRY-RUN" if dry_run else "LIVE"
    import boto3
    from botocore.exceptions import ClientError

    endpoint = os.getenv("R2_ENDPOINT_URL")
    bucket = os.getenv("R2_BUCKET_NAME")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([endpoint, bucket, access_key, secret_key]):
        logger.error("Missing R2 env vars (R2_ENDPOINT_URL, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)")
        return False

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )

        # List all objects
        logger.info("[%s] Scanning R2 bucket '%s' for objects older than %d days...", mode, bucket, ttl_days)
        deleted_count = 0
        deleted_size = 0

        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            contents = page.get("Contents", [])
            for obj in contents:
                key = obj["Key"]
                last_modified = obj["LastModified"].timestamp()
                size = obj.get("Size", 0)

                if last_modified < cutoff:
                    age_days = (time.time() - last_modified) / 86400
                    if dry_run:
                        deleted_count += 1
                        deleted_size += size
                        logger.info(
                            "WOULD DELETE (age %.1f days, %d KB): %s",
                            age_days, size // 1024, key,
                        )
                        continue
                    try:
                        s3.delete_object(Bucket=bucket, Key=key)
                        deleted_count += 1
                        deleted_size += size
                        logger.info(
                            "Deleted (age %.1f days, %d KB): %s",
                            age_days, size // 1024, key,
                        )
                    except ClientError as e:
                        logger.error("Failed to delete %s: %s", key, e)

        logger.info(
            "[%s] Cleanup complete: %s %d objects (%.2f MB)",
            mode,
            "would delete" if dry_run else "deleted",
            deleted_count,
            deleted_size / (1024 * 1024),
        )
        return True
    except Exception as e:
        logger.error("R2 cleanup failed: %s", e)
        return False


def main():
    ap = argparse.ArgumentParser(description="Delete R2 objects past their TTL.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be deleted without deleting anything.")
    ap.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS,
                    help="Delete objects older than this many days (default %d)." % DEFAULT_TTL_DAYS)
    args = ap.parse_args()

    # Load env (same pattern as youtube_upload.py)
    p = "/root/secrets/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    logger.info("R2 Cleanup (TTL=%d days, dry_run=%s) started at %s",
                args.ttl_days, args.dry_run, datetime.now().isoformat())
    success = cleanup_r2(ttl_days=args.ttl_days, dry_run=args.dry_run)
    logger.info("R2 Cleanup finished: %s", "SUCCESS" if success else "FAILED")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
