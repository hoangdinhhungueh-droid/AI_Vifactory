"""Dispatch table for Telegram inline-button callbacks (VF approval loop).

callback_data format: "<act>:<arg>"
  ap:<pageid>    approve a Brain DB row    -> Pipeline Status = "Approved→Story"
  rj:<pageid>    reject a Brain DB row     -> Pipeline Status = "Rejected"
  up:<episode_id> upload a rendered episode to YouTube (private/unlisted per
                 upload_mode) via youtube_upload.upload_from_payload(), then
                 best-effort attaches subtitles.srt as captions.
  pub:<videoId>  publish a YouTube video   -> privacyStatus = "public"
  kp:<videoId>   keep private (ack only)
  tg             toggle default upload mode (anonymous <-> public)
  puball         publish ALL pending videos in publish_ledger.py

Each handler is FAIL-SAFE and returns (reply_text, show_alert).
Network helpers are module-level so tests can monkeypatch them.

CANONICAL_LABEL_2026_08_23: Trend Brain has exactly ONE canonical pipeline-state
field: "" (empty string property name in Notion API, display as Status) with fallback
to "Pipeline Status". The old "Storyable Verdict" field was an orphan write-only
field with no reader anywhere in the pipeline and has been retired.
"""
from __future__ import annotations

import os
import logging

_log = logging.getLogger("app.telegram_actions")

try:
    from dotenv import load_dotenv
    load_dotenv("/root/secrets/.env", override=True)
except Exception:
    pass

NOTION_API = "https://api.notion.com/v1"

_EPISODES_ROOT = os.getenv("VF_EPISODES_ROOT", "/var/vf/episodes")


