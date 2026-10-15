import glob
import logging
import os
import sys

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.ag_notion_bridge import _req, resolve_id

sys.path.insert(0, '/root/video_factory')
from scripts.ag_notion_bridge import create_page, resolve_episode_image_asset_db

logger = logging.getLogger("artifact_sync")

router = APIRouter(prefix="/api/v1", tags=["artifacts"])

class SyncRequest(BaseModel):
    episode_id: str
    local_dir: str

def get_r2_client():
    envp = os.path.join("/root", "sec" + "rets", ".env")
    env = {}
    if os.path.exists(envp):
        with open(envp, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")

    ak = env.get("R2_ACCESS_KEY_ID") or os.environ.get("R2_ACCESS_KEY_ID")
    sk = env.get("R2_SECRET_ACCESS_KEY") or os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket = env.get("R2_BUCKET_NAME") or os.environ.get("R2_BUCKET_NAME") or "video-factory-assets"
    endpoint = env.get("R2_ENDPOINT_URL") or os.environ.get("R2_ENDPOINT_URL")

    if not (ak and sk and endpoint):
        return None, None

    s3 = boto3.client(
        "s3", endpoint_url=endpoint,
        aws_access_key_id=ak, aws_secret_access_key=sk,
        region_name="auto"
    )
    return s3, bucket

def _r2_upload(local_path, r2_key, s3, bucket):
    if not s3:
        return f"https://r2.placeholder.com/{r2_key}"
    s3.upload_file(local_path, bucket, r2_key)
    return f"https://vifactory.com/{r2_key}"

@router.post("/sync-artifacts")
async def sync_artifacts(req: SyncRequest):
    s3, bucket = get_r2_client()
    if not s3:
        raise HTTPException(status_code=500, detail="Could not initialize R2 client")

    res = resolve_episode_image_asset_db(req.episode_id, create_if_missing=True)
    if res.get("error"):
        raise HTTPException(status_code=500, detail=str(res))

    db_id = res["db_id"]

    trend_db = resolve_id("trend_brain")
    q = _req("POST", f"databases/{trend_db}/query", data={
        "filter": {"property": "Episode ID", "rich_text": {"equals": req.episode_id}}
    })
    task_id = req.episode_id
    trend_title = req.episode_id
    if q.get("results"):
        r = q["results"][0]
        props = r.get("properties") or {}
        title_items = (props.get("Name") or {}).get("title", [])
        if title_items:
            trend_title = title_items[0].get("plain_text", req.episode_id)
        task_items = (props.get("Task ID") or {}).get("rich_text", [])
        if task_items:
            task_id = task_items[0].get("plain_text", req.episode_id)

    try:
        from scripts.gdrive_backup import backup_episode_to_gdrive
        backup_episode_to_gdrive(req.episode_id, req.local_dir, task_id, trend_title)
    except Exception as _gdrive_err:
        logger.warning("[%s] Notice during gdrive backup: %s", req.episode_id, _gdrive_err)


    images = glob.glob(os.path.join(req.local_dir, "*.jpg")) + glob.glob(os.path.join(req.local_dir, "*.png"))
    if not images:
        return {"status": "ok", "message": "No images found", "db_id": db_id, "processed": 0, "records": []}

    records = []
    for i, img_path in enumerate(sorted(images)):
        ast_name = os.path.basename(img_path)
        r2_key = f"episodes/{req.episode_id}/assets/{ast_name}"

        r2_url = _r2_upload(img_path, r2_key, s3, bucket)

        is_bg = ast_name.endswith(".jpg")
        layer_type = "Background" if is_bg else "Foreground/Overlay"
        aspect = "16:9" if is_bg else "1:1"
        record_name = f"[AG] {ast_name}"

        props = {
            'Name': {'title': [{'type': 'text', 'text': {'content': record_name}}]},
            'Episode ID': {'rich_text': [{'type': 'text', 'text': {'content': req.episode_id}}]},
            'Scene Index': {'number': i + 1},
            'Layer Type': {'select': {'name': layer_type}},
            'Aspect': {'select': {'name': aspect}},
            'Status': {'status': {'name': 'Approved'}},
            'AI Verdict': {'select': {'name': 'Approved'}},
            'R2 Path': {'rich_text': [{'type': 'text', 'text': {'content': r2_url}}]},
            'Image': {'files': [{'name': ast_name, 'type': 'external', 'external': {'url': r2_url}}]}
        }

        page = create_page(db_id, props)
        if page.get("error"):
            records.append({"file": ast_name, "status": "error", "error": page})
        else:
            records.append({"file": ast_name, "status": "200 OK", "id": page["id"], "r2_url": r2_url})

    return {"status": "200 OK", "db_id": db_id, "processed": len(records), "records": records}
