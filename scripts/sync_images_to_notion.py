#!/usr/bin/env python3
"""
VPS Script: Sync received images to Notion Image Asset Library.
Called after Windows agent uploads images to /var/vf/episodes/{id}/assets/

Flow:
1. Detect new images in assets/ dir
2. Upload to R2 (Cloudflare CDN)
3. Create Notion DB rows with metadata
4. Optionally trigger B5 audit
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, '/root/video_factory')

from app.services.image_gen import _r2_upload
from scripts.ag_notion_bridge import create_page, resolve_episode_image_asset_db

EPISODES_DIR = Path("/var/vf/episodes")
IMAGE_ASSET_DB_ID = "f9101989-2400-830c-ab89-01700bb07933"

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def build_notion_properties(reuse_key: str, episode_id: str, layer_type: str,
                           prompt_text: str, r2_url: str, audit_data: Dict) -> Dict:
    """Build Notion properties dict with audit fields matching actual schema."""
    # Map verdict to Status (status type uses different structure)
    verdict = audit_data.get("verdict", "Approved")
    if verdict not in ["Approved", "Reviewed", "New", "Pulled by VPS", "Archived"]:
        verdict = "Approved"
    status_value = {"status": {"name": verdict}}

    properties = {
        "Name": {"title": [{"text": {"content": reuse_key}}]},
        "Episode ID": {"rich_text": [{"text": {"content": episode_id}}]},
        "Layer Type": {"select": {"name": layer_type}},
        "Reuse Key": {"rich_text": [{"text": {"content": reuse_key}}]},
        "Prompt": {"rich_text": [{"text": {"content": prompt_text[:2000]}}]},
        "Status": status_value,
        "R2 Path": {"rich_text": [{"text": {"content": r2_url}}]}
    }

    # Add audit fields if present (use correct property names)
    if audit_data:
        if "final_score" in audit_data:
            properties["Audit Final Score"] = {"number": audit_data["final_score"]}
        if "d1_score" in audit_data:
            properties["Audit D1 Score"] = {"number": audit_data["d1_score"]}
        if "d2_score" in audit_data:
            properties["Audit D2 Score"] = {"number": audit_data["d2_score"]}
        if "d3_score" in audit_data:
            properties["Audit D3 Score"] = {"number": audit_data["d3_score"]}
        if "confidence" in audit_data:
            properties["Audit Confidence"] = {"number": audit_data["confidence"]}
        if "issues" in audit_data:
            # Prompt Issues is multi_select, not rich_text
            issues_list = audit_data["issues"] if isinstance(audit_data["issues"], list) else [audit_data["issues"]] if audit_data["issues"] else []
            if issues_list:
                properties["Prompt Issues"] = {"multi_select": [{"name": issue[:100]} for issue in issues_list[:5]]}
        if "notes" in audit_data:
            properties["AI Review Notes"] = {"rich_text": [{"text": {"content": audit_data["notes"][:2000]}}]}
        if "verdict" in audit_data:
            properties["AI Verdict"] = {"select": {"name": audit_data["verdict"]}}

    return properties


def load_audit_data(audits_dir: Path, reuse_key: str) -> Dict:
    """Load audit JSON for a reuse key, return empty dict if not found."""
    audit_file = audits_dir / f"{reuse_key}_audit.json"
    if audit_file.exists():
        try:
            with open(audit_file, 'r', encoding='utf-8') as af:
                return json.load(af)
        except Exception as e:
            logger.warning(f"Failed to load audit for {reuse_key}: {e}")
    return {}


def sync_images_to_notion(episode_id: str, force: bool = False) -> Dict:
    """
    Sync images from assets/ to Notion Image Asset Library.

    Args:
        episode_id: Episode identifier
        force: Re-sync already synced images

    Returns:
        Dict with sync results
    """
    episode_dir = EPISODES_DIR / episode_id
    assets_dir = episode_dir / "assets"
    prompts_file = episode_dir / "prompts_forge.json"
    audits_dir = episode_dir / "audits"

    if not assets_dir.exists():
        return {"error": "Assets directory not found", "synced": 0}

    if not prompts_file.exists():
        return {"error": "prompts_forge.json not found", "synced": 0}

    # Resolve per-episode child database
    db_result = resolve_episode_image_asset_db(episode_id, create_if_missing=True)
    if db_result.get("error"):
        return {"error": f"Failed to resolve episode DB: {db_result.get('message')}", "synced": 0}

    episode_db_id = db_result["db_id"]
    print(f"[Notion] Using episode DB: {episode_db_id} (created: {db_result.get('created', False)})")

    # Load prompts to get metadata
    with open(prompts_file, 'r', encoding='utf-8') as f:
        prompts_data = json.load(f)

    backgrounds = prompts_data.get("backgrounds", {})
    foregrounds = prompts_data.get("foregrounds", {})

    synced_count = 0
    errors = []

    # Process background images
    for reuse_key, prompt_data in backgrounds.items():
        image_file = assets_dir / f"{reuse_key}.png"
        if not image_file.exists():
            continue

        try:
            # Upload to R2
            r2_key = f"episodes/{episode_id}/assets/{image_file.name}"
            r2_url = _r2_upload(str(image_file), r2_key)

            if not r2_url:
                errors.append(f"R2 upload failed: {reuse_key}")
                continue

            # Load prompt and audit data
            prompt_text = prompt_data if isinstance(prompt_data, str) else prompt_data.get("prompt", "")
            audit_data = load_audit_data(audits_dir, reuse_key)

            # Build properties and create page
            notion_properties = build_notion_properties(
                reuse_key, episode_id, "Background", prompt_text, r2_url, audit_data
            )

            result = create_page(episode_db_id, notion_properties)

            if result.get("error"):
                errors.append(f"{reuse_key}: {result.get('message', 'Unknown error')}")
            else:
                logger.info(f"✅ Created background row: {reuse_key} → {result.get('url', result.get('id'))}")
                synced_count += 1

        except Exception as e:
            errors.append(f"{reuse_key}: {str(e)}")

    # Process foreground images
    for reuse_key, prompt_data in foregrounds.items():
        # Look for _transparent.png first (chroma-keyed version)
        transparent_file = assets_dir / f"{reuse_key}_transparent.png"
        image_file = transparent_file if transparent_file.exists() else assets_dir / f"{reuse_key}.png"

        if not image_file.exists():
            continue

        try:
            r2_key = f"episodes/{episode_id}/assets/{image_file.name}"
            r2_url = _r2_upload(str(image_file), r2_key)

            if not r2_url:
                errors.append(f"R2 upload failed: {reuse_key}")
                continue

            prompt_text = prompt_data if isinstance(prompt_data, str) else prompt_data.get("prompt", "")
            audit_data = load_audit_data(audits_dir, reuse_key)

            notion_properties = build_notion_properties(
                reuse_key, episode_id, "Foreground", prompt_text, r2_url, audit_data
            )

            result = create_page(episode_db_id, notion_properties)

            if result.get("error"):
                errors.append(f"{reuse_key}: {result.get('message', 'Unknown error')}")
            else:
                logger.info(f"✅ Created foreground row: {reuse_key} → {result.get('url', result.get('id'))}")
                synced_count += 1

        except Exception as e:
            errors.append(f"{reuse_key}: {str(e)}")

    return {
        "episode_id": episode_id,
        "synced": synced_count,
        "errors": errors
    }

def main():
    """Entry point - called manually or via cron."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync images to Notion")
    parser.add_argument("episode_id", help="Episode ID to sync")
    parser.add_argument("--force", action="store_true", help="Re-sync all images")

    args = parser.parse_args()

    result = sync_images_to_notion(args.episode_id, args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if result.get("synced", 0) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
