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
  python3 scripts/continue_after_images.py --episode-id <EPISODE_ID> \
      [--market <market>] [--privacy unlisted] [--skip-upload]

Writes /var/vf/episodes/<id>/b4b10_state.json after every stage transition so
the poller (and a human) can see exactly where the leg is.
"""
import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

logger = logging.getLogger('continue_after_images')

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
    logger.info(msg)


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
        asyncio.run(tg.notify_error(stage, episode_id, detail[:1500]))
    except Exception as exc:
        _log("telegram notify_error failed (%s: %s)" % (type(exc).__name__, exc))


def _run_stage(stage, argv, episode_id, timeout, notify_on_error=False):
    import signal
    _log("=== %s: %s" % (stage, " ".join(argv)))
    _write_state(episode_id, stage=stage, status="running")
    started = time.time()
    proc = None
    try:
        proc = subprocess.Popen(
            argv,
            cwd=REPO,
            start_new_session=True,
        )
        proc.wait(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(2)
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError as _kill_err:
                logger.warning("timeout killpg failed: %s", _kill_err)
        msg = "%s TIMEOUT after %ss" % (stage, timeout)
        _log("FAILED " + msg)
        _write_state(episode_id, stage=stage, status="failed", error=msg,
                     elapsed_sec=timeout)
        if notify_on_error:
            _notify_error(stage, episode_id, msg)
        else:
            _log("Suppressed Telegram intermediate notification for %s" % stage)
        return False
    except Exception as exc:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError as _kill_err:
                logger.warning("exception killpg failed: %s", _kill_err)
        msg = "%s crashed (%s: %s)" % (stage, type(exc).__name__, exc)
        _log("FAILED " + msg)
        _write_state(episode_id, stage=stage, status="failed", error=msg)
        if notify_on_error:
            _notify_error(stage, episode_id, msg)
        else:
            _log("Suppressed Telegram intermediate notification for %s" % stage)
        return False
    finally:
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except OSError as _kill_err:
                logger.warning("finally killpg failed: %s", _kill_err)

    elapsed = round(time.time() - started, 1)
    if rc != 0:
        msg = "%s exited %d after %ss" % (stage, rc, elapsed)
        _log("FAILED " + msg)
        _write_state(episode_id, stage=stage, status="failed", error=msg,
                     elapsed_sec=elapsed)
        if notify_on_error:
            _notify_error(stage, episode_id, msg)
        else:
            _log("Suppressed Telegram intermediate notification for %s" % stage)
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
    ap.add_argument("--render-timeout", type=int, default=54000)
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
    is_two_layer = arch in ("two_layer_v1", "remotion_twolayer_karaoke_v4") or "twolayer" in arch or arch.startswith("two_layer")
    if not is_two_layer:
        _log("AUTO-FIX: render_architecture was %r. Enforcing 'remotion_twolayer_karaoke_v4' for B4-B10 continuation." % arch)
        brain["render_architecture"] = "remotion_twolayer_karaoke_v4"
        brain_path.write_text(json.dumps(brain, ensure_ascii=False, indent=2), encoding="utf-8")
        is_two_layer = True

    # Calculate adaptive dynamic render timeout matching run_episode (Pillar 3 & Rule 134)
    props_path = ep_dir / "remotion_props.json"
    effective_render_timeout = args.render_timeout
    if props_path.exists():
        try:
            from app.services.render_timeout_policy import (
                compute_render_timeout_hierarchy,
                extract_frames_from_props,
            )
            calc_frames = extract_frames_from_props(props_path, default_frames=18000)
            h = compute_render_timeout_hierarchy(calc_frames, base_timeout=args.render_timeout)
            effective_render_timeout = int(h["continue_timeout"])
            _log("adaptive render timeout set to %ds for %d frames (hierarchy: rem=%ds, run=%ds, cont=%ds)" % (
                effective_render_timeout, calc_frames,
                int(h["remotion_timeout"]), int(h["run_episode_timeout"]), effective_render_timeout
            ))
        except Exception as _terr:
            _log("failed reading props for timeout: %s" % _terr)

    # Stage B6.1: Props Staging & Editorial Briefing (Vox Minimalist Pacing)
    brain_path = ep_dir / "brain_input.json"
    props_path = ep_dir / "remotion_props.json"
    segments_path = ep_dir / "whisper_segments.json"
    manifest_path = ep_dir / "images" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = ep_dir / "assets" / "manifest.json"

    if segments_path.exists() and manifest_path.exists():
        _run_stage("B6.1 Props Staging",
                   [sys.executable, "scripts/build_remotion_props.py",
                    "--episode-id", episode_id,
                    "--brain-input", str(brain_path),
                    "--segments", str(segments_path),
                    "--manifest", str(manifest_path),
                    "--out", str(props_path),
                    "--skip-missing"],
                   episode_id, 300,
                   notify_on_error=False)

        # Stage B6.2: Autonomous Adversarial Director Gate (Rule 122/128/136)
        if props_path.exists():
            _run_stage("B6.2 Adversarial Director Gate",
                       [sys.executable, "scripts/orchestrator/adversarial_director_gate.py",
                        "--episode-id", episode_id,
                        "--props", str(props_path),
                        "--no-stills"],
                       episode_id, 300,
                       notify_on_error=False)
    else:
        _log("B6.1 Props Staging skipped in continue_after_images: whisper_segments or manifest not ready yet, delegated to resume_episode.py S4.5")

    master = ep_dir / "final_169.mp4"
    s10_final = ep_dir / "10_render" / "final.mp4"
    if not master.exists() and s10_final.exists() and s10_final.stat().st_size > 10000000:
        _log("Found S10 rendered master video at %s (%.1f MB). Bridging to %s..." %
             (s10_final, s10_final.stat().st_size / 1048576.0, master))
        import shutil
        try:
            os.link(str(s10_final), str(master))
        except OSError:
            shutil.copy2(str(s10_final), str(master))

    # Rule 121 & 122: Temporal Motion Audit on existing master video
    is_master_dynamic = False
    if master.exists() and master.stat().st_size > 10000000:
        try:
            from stages.s08_video_gen import validate_video_motion_temporal_delta
            motion_score = validate_video_motion_temporal_delta(master)
            _log("Existing master video verified dynamic (motion delta = %.2f > 0.5)" % motion_score)
            is_master_dynamic = True
        except Exception as _m_err:
            _log("Existing master video at %s failed motion audit (%s). Purging static file to force fresh render." % (master, _m_err))
            try:
                master.unlink()
            except OSError as _unl_err:
                _log("Notice: failed to unlink invalid master video %s: %s" % (master, _unl_err))
            is_master_dynamic = False

    if is_master_dynamic:
        _log("Master video already rendered and verified dynamic at %s (%.1f MB). Skipping B4-B7 render." %
             (master, master.stat().st_size / 1048576.0))
        render_ok = True
    else:
        render_ok = _run_stage("B4-B7 render (resume_episode)",
                               [sys.executable, "scripts/resume_episode.py",
                                "--episode-id", episode_id],
                               episode_id, effective_render_timeout,
                               notify_on_error=False)

    master = ep_dir / "final_169.mp4"
    if not render_ok and not (master.exists() and master.stat().st_size > 0):
        # Check self-healing mux bridge before failing
        silent_video = ep_dir / "twolayer_silent.mp4"
        if not (silent_video.exists() and silent_video.stat().st_size > 10000000):
            msg = f"render stage failed and master video missing for {episode_id}"
            _log("FATAL " + msg)
            _write_state(episode_id, stage="render-verify", status="failed", error=msg)
            return 3

    if not master.exists() or master.stat().st_size == 0:
        # Self-Healing Mux Bridge: If twolayer_silent.mp4 exists, mux it immediately
        silent_video = ep_dir / "twolayer_silent.mp4"
        if silent_video.exists() and silent_video.stat().st_size > 10000000:
            _log("Self-Healing Mux Bridge: twolayer_silent.mp4 found (%.1f MB). Running mux_master_episode.py..."
                 % (silent_video.stat().st_size / 1048576.0))
            mux_ok = _run_stage("S7 Muxing (mux_master_episode)",
                                [sys.executable, "scripts/mux_master_episode.py",
                                 "--episode-id", episode_id],
                                episode_id, 300,
                                notify_on_error=False)
            if mux_ok and master.exists() and master.stat().st_size > 0:
                _log("Self-Healing Mux Bridge succeeded -> master video ready: %s" % master)

    if not master.exists() or master.stat().st_size == 0:
        msg = "render failed and master %s is missing/empty after self-healing" % master
        _log("FATAL " + msg)
        _write_state(episode_id, stage="render-verify", status="failed", error=msg)
        _log("Suppressed Telegram error alert for render-verify; LLM orchestrator handles VPS auto-debugging")
        return 3
    _log("master present: %s (%.1f MB)" % (master, master.stat().st_size / 1048576.0))

    # Stage B9: Post-Render Autonomous Technical Sweep (LUFS & Rule 135 exact chapters)
    # Non-fatal audit stage: intermediate error suppressed, details logged to report
    _run_stage("B9 Post-Render Technical Sweep",
               [sys.executable, "-m", "app.services.post_render_technical_sweep",
                "--episode-id", episode_id,
                "--episode-dir", str(ep_dir)],
               episode_id, 300,
               notify_on_error=False)

    if args.skip_upload:
        _log("--skip-upload set; stopping before B10/HG3")
        _write_state(episode_id, stage="done-render-only", status="ok")
        return 0

    if not _run_stage("B10 upload + HG3",
                      [sys.executable, "scripts/execute_b10_auto_seo_upload_gate2.py",
                       "--episode", episode_id,
                       "--market", args.market,
                       "--privacy", args.privacy,
                       "--force-reupload"],
                      episode_id, args.upload_timeout,
                      notify_on_error=False):
        return 4

    _write_state(episode_id, stage="done", status="ok")
    _log("B4->B10 complete; Human Gate 3 card dispatched")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [CONTINUE_AFTER_IMAGES] %(message)s")
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired as exc:
        _log("TIMEOUT %s" % exc)
        sys.exit(5)
    except Exception:
        _log("CRASH\n" + traceback.format_exc())
        sys.exit(9)
