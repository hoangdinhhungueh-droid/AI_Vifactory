#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-episode B4 completion poller (real Moc-2 wiring, 29/08/2026).

hero_resume_poller.py (Moc 1) proved the Notion boilerplate but only ever
watched hero-flagged rows and explicitly left continuation unwired ("Needs
S5 resume-capability confirmed before wiring"). S5 resume is confirmed now
(scripts/resume_episode.py + scripts/continue_after_images.py, traced against
the live run_episode.py S4.5/S4.6/S7 path). This script closes that gap:

For every episode under /var/vf/episodes/ that has a prompts_forge.json (i.e.
went through the B3.5/HG2 Antigravity image hand-off) and is not already
past this leg, it:

  1. Reads the expected set of {Background, Foreground} Reuse Keys from
     that episode's prompts_forge.json.
  2. Queries Notion Image Asset Library CHILD DB (per-episode) for rows with
     that Episode ID whose Status is Approved or Pulled by VPS.
  3. If every expected key is covered -> spawns
     scripts/continue_after_images.py for that episode (detached, same
     lock-file convention as telegram_actions._spawn_production) and marks
     the episode so it is not re-spawned on the next poll tick.
  4. Otherwise does nothing (still waiting on Antigravity/quota).

Intended to run every few minutes from cron (this codebase's established
convention for batch jobs -- see crontab: backup_postgres.sh,
run_trend_pipeline.py, cleanup_r2_old_files.py all run this way, not pm2):

  */10 * * * * cd /root/video_factory && /usr/bin/python3 scripts/image_completion_poller.py >> /var/log/vf_image_completion_poller.log 2>&1

Safe to run concurrently with itself: the same /var/vf/locks/<id>.lock
O_CREAT|O_EXCL guard used by the HG1 dispatch path prevents a double-spawn.

FIXED 01/09/2026: Query per-episode child DB instead of parent DB (Issue #3).
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, '/root/video_factory')
from scripts.ag_notion_bridge import resolve_episode_image_asset_db

EPISODES = Path("/var/vf/episodes")
LOCK_DIR = Path("/var/vf/locks")
LOG_DIR = Path("/var/vf/logs")
NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"
APPROVED_STATUSES = {"Approved", "Pulled by VPS"}


def _load_env():
    for path in ("/etc/environment", "/root/secrets/.env"):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[7:]
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and not os.environ.get(k):
                        os.environ[k] = v
        except OSError:
            continue


def _log(msg):
    print("[%s] %s" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg), flush=True)


def _token():
    return os.environ.get("NOTION_TOKEN")


def _request(method, path, token, body=None, retries=2):
    """Notion occasionally stalls mid-response (seen live: SSL read timeout on
    a /databases/query call) -- retry transient network errors, but not
    HTTP-level errors (401/429/etc), which are real answers, not glitches."""
    url = API_BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last_exc = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Notion-Version", NOTION_VERSION)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read().decode("utf-8"))
            except Exception:
                payload = {"raw_error": str(e)}
            return e.code, payload
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
    raise RuntimeError("network error after %d attempts: %s" % (retries + 1, last_exc))


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


def get_prop_status(props, name):
    prop = props.get(name)
    if not prop:
        return ""
    if prop.get("type") == "status":
        return (prop.get("status") or {}).get("name", "")
    if prop.get("type") == "select":
        return (prop.get("select") or {}).get("name", "")
    return ""


def query_approved_keys(token, db_id, episode_id):
    """-> set of Reuse Key strings with Status in APPROVED_STATUSES for this episode."""
    body = {"filter": {"property": "Episode ID",
                       "rich_text": {"equals": episode_id}}}
    keys = set()
    cursor = None
    while True:
        if cursor:
            body["start_cursor"] = cursor
        status, payload = _request("POST", "/databases/%s/query" % db_id, token, body)
        if status != 200:
            raise RuntimeError("query failed: " + json.dumps(payload)[:300])
        for row in payload.get("results", []):
            props = row.get("properties", {})
            st = get_prop_status(props, "Status")
            if st not in APPROVED_STATUSES:
                continue
            rk = get_prop_text(props, "Reuse Key")
            if rk:
                keys.add(rk)
        if not payload.get("has_more"):
            break
        cursor = payload.get("next_cursor")
    return keys


