#!/usr/bin/env python3
"""Push locally-cached generated images into the Notion "Image Asset
Library" file property (Image), for rows belonging to a given episode that
are Status=Approved but don't have the Image file attached yet.

This makes the image persist as a real Notion-hosted file attachment,
independent of the 7-day R2 presigned URL expiry.

Usage:
  python3 scripts/push_images_to_notion.py --episode-id genghis-khan-2026-ep005 --cache-dir /tmp/vf/img_cache
"""
import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"
DB_TITLE = "Image Asset Library"


def _token():
    return os.environ.get("NOTION_TOKEN")


def _request(method, path, token, body=None, base=API_BASE):
    url = base + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"raw_error": str(e)}
        return e.code, payload


def find_database_id(token):
    status, payload = _request("POST", "/search", token, {"query": DB_TITLE, "filter": {"value": "database", "property": "object"}})
    if status != 200:
        raise RuntimeError("search failed: " + json.dumps(payload)[:300])
    for result in payload.get("results", []):
        title_parts = result.get("title", [])
        title_text = "".join(t.get("plain_text", "") for t in title_parts)
        if DB_TITLE.lower() in title_text.lower():
            return result["id"]
    raise RuntimeError("database not found: " + DB_TITLE)


def query_rows(token, database_id, episode_id, status_name):
    body = {
        "filter": {
            "and": [
                {"property": "Episode ID", "rich_text": {"equals": episode_id}},
                {"property": "Status", "status": {"equals": status_name}},
            ]
        },
        "page_size": 100,
    }
    rows = []
    cursor = None
    while True:
        if cursor:
            body["start_cursor"] = cursor
        status, payload = _request("POST", "/databases/%s/query" % database_id, token, body)
        if status != 200:
            raise RuntimeError("query failed: " + json.dumps(payload)[:300])
        rows.extend(payload.get("results", []))
        if payload.get("has_more"):
            cursor = payload.get("next_cursor")
        else:
            break
    return rows


def get_prop_text(props, name):
    prop = props.get(name)
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    return ""


def get_prop_files(props, name):
    prop = props.get(name)
    if not prop or prop.get("type") != "files":
        return []
    return prop.get("files", [])


def create_file_upload(token, filename):
    status, payload = _request("POST", "/file_uploads", token, {"filename": filename, "mode": "single_part"})
    if status not in (200, 201):
        raise RuntimeError("create_file_upload failed: " + json.dumps(payload)[:300])
    return payload["id"], payload["upload_url"]


