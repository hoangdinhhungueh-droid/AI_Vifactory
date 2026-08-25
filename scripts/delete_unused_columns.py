import os
import httpx
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = "/root/secrets/.env"
try:
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("NOTION_TOKEN="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["NOTION_TOKEN"] = val
except Exception as e:
    logger.warning("Could not load secrets env: %s", e)

token = os.getenv("NOTION_TOKEN")
if not token:
    logger.error("NO NOTION TOKEN")
    sys.exit(1)

DB_ID = os.getenv("TREND_BRAIN_DB_ID", "4c101989-2400-8334-8016-01d4f463b09f")

headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

payload = {
    "properties": {
        "Theme": None,
        "Entity Type": None,
        "Mapped Premise": None,
        "Series": None
    }
}

logger.info(f"Sending PATCH to DB {DB_ID} to delete properties...")
try:
    resp = httpx.patch(f"https://api.notion.com/v1/databases/{DB_ID}", headers=headers, json=payload, timeout=30.0)
    logger.info(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        logger.info("Successfully removed properties.")
    else:
        logger.error(f"Error: {resp.text}")
except Exception as e:
    logger.error(f"Exception: {e}")