def expected_keys(episode_dir):
    """-> set of every Reuse Key the episode needs, from prompts_forge.json.

    Confirmed live shape: top-level "backgrounds"
    and "foregrounds", each a dict of {reuse_key: prompt_text} -- not a list.
    """
    forge_path = episode_dir / "prompts_forge.json"
    forge = json.loads(forge_path.read_text(encoding="utf-8"))
    keys = set()
    for layer in ("backgrounds", "foregrounds"):
        items = forge.get(layer)
        if isinstance(items, dict):
            keys.update(k for k in items if k)
        elif isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    rk = item.get("reuse_key") or item.get("Reuse Key")
                    if rk:
                        keys.add(rk)
                elif isinstance(item, str):
                    keys.add(item)
    return keys


def _lock_path(episode_id):
    # Deliberately a DIFFERENT lock name than telegram_actions._spawn_production's
    # "<id>.lock" (the HG1 dispatch lock). That lock is never unlinked after a
    # successful run, only on spawn failure, so it stays present for the rest
    # of the episode's life -- reusing it here would make every episode look
    # "already dispatched" for B4->B10 forever, without ever actually running it.
    return LOCK_DIR / ("%s.b4b10.lock" % episode_id)


def already_dispatched(episode_id):
    return _lock_path(episode_id).exists()


def spawn_continuation(episode_id):
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(episode_id)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        _log("%s: lock already held, skipping (already running or done)" % episode_id)
        return False
    log_path = LOG_DIR / ("%s_b4b10.log" % episode_id)
    try:
        logfd = os.open(str(log_path), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        proc = subprocess.Popen(
            [sys.executable, "scripts/continue_after_images.py",
             "--episode-id", episode_id],
            cwd="/root/video_factory",
            stdout=logfd, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True, pass_fds=(logfd,),
        )
        os.write(fd, str(proc.pid).encode())
        os.close(logfd)
        _log("%s: dispatched continue_after_images.py pid=%d log=%s" %
             (episode_id, proc.pid, log_path))
        return True
    except Exception as e:
        os.unlink(str(lock))
        _log("%s: spawn failed: %s" % (episode_id, e))
        return False
    finally:
        os.close(fd)


def main():
    _load_env()
    token = _token()
    if not token:
        _log("ERROR no NOTION_TOKEN in env")
        return 1
    if not EPISODES.exists():
        _log("ERROR no episodes dir at %s" % EPISODES)
        return 1

    candidates = sorted(p for p in EPISODES.iterdir()
                        if p.is_dir() and not p.name.startswith("_dead_")
                        and (p / "prompts_forge.json").exists())
    if not candidates:
        _log("no candidate episodes with prompts_forge.json")
        return 0

    for ep_dir in candidates:
        episode_id = ep_dir.name
        if (ep_dir / "final_169.mp4").exists():
            continue  # already rendered; nothing to poll for
        if already_dispatched(episode_id):
            continue

        try:
            need = expected_keys(ep_dir)
        except Exception as e:
            _log("%s: cannot read prompts_forge.json: %s" % (episode_id, e))
            continue
        if not need:
            _log("%s: prompts_forge.json has no reuse keys, skipping" % episode_id)
            continue

        # FIXED: Resolve per-episode child DB instead of querying parent
        try:
            db_result = resolve_episode_image_asset_db(episode_id, create_if_missing=False)
            if db_result.get("error"):
                _log("%s: no child DB found, skipping (images not yet synced)" % episode_id)
                continue
            episode_db_id = db_result["db_id"]
            have = query_approved_keys(token, episode_db_id, episode_id)
        except Exception as e:
            _log("%s: failed to resolve child DB or query: %s" % (episode_id, e))
            continue

        missing = need - have
        if missing:
            _log("%s: waiting on %d/%d images (%s%s)" % (
                episode_id, len(missing), len(need),
                ", ".join(sorted(missing)[:5]),
                ", ..." if len(missing) > 5 else ""))
            continue
        _log("%s: all %d images Approved -> triggering B4->B10" %
             (episode_id, len(need)))
        spawn_continuation(episode_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
