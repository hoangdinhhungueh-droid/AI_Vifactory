"""VF Visual Engine - R2 Upload & Cleanup (H-04 Restoration).

B4 visuals (Layer 1 Background 16:9 & Layer 2 Foreground 1:1 Chroma-key)
are 100% generated via Google Image Native Forge in Antigravity UI,
then synced to R2 (Cloudflare), GG Drive per market, and Notion Image Library.

This module provides the R2 upload layer only (no VPS image generation).
"""
import os, logging
from typing import Optional

logger = logging.getLogger(__name__)


def _r2_upload(local_path: str, r2_key: str) -> Optional[str]:
    """Upload a local file to Cloudflare R2.

    Args:
        local_path: local file path to upload
        r2_key: R2 object key (e.g. 'episodes/{ep_id}/assets/image.png')

    Returns:
        public R2 URL on success, None on failure
    """
    import boto3
    from botocore.exceptions import ClientError

    try:
        endpoint = os.getenv("R2_ENDPOINT_URL")
        bucket = os.getenv("R2_BUCKET_NAME")
        access_key = os.getenv("R2_ACCESS_KEY_ID")
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

        if not all([endpoint, bucket, access_key, secret_key]):
            logger.warning("[r2_upload] missing R2 env vars, skipping upload")
            return None

        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )

        if not os.path.exists(local_path):
            logger.error("[r2_upload] file not found: %s", local_path)
            return None

        with open(local_path, "rb") as f:
            s3.put_object(Bucket=bucket, Key=r2_key, Body=f)
        logger.info("[r2_upload] uploaded %s -> %s", local_path, r2_key)

        public_url = f"{endpoint}/{bucket}/{r2_key}"
        return public_url
    except ClientError as e:
        logger.error("[r2_upload] boto3 error: %s", e)
        return None
    except Exception as e:
        logger.error("[r2_upload] unexpected error: %s", e)
        return None


async def gen_reference_image(*args, **kwargs):
    """Placeholder: all images generated via Antigravity (B4)."""
    logger.info("[gen_reference_image] stub (images via Antigravity UI)")
    return None


async def gen_scene_image(*args, **kwargs):
    """Placeholder: all images generated via Antigravity (B4)."""
    logger.info("[gen_scene_image] stub (images via Antigravity UI)")
    return None
