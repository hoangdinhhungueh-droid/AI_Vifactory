#!/usr/bin/env python3
"""Pull Approved (or other status) images from the Notion "Image Asset
Library" for one episode down to the VPS local filesystem, for use by the
generic 2-layer (Background/Foreground) Remotion pipeline.

Generalizes scripts/hero_resume_poller.py (which only handled
Is Hero Reference=true rows) to any Background/Foreground row for a given
Episode ID.

Usage:
  python3 scripts/pull_approved_images.py \
      --episode-id genghis-khan-2026-ep005 \
      [--statuses Approved] \
      [--out-dir /var/vf/episodes/genghis-khan-2026-ep005/assets] \
      [--no-mark]

For each matching row:
  - Downloads the Notion "Image" file property if present (temporary
    Notion-hosted URL, valid ~1 hour).
  - Else downloads from Cloudflare R2 using the "R2 Path" property. R2
    config mirrors app/services/image_gen.py's _r2_config()/_r2_upload():
    endpoint = R2_ENDPOINT or R2_ENDPOINT_URL or derived from
    CLOUDFLARE_ACCOUNT_ID; bucket = R2_BUCKET or R2_BUCKET_NAME or
    "vf-assets" (default); "R2 Path" is the full object key within that
    bucket (NOT "bucket/key" -- do not split on "/").
  - Writes <out-dir>/<slug(Reuse Key or Name)>.jpg
  - FIX 07/08/2026 (QC feedback #1, background not removed on composited
    core/character images): when a row's Layer Type is "Foreground/Overlay",
    additionally runs the pure-Pillow chroma-key remover
    (scripts/remove_bg_chromakey.py) against the downloaded jpg to produce
    a real-alpha "<slug>_nobg.png" alongside it, and points the manifest's
    local_path at that PNG instead of the raw jpg. All current Foreground
    Style Lock prompts bake in a solid magenta (#FF00FF-ish) backdrop
    specifically so this key can run reliably. Remotion's existing
    <Img style={{objectFit:"contain"}}> renders PNG alpha transparently with
    no further composition changes needed. If the chroma-key step fails for
    any reason, we fall back to the raw jpg (never hard-fails the pull).
    An ML-matting alternative (rembg/onnxruntime) was tried first and
    rejected: this VPS's CPU does not support the x86-64-v2 instruction
    baseline those wheels require (numpy>=2 fails to import at all, even in
    a fully isolated venv) -- see Decisions Log for 07/08/2026.
  - Writes <out-dir>/manifest.json mapping reuse_key/name -> local path,
    Layer Type, Scene Index (consumed by scripts/build_remotion_props.py).
  - Marks Status = "Pulled by VPS" on success (unless --no-mark).
"""
import argparse
import json
import os
import re
import sys

# FIX 02/09/2026: Add repo root to sys.path BEFORE app.* imports
# to prevent ModuleNotFoundError when run as subprocess
sys.path.insert(0, "/root/video_factory")

from app.services.quota_manager import (
    read_quota, is_quota_available, get_retry_wait_seconds, mark_resumed
)
import urllib.error
import urllib.request

# Sibling module: pure-Pillow chroma-key background remover (no numpy/scipy/
# onnxruntime dependency -- see remove_bg_chromakey.py docstring for why).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from remove_bg_chromakey import remove_bg_chromakey
except Exception as _e:  # pragma: no cover - defensive, never hard-fail the pull
    remove_bg_chromakey = None
    print("WARNING: remove_bg_chromakey unavailable (%r); Foreground rows will keep raw jpg" % (_e,))

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"
DB_TITLE = "Image Asset Library"


def _token():
    try:
        from compile_episode_from_notion import _token as _ctoken
        t = _ctoken()
        if t:
            return t
    except Exception:
        pass
    return os.environ.get("NOTION_TOKEN", "")


def _request(method, path, token, body=None):
    url = API_BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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


def query_rows(token, database_id, episode_id, statuses):
    status_filters = [{"property": "Status", "status": {"equals": s}} for s in statuses]
    or_filter = status_filters[0] if len(status_filters) == 1 else {"or": status_filters}
    body = {
        "filter": {
            "and": [
                {"property": "Episode ID", "rich_text": {"equals": episode_id}},
                or_filter,
            ]
        },
        "page_size": 100,
    }
    status, payload = _request("POST", "/databases/%s/query" % database_id, token, body)
    if status != 200:
        raise RuntimeError("query failed: " + json.dumps(payload)[:300])
    return payload.get("results", [])


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


def get_prop_number(props, name):
    prop = props.get(name)
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def get_prop_select(props, name):
    prop = props.get(name)
    if not prop:
        return None
    if prop.get("type") == "select" and prop.get("select"):
        return prop["select"].get("name")
    if prop.get("type") == "status" and prop.get("status"):
        return prop["status"].get("name")
    return None


