#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B4 -> B10 continuation leg: render + upload an episode whose Notion Image
Asset Library rows are complete (all Background/Foreground reuse keys at
Approved / Pulled by VPS).

Wired against the ONLY live golive path (traced and verified 29/08/2026):

  1. scripts/resume_episode.py --episode-id <id>
       -> app.pipeline.run_episode.run_pipeline()
       -> S4 TTS
       -> S4.5 two_layer_v1 gate (brain_input.json render_architecture)
            pull_approved_images.py -> build_remotion_props.py
            -> render_twolayer_visual.py
       -> S4.6 coverage fail-fast (video/audio ratio >= VF_MIN_VIDEO_COVERAGE)
       -> S6 subtitles -> S7 master render (final_169.mp4)

  2. scripts/execute_b10_auto_seo_upload_gate2.py --episode <id>
       -> auto SEO packaging (Rule 119), Notion Story Library + YouTube
          Registry sync, B9 quality probe (hard gate), YouTube upload,
          publish ledger, then the Human Gate 3 Telegram card.

Deliberately does NOT touch scripts/render_and_finalize_episode.py (imports a
module that does not exist, zero referrers), nor
scripts/render_remotion_two_layer_master.py / scripts/execute_b10_master.py
(both hardcoded to one specific past episode). Those are dead/legacy.

Usage:
  python3 scripts/continue_after_images.py --episode-id en_test_hg1_v2 \
      [--market en] [--privacy unlisted] [--skip-upload]

Writes /var/vf/episodes/<id>/b4b10_state.json after every stage transition so
the poller (and a human) can see exactly where the leg is.
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO = "/root/video_factory"
EPISODES = Path("/var/vf/episodes")
sys.path.insert(0, REPO)


def _load_env():
    """Cron/pm2 shells do not always carry NOTION_TOKEN etc. Fill the gaps from
    /etc/environment, then /root/secrets/.env, without clobbering real values."""
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


def _state_path(episode_id):
    return EPISODES / episode_id / "b4b10_state.json"


def _write_state(episode_id, **fields):
    path = _state_path(episode_id)
    state = {}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    state.update(fields)
    state["episode_id"] = episode_id
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def _notify_error(stage, episode_id, detail):
    try:
        from app.services import telegram_notify as tg
        asyncio.run(tg.notify_error("B4->B10 %s" % stage, episode_id, detail[:1500]))
    except Exception as exc:
        _log("telegram notify_error failed (%s: %s)" % (type(exc).__name__, exc))


def _run_stage(stage, argv, episode_id, timeout):
    _log("=== %s: %s" % (stage, " ".join(argv)))
    _write_state(episode_id, stage=stage, status="running")
    started = time.time()
    proc = subprocess.run(argv, cwd=REPO, timeout=timeout)
    elapsed = round(time.time() - started, 1)
    if proc.returncode != 0:
        msg = "%s exited %d after %ss" % (stage, proc.returncode, elapsed)
        _log("FAILED " + msg)
        _write_state(episode_id, stage=stage, status="failed", error=msg,
                     elapsed_sec=elapsed)
        _notify_error(stage, episode_id, msg)
        return False
    _log("OK %s in %ss" % (stage, elapsed))
    _write_state(episode_id, stage=stage, status="ok", elapsed_sec=elapsed)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--market", default="en")
    ap.add_argument("--privacy", default="unlisted")
    ap.add_argument("--skip-upload", action="store_true",
                    help="render only; stop before B10/HG3 (dry run)")
    ap.add_argument("--render-timeout", type=int, default=7200)
    ap.add_argument("--upload-timeout", type=int, default=3600)
    args = ap.parse_args()

    _load_env()
    episode_id = args.episode_id
    ep_dir = EPISODES / episode_id
    brain_path = ep_dir / "brain_input.json"
    if not brain_path.exists():
        _log("ERROR no brain_input.json at %s" % brain_path)
        return 1

    try:
        brain = json.loads(brain_path.read_text(encoding="utf-8"))
    except Exception as exc:
        _log("ERROR unreadable brain_input.json: %s" % exc)
        return 1

    arch = str(brain.get("render_architecture") or "").strip()
    if arch != "two_layer_v1":
        # Not fatal for the pipeline, but it means S4.5 will be skipped and the
        # legacy S5 stock-clip path runs instead -- almost certainly not what
        # the Antigravity image flow intended. Say so loudly.
        _log("WARNING render_architecture=%r (not two_layer_v1): S4.5 two-layer "
             "path will be SKIPPED and legacy S5 will run instead" % arch)

    _write_state(episode_id, stage="start", status="running",
                 market=args.market, privacy=args.privacy,
                 skip_upload=bool(args.skip_upload))

    if not _run_stage("B4-B7 render (resume_episode)",
                      [sys.executable, "scripts/resume_episode.py",
                       "--episode-id", episode_id],
                      episode_id, args.render_timeout):
        return 2

    master = ep_dir / "final_169.mp4"
    if not master.exists() or master.stat().st_size == 0:
        msg = "render reported success but %s is missing/empty" % master
        _log("FAILED " + msg)
        _write_state(episode_id, stage="render-verify", status="failed", error=msg)
        _notify_error("render-verify", episode_id, msg)
        return 3
    _log("master present: %s (%.1f MB)" % (master, master.stat().st_size / 1048576.0))

    if args.skip_upload:
        _log("--skip-upload set; stopping before B10/HG3")
        _write_state(episode_id, stage="done-render-only", status="ok")
        return 0

    if not _run_stage("B10 upload + HG3",
                      [sys.executable, "scripts/execute_b10_auto_seo_upload_gate2.py",
                       "--episode", episode_id,
                       "--market", args.market,
                       "--privacy", args.privacy],
                      episode_id, args.upload_timeout):
        return 4

    _write_state(episode_id, stage="done", status="ok")
    _log("B4->B10 complete; Human Gate 3 card dispatched")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired as exc:
        _log("TIMEOUT %s" % exc)
        sys.exit(5)
    except Exception:
        _log("CRASH\n" + traceback.format_exc())
        sys.exit(9)