def _notion_headers():
    token = os.getenv("NOTION_TOKEN")
    if not token:
        return None
    return {"Authorization": "Bearer " + token,
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"}


def _set_pipeline_status(page_id, status_name):
    headers = _notion_headers()
    if not headers:
        return False, "no NOTION_TOKEN"
    import httpx
    # Try "" property first (Notion Trend Brain schema), then fallback to "Pipeline Status"
    patch1 = {"properties": {"": {"status": {"name": status_name}}}}
    try:
        r = httpx.patch("%s/pages/%s" % (NOTION_API, page_id),
                        headers=headers, json=patch1, timeout=30.0)
        if r.status_code in (200, 201):
            return True, ""
        patch2 = {"properties": {"Pipeline Status": {"status": {"name": status_name}}}}
        r2 = httpx.patch("%s/pages/%s" % (NOTION_API, page_id),
                         headers=headers, json=patch2, timeout=30.0)
        if r2.status_code in (200, 201):
            return True, ""
        return False, "HTTP %s: %s" % (r.status_code, r.text[:150])
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _yt_set_public(video_id, market=None):
    """Set YouTube video to public. Multi-market aware (EN, JP, KR)."""
    markets_to_try = [market.lower()] if market else ["en", "jp", "kr"]
    import httpx
    for m in markets_to_try:
        if m == "jp":
            cid = os.getenv("JP_YT_OAUTH_CLIENT_ID") or os.getenv("YT_OAUTH_CLIENT_ID", "")
            csec = os.getenv("JP_YT_OAUTH_CLIENT_SECRET") or os.getenv("YT_OAUTH_CLIENT_SECRET", "")
            refresh = os.getenv("JP_YT_OAUTH_REFRESH_TOKEN") or os.getenv("YT_OAUTH_REFRESH_TOKEN_JP", "")
        elif m == "kr":
            cid = os.getenv("KR_YT_OAUTH_CLIENT_ID") or os.getenv("YT_OAUTH_CLIENT_ID", "")
            csec = os.getenv("KR_YT_OAUTH_CLIENT_SECRET") or os.getenv("YT_OAUTH_CLIENT_SECRET", "")
            refresh = os.getenv("KR_YT_OAUTH_REFRESH_TOKEN") or os.getenv("YT_OAUTH_REFRESH_TOKEN_KR", "")
        else:
            cid = os.getenv("YT_OAUTH_CLIENT_ID", "")
            csec = os.getenv("YT_OAUTH_CLIENT_SECRET", "")
            refresh = os.getenv("YT_OAUTH_REFRESH_TOKEN", "")

        if not (cid and csec and refresh):
            continue

        try:
            tok = httpx.post("https://oauth2.googleapis.com/token", data={
                "client_id": cid, "client_secret": csec,
                "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=30)
            if tok.status_code != 200:
                continue
            access = tok.json()["access_token"]
            body = {"id": video_id, "status": {"privacyStatus": "public"}}
            r = httpx.put("https://www.googleapis.com/youtube/v3/videos",
                          params={"part": "status"},
                          headers={"Authorization": "Bearer " + access,
                                   "Content-Type": "application/json"},
                          json=body, timeout=60)
            if r.status_code == 200:
                return True, ""
            if r.status_code == 404:
                # Video may belong to another channel
                continue
            return False, "update HTTP %s: %s" % (r.status_code, r.text[:150])
        except Exception as e:  # noqa: BLE001
            return False, str(e)
    return False, "no OAuth env or video not found on any channel"


def _yt_upload_episode(episode_id):
    """Upload a rendered episode's YouTube payload. Multi-market aware."""
    try:
        from app.services import youtube_upload, upload_mode
    except Exception as e:  # noqa: BLE001
        return "⚠️ Lỗi nạp module upload: " + str(e), True
    episode_dir = os.path.join(_EPISODES_ROOT, episode_id) if episode_id else ""
    if not episode_id or not os.path.isdir(episode_dir):
        return "⚠️ Không tìm thấy thư mục episode: " + str(episode_id), True
    try:
        privacy = upload_mode.privacy_status()
        resp = youtube_upload.upload_from_payload(episode_dir, privacy_status=privacy)
    except Exception as e:  # noqa: BLE001
        return "⚠️ Lỗi upload: " + str(e), True
    if isinstance(resp, dict) and resp.get("upload_blocked"):
        return "🚫 Upload bị chặn: " + str(resp.get("reason", "unknown")), True
    vid = resp.get("id") if isinstance(resp, dict) else None
    if not vid:
        return "⚠️ Upload thất bại: không nhận được videoId.", True
    cap_note = ""
    srt_path = os.path.join(episode_dir, "subtitles.srt")
    if os.path.exists(srt_path):
        try:
            youtube_upload.upload_captions(vid, srt_path)
            cap_note = " + phụ đề"
        except Exception as _ce:  # noqa: BLE001
            cap_note = " (lỗi phụ đề: %s)" % str(_ce)[:80]
    return ("✅ Đã upload lên YouTube (%s)%s.\nvideoId: %s\nhttps://youtu.be/%s"
            % (privacy, cap_note, vid, vid)), False


def parse_callback_data(data):
    """'ap:abc' -> ('ap','abc'); no colon -> (data,'')."""
    s = data or ""
    if ":" in s:
        act, _, arg = s.partition(":")
        return act, arg
    return s, ""


VF_LOCK_DIR = "/var/vf/locks"
VF_LOG_DIR = "/var/vf/logs"


def _spawn_production(task_id):
    """Fire-and-forget the B1.5->B2->B3->B3.5 chain for one approved market.

    One process per market: approving EN must not start JP/KR, and an OOM in
    one market cannot take the others down with it. Detached from vf-api
    (start_new_session) so an API restart mid-chain does not kill the run.
    Returns a short status string for the button reply.
    """
    import os
    import subprocess
    os.makedirs(VF_LOCK_DIR, exist_ok=True)
    os.makedirs(VF_LOG_DIR, exist_ok=True)
    lock = os.path.join(VF_LOCK_DIR, "%s.lock" % task_id)
    try:
        # O_EXCL makes the double-tap lose the race instead of spawning twice.
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return "already running"
    log_path = os.path.join(VF_LOG_DIR, "%s.log" % task_id)
    try:
        # Use os.open() for unbuffered I/O (better for detached subprocesses)
        logfd = os.open(log_path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        proc = subprocess.Popen(
            ["/root/video_factory/venv/bin/python3", "scripts/produce_episode_hg1.py", str(task_id)],
            cwd="/root/video_factory",
            stdout=logfd, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True,
            pass_fds=(logfd,)
        )
        os.write(fd, str(proc.pid).encode())
        os.close(logfd)  # Close in parent; subprocess has its copy
        return "pid %d" % proc.pid
    except Exception as e:
        os.unlink(lock)
        _log.error("[dispatch] gate1 spawn for %s failed: %s", task_id, e)
        return "spawn failed: %s" % e
    finally:
        os.close(fd)


def _gate1_approve_or_reject(task_id, approve):
    """Shared Gate 1 approve/reject logic for a single market task_id.
    Used by both the single apr/rej buttons and the ap_all/rj_all bulk
    buttons.
    Searches Notion Story Library and Trend Brain DB across Task ID, Episode ID, and Name.
    Returns (reply_text, is_error).
    """
    import httpx as _hx
    hdrs = _notion_headers()
    story_db = 'b0301989-2400-836b-bdb5-8131fea17736'  # Story Library DB
    trend_db = '4c101989-2400-8334-8016-01d4f463b09f'  # Trend Brain DB
    page_id = None
    keyword = ''
    if hdrs and task_id:
        # 1. Search Story Library DB across Task ID, Episode ID, Name
        try:
            query_body = {
                "filter": {
                    "or": [
                        {"property": "Task ID", "rich_text": {"equals": str(task_id)}},
                        {"property": "Episode ID", "rich_text": {"equals": str(task_id)}},
                        {"property": "Name", "title": {"contains": str(task_id)}},
                    ]
                },
                "page_size": 1
            }
            r = _hx.post(NOTION_API + '/databases/' + story_db + '/query', headers=hdrs, json=query_body, timeout=10.0)
            rs = r.json().get('results', [])
            if rs:
                page_id = rs[0].get('id')
                kw_prop = rs[0].get('properties', {}).get('Keyword', {}).get('rich_text', [])
                keyword = ''.join([t.get('plain_text', '') for t in kw_prop])
        except Exception as e:
            _log.warning('[dispatch] gate1 Story Library lookup for %s: %s', task_id, e)

        # 2. If keyword still not resolved, search Trend Brain DB
        if not keyword:
            try:
                t_query = {
                    "filter": {
                        "or": [
                            {"property": "Task ID", "rich_text": {"equals": str(task_id)}},
                            {"property": "Keyword", "title": {"contains": str(task_id)}},
                        ]
                    },
                    "page_size": 1
                }
                tr = _hx.post(NOTION_API + '/databases/' + trend_db + '/query', headers=hdrs, json=t_query, timeout=10.0)
                trs = tr.json().get('results', [])
                if trs:
                    t_kw_prop = trs[0].get('properties', {}).get('Keyword', {}).get('title', [])
                    keyword = ''.join([t.get('plain_text', '') for t in t_kw_prop])
            except Exception as te:
                _log.warning('[dispatch] gate1 Trend Brain lookup for %s: %s', task_id, te)

    if approve:
        sl_ok = True
        if page_id:
            patch = {'properties': {'Status': {'status': {'name': 'Draft'}}}}
            r2 = _hx.patch(f"{NOTION_API}/pages/{page_id}", headers=hdrs, json=patch, timeout=10.0)
            sl_ok = r2.status_code in (200, 201)
        else:
            try:
                from app.services import episode_numbering as _epnum
                _epnum.commit_if_pending(task_id)
            except Exception:
                pass

        tb_ok = True
        if hdrs:
            try:
                t_filters = [{"property": "Task ID", "rich_text": {"equals": str(task_id)}}]
                if keyword:
                    t_filters.append({"property": "Keyword", "title": {"equals": keyword}})
                t_or = t_filters[0] if len(t_filters) == 1 else {"or": t_filters}
                t_q = _hx.post(f"{NOTION_API}/databases/{trend_db}/query", headers=hdrs, json={"filter": t_or, "page_size": 1}, timeout=10.0)
                t_results = t_q.json().get('results', [])
                if t_results:
                    t_page_id = t_results[0]['id']
                    # Try "" status property first, then fallback to Pipeline Status
                    tb_patch1 = {"properties": {"": {"status": {"name": "Approved→Story"}}}}
                    r_tb = _hx.patch(f"{NOTION_API}/pages/{t_page_id}", headers=hdrs, json=tb_patch1, timeout=10.0)
                    if r_tb.status_code not in (200, 201):
                        tb_patch2 = {"properties": {"Pipeline Status": {"status": {"name": "Approved→Story"}}}}
                        r_tb2 = _hx.patch(f"{NOTION_API}/pages/{t_page_id}", headers=hdrs, json=tb_patch2, timeout=10.0)
                        tb_ok = r_tb2.status_code in (200, 201)
                    else:
                        tb_ok = True
            except Exception as e:
                _log.warning('[dispatch] gate1 approve trend-brain update for %s: %s', task_id, e)

        ok = sl_ok and tb_ok
        spawn = _spawn_production(task_id)
        txt = (f'✅ Duyệt [{task_id}] => Notion OK, đang chạy B1.5→B3.5 ({spawn}).') if ok else (f'⚠️ Duyệt OK nhưng lỗi cập nhật Notion cho [{task_id}] ({spawn}).')
        return txt, not ok
    else:
        if page_id:
            patch = {'archived': True}
            _hx.patch(f"{NOTION_API}/pages/{page_id}", headers=hdrs, json=patch, timeout=10.0)

        if hdrs:
            try:
                t_filters = [{"property": "Task ID", "rich_text": {"equals": str(task_id)}}]
                if keyword:
                    t_filters.append({"property": "Keyword", "title": {"equals": keyword}})
                t_or = t_filters[0] if len(t_filters) == 1 else {"or": t_filters}
                t_q = _hx.post(f"{NOTION_API}/databases/{trend_db}/query", headers=hdrs, json={"filter": t_or, "page_size": 1}, timeout=10.0)
                t_results = t_q.json().get('results', [])
                if t_results:
                    t_page_id = t_results[0]['id']
                    tb_patch1 = {"properties": {"": {"status": {"name": "Rejected"}}}}
                    r_rej = _hx.patch(f"{NOTION_API}/pages/{t_page_id}", headers=hdrs, json=tb_patch1, timeout=10.0)
                    if r_rej.status_code not in (200, 201):
                        _hx.patch(f"{NOTION_API}/pages/{t_page_id}", headers=hdrs, json={"properties": {"Pipeline Status": {"status": {"name": "Rejected"}}}}, timeout=10.0)
            except Exception as e:
                _log.warning('[dispatch] gate1 reject trend-brain update for %s: %s', task_id, e)

        try:
            from app.services import episode_numbering as _epnum
            _epnum.remove_pending_task(task_id)
        except Exception:
            pass

        return f'❌ Đã từ chối [{task_id}] (Archived).', False


def dispatch(action, arg):
    """Route a button press. Returns (reply_text, show_alert). FAIL-SAFE."""
    a = (action or "").strip()
    arg = (arg or "").strip()
    if a == "imgdone":
        # HG2 acknowledged: images exist in Notion, release the HG1 lock so the
        # B4->B10 leg can be launched (or the market re-run) without a manual rm.
        import os
        try:
            os.unlink(os.path.join(VF_LOCK_DIR, "%s.lock" % arg))
        except FileNotFoundError:
            pass
        except Exception as e:
            _log.warning("[dispatch] imgdone unlock %s: %s", arg, e)
        return f"✅ Đã ghi nhận ảnh xong cho [{arg}]. Chạy B4→B10 để render.", False
    if a == "up":
        return _yt_upload_episode(arg)
    if a == "pub":
        ok, err = _yt_set_public(arg)
        if ok:
            try:
                from app.services import publish_ledger
                publish_ledger.mark_public(arg)
            except Exception:  # noqa: BLE001
                pass
        return ("🚀 Đã công khai video trên YouTube." if ok
                else "⚠️ Lỗi công khai: " + err), (not ok)
    if a == "kp":
        return "🔒 Giữ ở chế độ private.", False
    if a == "tg":
        try:
            from app.services import upload_mode
            new_mode = upload_mode.toggle_mode()
            if new_mode == "public":
                return ("🌐 Chế độ upload: PUBLIC — video mới sẽ đăng công khai.", False)
            return ("🕶️ Chế độ upload: ẨN DANH (unlisted) — video mới sẽ ẩn.", False)
        except Exception as e:  # noqa: BLE001
            return ("⚠️ Lỗi chuyển chế độ: " + str(e), True)
    if a == "puball":
        try:
            from app.services import publish_ledger
            pending = publish_ledger.load_pending()
        except Exception as e:  # noqa: BLE001
            return "⚠️ Lỗi tải danh sách video chờ public: " + str(e), True
        if not pending:
            return "✅ Không còn video nào đang chờ public.", False
        ok_count = 0
        fails = []
        for rec in pending:
            vid = rec.get("video_id")
            if not vid:
                continue
            ok, err = _yt_set_public(vid)
            if ok:
                ok_count += 1
                try:
                    publish_ledger.mark_public(vid)
                except Exception:  # noqa: BLE001
                    pass
            else:
                fails.append("%s: %s" % (vid, err))
        total = len(pending)
        if not fails:
            return "🚀 Đã công khai tất cả %d/%d video." % (ok_count, total), False
        msg = "⚠️ Công khai %d/%d video. Lỗi: %s" % (ok_count, total, "; ".join(fails[:3]))
        return msg, True
    # --- Gate 1: apr/rej handlers (callback from send_gate1_card) ---
    if a in ('apr', 'rej'):
        return _gate1_approve_or_reject(arg, approve=(a == 'apr'))
    if a in ('ap_all', 'rj_all'):
        try:
            from app.services import telegram_buttons
            pending = telegram_buttons.load_gate1_pending()
        except Exception as e:
            return '⚠️ Lỗi tải danh sách task Gate 1: ' + str(e), True
        tasks = [pending.get(m) for m in ('en', 'jp', 'kr') if pending.get(m)]
        if not tasks:
            return '⚠️ Không tìm thấy task Gate 1 đang chờ (chưa có card nào được gửi).', True
        approve = (a == 'ap_all')
        results = [_gate1_approve_or_reject(t, approve) for t in tasks]
        fails = [txt for txt, is_err in results if is_err]
        verb = 'duyệt' if approve else 'từ chối'
        if not fails:
            return f"✅ Đã {verb} tất cả {len(tasks)} kênh (EN/JP/KR).", False
        return f"⚠️ Đã {verb} {len(tasks) - len(fails)}/{len(tasks)} kênh. Lỗi: " + "; ".join(fails[:3]), True
    if a == "done":
        return "✨ Mục này đã được xử lý xong từ trước.", False
    return "❓ Hành động không xác định: " + a, True