def get_prop_files(props, name):
    prop = props.get(name)
    if not prop or prop.get("type") != "files":
        return []
    out = []
    for f in prop.get("files", []):
        if f.get("type") == "file":
            out.append(f["file"]["url"])
        elif f.get("type") == "external":
            out.append(f["external"]["url"])
    return out


def slugify(s):
    s = (s or "untitled").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "untitled"


def download(url, out_path):
    req = urllib.request.Request(url, headers={"User-Agent": "vf-pull/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(out_path, "wb") as f:
        f.write(data)
    return len(data)


def _r2_config():
    """Mirror app/services/image_gen.py's _r2_config() env-var precedence."""
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    ak = os.environ.get("R2_ACCESS_KEY_ID")
    sk = os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket = os.environ.get("R2_BUCKET") or os.environ.get("R2_BUCKET_NAME") or "vf-assets"
    endpoint = (
        os.environ.get("R2_ENDPOINT")
        or os.environ.get("R2_ENDPOINT_URL")
        or (("https://" + account + ".r2.cloudflarestorage.com") if account else "")
    )
    if not (ak and sk and endpoint):
        return None
    return {"endpoint": endpoint, "ak": ak, "sk": sk, "bucket": bucket}


def download_from_r2(r2_path, out_path):
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 not installed; cannot pull R2 Path assets (pip install boto3)")
    cfg = _r2_config()
    if not cfg:
        raise RuntimeError("missing R2 creds in env (R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY/endpoint)")
    # r2_path is the full object key within the configured bucket (as written
    # by image_gen.py's _r2_upload); it is NOT "bucket/key" -- do not split.
    key = r2_path.lstrip("/")
    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["ak"],
        aws_secret_access_key=cfg["sk"],
        region_name="auto",
    )
    s3.download_file(cfg["bucket"], key, out_path)
    return os.path.getsize(out_path)


def mark_pulled(token, page_id):
    body = {"properties": {"Status": {"status": {"name": "Pulled by VPS"}}}}
    status, _ = _request("PATCH", "/pages/%s" % page_id, token, body)
    return status == 200


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--statuses", default="Approved",
                    help="comma-separated list (default: Approved)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--no-mark", action="store_true",
                    help="skip marking Status = Pulled by VPS after download")
    args = ap.parse_args()

    statuses = [s.strip() for s in args.statuses.split(",")]
    out_dir = args.out_dir or os.path.join("/var/vf/episodes", args.episode_id, "images")
    os.makedirs(out_dir, exist_ok=True)

    token = _token()
    manifest_path = os.path.join(out_dir, "manifest.json")
    
    # Check if local assets already exist from previous stage
    ep_dir = os.path.dirname(out_dir)
    prompts_file = os.path.join(ep_dir, "prompts_forge.json")
    if os.path.exists(prompts_file):
        try:
            with open(prompts_file) as pf:
                pd = json.load(pf)
            local_manifest = []
            for k in pd.get("backgrounds", {}):
                p = os.path.join(out_dir, f"{k}.png")
                p_asset = os.path.join(ep_dir, "assets", f"{k}.png")
                if not os.path.exists(p) and os.path.exists(p_asset):
                    import shutil; shutil.copyfile(p_asset, p)
                if os.path.exists(p):
                    local_manifest.append({"name": k, "reuse_key": k, "layer_type": "Background", "local_path": p, "status": "Approved"})
            for k in pd.get("foregrounds", {}):
                p = os.path.join(out_dir, f"{k}.png")
                p_trans = os.path.join(ep_dir, "assets", f"{k}_transparent.png")
                p_asset = os.path.join(ep_dir, "assets", f"{k}.png")
                if not os.path.exists(p):
                    if os.path.exists(p_trans):
                        import shutil; shutil.copyfile(p_trans, p)
                    elif os.path.exists(p_asset):
                        import shutil; shutil.copyfile(p_asset, p)
                if os.path.exists(p):
                    local_manifest.append({"name": k, "reuse_key": k, "layer_type": "Foreground/Overlay", "local_path": p, "status": "Approved"})
            if len(local_manifest) >= len(pd.get("backgrounds", {})) + len(pd.get("foregrounds", {})) and len(local_manifest) > 0:
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(local_manifest, f, indent=2)
                print(f"LOCAL_PULLED: {len(local_manifest)} images from local cache -> {manifest_path}")
                return
        except Exception as _e_local:
            print(f"DEBUG: Local manifest fallback skipped: {_e_local}")

    if not token:
        raise RuntimeError("NOTION_TOKEN not set")

    try:
        database_id = find_database_id(token)
    except Exception as _e_db:
        print(f"WARNING: find_database_id failed: {_e_db}")
        database_id = "f9101989-2400-830c-ab89-01700bb07933" 
    rows = query_rows(token, database_id, args.episode_id, statuses)
    print("FOUND_ROWS=%d statuses=%s episode_id=%s" % (len(rows), statuses, args.episode_id))

    # Check quota state (anti-429 pattern)
    current_quota = read_quota()
    if current_quota and not is_quota_available(current_quota):
        wait_sec = get_retry_wait_seconds(current_quota)
        wait_min = wait_sec / 60
        print(f"QUOTA_EXHAUSTED: {current_quota.images_generated}/{current_quota.target_count} generated.")
        print(f"Quota will reset in ~{wait_min:.0f} minutes. Try again at: {current_quota.quota_reset_at}")
        print(f"(You can retry: python3 scripts/pull_approved_images.py --episode-id {args.episode_id})")
        sys.exit(0)  # Not fatal; poller will retry
    
    if current_quota and current_quota.status == "QUOTA_EXHAUSTED":
        # Quota has reset; mark resumed
        mark_resumed(current_quota)
        print(f"INFO: Quota has reset. Resuming from {current_quota.images_generated}/{current_quota.target_count}")

    manifest = []
    for row in rows:
        page_id = row["id"]
        props = row.get("properties", {})
        name = get_prop_text(props, "Name")
        reuse_key = get_prop_text(props, "Reuse Key")
        r2_path = get_prop_text(props, "R2 Path")
        layer_type = get_prop_select(props, "Layer Type")
        scene_index = get_prop_number(props, "Scene Index")
        status = get_prop_select(props, "Status")
        files = get_prop_files(props, "Image")

        slug = slugify(reuse_key or name)
        out_path = os.path.join(out_dir, slug + ".jpg")

        source = None
        try:
            if files:
                download(files[0], out_path)
                source = "notion_file"
            elif r2_path:
                download_from_r2(r2_path, out_path)
                source = "r2"
            else:
                print("SKIP page_id=%s name=%r: no Image file and no R2 Path" % (page_id, name))
                continue
        except Exception as e:
            print("FAIL page_id=%s name=%r err=%r" % (page_id, name, e))
            continue

        local_path = out_path
        if layer_type == "Foreground/Overlay" and remove_bg_chromakey is not None:
            # FIX 07/08/2026 (QC feedback #1): strip the solid magenta backdrop
            # from core/character composites so Remotion renders them with a
            # real transparent background instead of a flat color block.
            # FIX 08/08/2026 (Rule 76): validate transparency after chroma-key.
            # If _nobg.png has <80% transparent pixels, the source image likely
            # lacks a proper magenta backdrop -- FAIL HARD instead of falling
            # back to raw jpg (which would reintroduce the background bug).
            try:
                alpha_path = os.path.splitext(out_path)[0] + "_nobg.png"
                remove_bg_chromakey(out_path, alpha_path)
                # Validate: foreground must have >80% transparent pixels
                from PIL import Image as _ValImg
                _vim = _ValImg.open(alpha_path).convert("RGBA")
                _vw, _vh = _vim.size
                _vtrans = sum(1 for _vpx in _vim.getdata() if _vpx[3] < 128)
                _vtotal = _vw * _vh
                _vtrans_pct = 100 * _vtrans / _vtotal if _vtotal > 0 else 0
                if _vtrans_pct < 80:
                    raise RuntimeError(
                        "chroma-key produced only %.1f%% transparent pixels (need >80%%); "
                        "source image may lack proper magenta backdrop" % _vtrans_pct
                    )
                local_path = alpha_path
                print("BG_REMOVED page_id=%s -> %s (transparent=%.1f%%)" % (page_id, alpha_path, _vtrans_pct))
            except Exception as e:
                print("BG_REMOVE_FAILED page_id=%s err=%r (FAILING -- no raw jpg fallback per Rule 76)" % (page_id, e))
                # Rule 76: do NOT fall back to raw jpg -- it reintroduces the
                # background bug. Skip this image entirely instead.
                continue

        print("PULLED page_id=%s name=%r layer=%r scene_index=%r -> %s (%s)" % (
            page_id, name, layer_type, scene_index, local_path, source))
        manifest.append({
            "page_id": page_id, "name": name, "reuse_key": reuse_key,
            "layer_type": layer_type, "scene_index": scene_index,
            "status": status, "local_path": local_path, "source": source,
        })
        if not args.no_mark:
            marked = mark_pulled(token, page_id)
            print("MARKED_PULLED page_id=%s ok=%s" % (page_id, marked))

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print("WROTE_MANIFEST", manifest_path, len(manifest), "rows")


if __name__ == "__main__":
    main()