def send_file_upload(token, upload_url, file_path):
    filename = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    boundary = uuid.uuid4().hex
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    parts = []
    parts.append(("--%s\r\n" % boundary).encode("utf-8"))
    parts.append(('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % filename).encode("utf-8"))
    parts.append(("Content-Type: %s\r\n\r\n" % mime_type).encode("utf-8"))
    parts.append(file_bytes)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(upload_url, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"raw_error": str(e)}
        return e.code, payload


def attach_to_page(token, page_id, file_upload_id, filename):
    body = {
        "properties": {
            "Image": {
                "files": [
                    {"type": "file_upload", "file_upload": {"id": file_upload_id}, "name": filename}
                ]
            }
        }
    }
    status, payload = _request("PATCH", "/pages/%s" % page_id, token, body)
    return status, payload


YOUTUBE_REGISTRY_DB_TITLE = "YouTube Channel & Video Metadata Registry"


def find_youtube_registry_db_id(token):
    status, payload = _request("POST", "/search", token, {"query": YOUTUBE_REGISTRY_DB_TITLE, "filter": {"value": "database", "property": "object"}})
    if status != 200:
        raise RuntimeError("search failed: " + json.dumps(payload)[:300])
    for result in payload.get("results", []):
        title_parts = result.get("title", [])
        title_text = "".join(t.get("plain_text", "") for t in title_parts)
        if YOUTUBE_REGISTRY_DB_TITLE.lower() in title_text.lower():
            return result["id"]
    return None


def sync_thumbnail_to_youtube_registry(token, episode_id, file_url):
    """23/08/2026: after a 'thumbnail' image is attached to the Image Asset
    Library, mirror its Notion-hosted URL onto the matching YouTube Registry
    row's Thumbnail URL property, so B10 upload / reporting can reference it
    without a manual Human Gate 2 step. Best-effort: any failure is logged
    and swallowed so it never blocks the main image-sync loop."""
    try:
        db_id = find_youtube_registry_db_id(token)
        if not db_id:
            print("WARN(thumbnail_sync) YouTube Registry DB not found")
            return False
        status, payload = _request("POST", "/databases/%s/query" % db_id, token, {
            "filter": {"property": "Episode ID", "rich_text": {"equals": episode_id}},
            "page_size": 1,
        })
        if status != 200:
            print("WARN(thumbnail_sync) query failed: " + json.dumps(payload)[:200])
            return False
        results = payload.get("results", [])
        if not results:
            print("WARN(thumbnail_sync) no YouTube Registry row for episode_id=%s" % episode_id)
            return False
        reg_page_id = results[0]["id"]
        patch_status, patch_payload = _request("PATCH", "/pages/%s" % reg_page_id, token, {
            "properties": {"Thumbnail URL": {"url": file_url}}
        })
        if patch_status not in (200, 201):
            print("WARN(thumbnail_sync) patch failed: " + json.dumps(patch_payload)[:200])
            return False
        print("OK(thumbnail_sync) episode_id=%s reg_page_id=%s" % (episode_id, reg_page_id))
        return True
    except Exception as e:
        print("WARN(thumbnail_sync) exception: %r" % e)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--cache-dir", default="/tmp/vf/img_cache")
    ap.add_argument("--status", default="Approved")
    args = ap.parse_args()

    token = _token()
    if not token:
        print("ERROR: no NOTION_TOKEN in env")
        sys.exit(1)

    database_id = find_database_id(token)
    rows = query_rows(token, database_id, args.episode_id, args.status)
    print("FOUND_ROWS=%d episode_id=%s status=%s" % (len(rows), args.episode_id, args.status))

    n_ok, n_skip, n_fail = 0, 0, 0
    for row in rows:
        page_id = row["id"]
        props = row.get("properties", {})
        name = get_prop_text(props, "Name")
        r2_path = get_prop_text(props, "R2 Path")
        existing_files = get_prop_files(props, "Image")

        if existing_files:
            print("SKIP(has_image) page_id=%s name=%r" % (page_id, name))
            n_skip += 1
            continue
        if not r2_path:
            print("SKIP(no_r2_path) page_id=%s name=%r" % (page_id, name))
            n_skip += 1
            continue

        basename = os.path.basename(r2_path)
        local_path = os.path.join(args.cache_dir, basename)
        if not os.path.isfile(local_path):
            print("SKIP(no_local_file) page_id=%s name=%r local_path=%s" % (page_id, name, local_path))
            n_skip += 1
            continue

        try:
            upload_id, upload_url = create_file_upload(token, basename)
            send_status, send_payload = send_file_upload(token, upload_url, local_path)
            if send_status not in (200, 201):
                print("FAIL(send) page_id=%s name=%r status=%s payload=%s" % (page_id, name, send_status, json.dumps(send_payload)[:200]))
                n_fail += 1
                continue
            attach_status, attach_payload = attach_to_page(token, page_id, upload_id, basename)
            if attach_status not in (200, 201):
                print("FAIL(attach) page_id=%s name=%r status=%s payload=%s" % (page_id, name, attach_status, json.dumps(attach_payload)[:200]))
                n_fail += 1
                continue
            print("OK page_id=%s name=%r local_path=%s upload_id=%s" % (page_id, name, local_path, upload_id))
            n_ok += 1

            # 23/08/2026: if this row is the episode's thumbnail image, also
            # mirror its hosted URL onto the YouTube Registry row so the
            # thumbnail is tracked end-to-end without a manual Gate 2 step.
            if "thumbnail" in (name or "").lower():
                try:
                    new_files = attach_payload.get("properties", {}).get("Image", {}).get("files", [])
                    file_url = None
                    for fobj in new_files:
                        if fobj.get("type") == "file" and fobj.get("file", {}).get("url"):
                            file_url = fobj["file"]["url"]
                    if file_url:
                        sync_thumbnail_to_youtube_registry(token, args.episode_id, file_url)
                    else:
                        print("WARN(thumbnail_sync) no file url found in attach_payload for page_id=%s" % page_id)
                except Exception as e:
                    print("WARN(thumbnail_sync) exception page_id=%s err=%r" % (page_id, e))
        except Exception as e:
            print("FAIL(exception) page_id=%s name=%r err=%r" % (page_id, name, e))
            n_fail += 1

    print("SUMMARY ok=%d skip=%d fail=%d total=%d" % (n_ok, n_skip, n_fail, len(rows)))


if __name__ == "__main__":
    main()
