import os
"""MPT-G4-1 - Video render: concat clips + mux audio + BGM mix. SEG_MAX_SEC=300.

Spec-enhance v2 (29/06):
  - stream_loop=-1 fills video to audio duration (fixes duration_drift).
  - Editorial doc color grade: eq + colorbalance + grain + vignette (VF_GRADE=1).
  - Subtitle lower-third: 18pt bold white, MarginV=200 (~10% from bottom).

Hotfix v3 (04/07): _concat_clips rewritten to rolling pairwise xfade instead of a
single N-input filter_complex. Root cause of Lehman pilot S7 crash: an 81-input
(intro+79 scenes+outro) xfade/concat filter graph opened all decoders at once and
was OOM-killed by the kernel (confirmed via dmesg oom-killer log, ffmpeg pid killed
at ~4.1GB anon-rss on an 8GB VPS). Rolling pairwise concat bounds memory to ~2
decoders at a time regardless of clip count.
"""
import asyncio, logging, os, shutil, tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SEG_MAX_SEC = 3600  # FIX 06/08/2026: two-layer architecture renders ONE clip
# spanning the WHOLE episode (was previously many short B-roll clips), so the
# old 300s cap silently truncated the single long clip during _scale_clip,
# causing [S7-coverage] failures (EP005: 653s narration -> 300s video track).
# Raised to 3600s (60min) as a generous safety cap that still guards against a
# truly corrupt/runaway duration probe, without truncating real episodes.
DEFAULT_ASPECT = os.getenv("VF_IMAGE_ASPECT", "16:9")
ASPECT_SIZES = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1":  (1080, 1080),
}
XFADE_DURATION = 0.5

# Editorial documentary grade (toggleable via VF_GRADE=0 env).
_GRADE_VF = (
    "eq=contrast=1.08:saturation=0.86:gamma=0.98,"
    "colorbalance=bs=0.06:rm=0.04:gm=-0.02,"
    "noise=alls=7:allf=t,"
    "vignette=PI/8"  # FIX 28/07/2026: PI/5 vignette darkened corner-safe-zone Remotion stat cards to near-invisibility (measured bright-pixel frac 0.19->0.01); PI/8 keeps documentary look while keeping cards legible (0.19->0.09, max 255->248)
)

# Subtitle: bold white, lower-third (MarginV 200px ~10% from bottom on 9:16).
_SUB_STYLE = (
    "Fontname=DejaVu Sans,Fontsize=18,Bold=1,PrimaryColour=&H00FFFFFF&,"
    "OutlineColour=&H90000000&,BorderStyle=3,Outline=2,Shadow=0,"
    "Alignment=2,MarginV=30"
)


def _grade_enabled() -> bool:
    return os.environ.get("VF_GRADE", "1") not in ("0", "false", "False", "")


# ---------------------------------------------------------------------------
# Checkpointing (Hotfix v6, 05/07): persist progress to a STABLE per-episode
# dir (not the random tempfile.mkdtemp() dir, which is destroyed on every
# process restart) so a crash/retry resumes from the last verified-good
# artifact instead of redoing the whole multi-hour pipeline from clip 0.
# Root motivation: 2 back-to-back full-pipeline redos today were wasted
# solely because of a bug in the LAST-second mux step, after concat+grade had
# already fully succeeded.
#
# Invariant: at most ONE "current" file exists on disk per stage at a time
# (atomic write-then-os.replace swap), and it is only ever published once
# ffmpeg has returned success AND passed frame-validation - so the file on
# disk is always either "not there yet" or "a fully valid checkpoint",
# never a partial/corrupt one.
# ---------------------------------------------------------------------------
import hashlib
import json

CKPT_ROOT = "/var/vf/episodes"


def _ckpt_dir(episode_id: str, aspect: str) -> str:
    d = f"{CKPT_ROOT}/{episode_id}/s7_checkpoint/{aspect.replace(':', '')}"
    os.makedirs(d, exist_ok=True)
    return d


def _clips_signature(clips: list, aspect: str) -> str:
    """Fingerprint of (clip paths + mtimes + aspect) so a checkpoint from a
    stale/different clip set can never be mistakenly resumed into."""
    h = hashlib.sha256()
    h.update(aspect.encode())
    for c in clips:
        h.update(str(c).encode())
        try:
            h.update(str(os.path.getmtime(c)).encode())
        except OSError:
            pass
    return h.hexdigest()[:20]


def _load_manifest(ckpt_dir: str):
    p = f"{ckpt_dir}/manifest.json"
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return None


def _save_manifest(ckpt_dir: str, data: dict) -> None:
    p = f"{ckpt_dir}/manifest.json"
    tmp = f"{p}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, p)


def _atomic_publish(src_path: str, final_path: str) -> None:
    """Publish src_path as final_path such that final_path either doesn't
    exist yet, or is always a complete file - never a half-written one."""
    os.replace(src_path, final_path)


def _aspect_to_size(aspect: str):
    return ASPECT_SIZES.get(aspect, ASPECT_SIZES["9:16"])


async def _validate_clip(path: str) -> bool:
    # Frame-validation: True if clip has >=1 decodable video packet.
    if not Path(path).exists():
        return False
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-count_packets", "-show_entries", "stream=nb_read_packets",
        "-of", "csv=p=0", path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            return False
        # FIX 29/07/2026: ffprobe tra "150," (co dau phay) cho mp4 mang ICC
        # Profile side data - dung chinh la cac clip Remotion. "150,".isdigit()
        # = False nen 12 clip the bi loai am tham khoi ban ghep. Lay cot dau
        # tien va bo moi ky tu khong phai so.
        raw = out.decode().strip()
        nn = raw.splitlines()[0].split(",")[0].strip() if raw else ""
        return nn.isdigit() and int(nn) > 0
    except Exception:
        return False


def _srt_ts(ms):
    h, r = divmod(int(ms), 3600000)
    m, r = divmod(r, 60000)
    s2, ms2 = divmod(r, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s2, ms2)


def _write_srt(segments, path):
    # Mirror S6 schema: start_ms/end_ms or start/end seconds + text.
    n = 0
    with open(path, "w") as fout:
        for i, seg in enumerate(segments or [], 1):
            text = (seg.get("text", "") or "").strip()
            if not text:
                continue
            s_ms = int(seg.get("start_ms", seg.get("start", 0) * 1000))
            e_ms = int(seg.get("end_ms", seg.get("end", 0) * 1000))
            fout.write("%d\n%s --> %s\n%s\n\n" % (i, _srt_ts(s_ms), _srt_ts(e_ms), text))
            n += 1
    return n


async def _probe_wh(path: str):
    """Return (width, height) of the first video stream, or (None, None)."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height", "-of", "csv=p=0", path]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        parts = out.decode().strip().split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return None, None


def _aspect_gate_mode() -> str:
    """off | warn (default) | block - VF_ASPECT_GATE."""
    return (os.environ.get("VF_ASPECT_GATE") or "warn").strip().lower()


async def _scale_clip(src: str, dst: str, w: int, h: int, max_sec: int = SEG_MAX_SEC,
                       max_attempts: int = 3):
    """Scale+pad one clip. Auto-retries a transient ffmpeg failure (Hotfix v6,
    05/07 "tu dong fix loi" requirement) before giving up on this clip."""
    # GATE 27/07/2026: a clip whose own ratio differs from the target gets
    # pillar/letterboxed by the pad below. black_ratio cannot detect that, so
    # catch it here, at the only place that knows both ratios.
    if _aspect_gate_mode() != "off":
        sw, sh = await _probe_wh(src)
        if sw and sh and w and h:
            src_r, dst_r = float(sw) / float(sh), float(w) / float(h)
            if abs(src_r - dst_r) / dst_r > 0.04:
                msg = ("[S7-aspect] %s is %dx%d (%.3f) but target is %dx%d (%.3f)"
                       " -> clip would be pillar/letterboxed"
                       % (os.path.basename(src), sw, sh, src_r, w, h, dst_r))
                if _aspect_gate_mode() == "block":
                    raise RuntimeError(msg)
                logger.warning(msg)
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
               f"pad={w}:{h}:-1:-1:color=black,setsar=1,format=yuv420p,fps=30",
        "-c:v", "libx264", "-preset", "fast", "-an",
        "-t", str(max_sec), dst
    ]
    last_err = ""
    for attempt in range(1, max_attempts + 1):
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and await _validate_clip(dst):
            return
        last_err = stderr.decode(errors="ignore")[-200:]
        if attempt < max_attempts:
            await asyncio.sleep(2.0)
    raise RuntimeError(f"scale failed after {max_attempts} attempts: {last_err}")


async def _probe_duration(path: str) -> float:
    """Return clip duration in seconds (ffprobe); 5.0 on failure."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", path]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        return float(out.decode().strip())
    except Exception:
        return 5.0


async def _probe_duration_or_none(path: str):
    """Like _probe_duration but returns None (never a numeric fallback) on
    failure.

    Hotfix v5 (05/07 17:16 postmortem): the final mux safety-check used to
    call _probe_duration, whose 5.0-on-failure fallback made a transient
    ffprobe glitch look like "video is only 5s long", wrongly re-arming
    "-stream_loop -1" and producing a runaway (~12h / 49GB) mux that then
    failed. This probe is used ONLY at that mux safety-check so a probe
    failure is treated as "unknown" (safe) instead of "short" (dangerous).
    _probe_duration itself is left unchanged since it is also used by the
    working pairwise-xfade concat step, where a None would break arithmetic.
    """
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", path]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        return float(out.decode().strip())
    except Exception:
        return None


async def _xfade_pair(a: str, b: str, out_path: str, xf: float, trans: str, dur_a: float):
    """Crossfade exactly two inputs (bounded memory: 2 decoders)."""
    offset = max(0.0, dur_a - xf)
    fc = (
        f"[0:v]setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];"
        f"[v0][v1]xfade=transition={trans}:duration={xf:.3f}:offset={offset:.3f}[vout]"
    )
    cmd = [
        "ffmpeg", "-y", "-i", a, "-i", b,
        "-filter_complex", fc, "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", out_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    return proc.returncode == 0, stderr.decode(errors="ignore")[-300:]


async def _hardcut_pair(a: str, b: str, out_path: str):
    """Hard-cut concat exactly two inputs (fallback if xfade pair fails)."""
    fc = "[0:v]setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];[v0][v1]concat=n=2:v=1:a=0[vout]"
    cmd = [
        "ffmpeg", "-y", "-i", a, "-i", b,
        "-filter_complex", fc, "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", out_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    return proc.returncode == 0, stderr.decode(errors="ignore")[-300:]


async def _retry_pair_fn(fn, *args, attempts: int = 2):
    """Auto-retry an (ok, err)-returning pair-merge function before the
    caller falls back further (Hotfix v6, 05/07 auto-fix requirement)."""
    ok, err = False, ""
    for _ in range(attempts):
        ok, err = await fn(*args)
        if ok:
            return ok, err
    return ok, err


async def _concat_clips(clips: list, output_path: str, aspect: str,
                         episode_id=None) -> str:
    """Scale and concat clips using rolling pairwise FFmpeg xfade (bounded memory).

    Hotfix v3: previously built ONE filter_complex with all N clips as -i inputs
    simultaneously (N=81 for the Lehman pilot: intro + 79 scenes + outro). That
    opened 81 decoders in a single ffmpeg process and was OOM-killed on the VPS
    (confirmed via dmesg). Now each clip is folded into a running accumulator one
    at a time (2 decoders per step), so memory use no longer scales with clip count.

    Hotfix v6 (05/07): checkpointed + resumable. Previously ANY failure
    downstream (even the final mux, after this whole step already succeeded)
    forced a full redo of this multi-hour step from clip 0, because progress
    only lived in a random tempfile.mkdtemp() dir that dies with the process.
    When episode_id is given, per-clip scaled outputs and the rolling
    accumulator are persisted to a stable per-episode checkpoint dir and a
    manifest tracks progress, so a retry resumes from the last verified step.
    Only one accumulator file ever exists on disk at a time (atomic
    write-then-replace) and it is always a ffmpeg-succeeded, frame-validated
    file - never a partial one.
    """
    if not clips:
        raise ValueError("[video_render] No clips provided")

    use_ckpt = bool(episode_id)
    ckpt_dir = _ckpt_dir(episode_id, aspect) if use_ckpt else None
    sig = _clips_signature(clips, aspect) if use_ckpt else None
    concat_done_path = f"{ckpt_dir}/concat_done.mp4" if use_ckpt else None

    # Fast path: this exact clip set + aspect was already fully concatenated
    # in a previous attempt - skip everything below entirely.
    if use_ckpt:
        manifest = _load_manifest(ckpt_dir)
        if (manifest and manifest.get("sig") == sig
                and manifest.get("stage") == "concat_done"
                and os.path.exists(concat_done_path)
                and await _validate_clip(concat_done_path)):
            shutil.copy(concat_done_path, output_path)
            return output_path

    # Per-clip frame-validation: drop clips with no decodable video packets.
    validated, dropped = [], []
    for _c in clips:
        if await _validate_clip(_c):
            validated.append(_c)
        else:
            dropped.append(_c)
    if not validated:
        raise ValueError("[video_render] No valid clips after frame-validation")
    # GATE 29/07/2026: truoc day clip bi loai o day mat hoan toan im lang, nen
    # 12 clip Remotion bien khoi video cuoi ma khong ai biet. Gio phai bao to.
    if dropped:
        _msg = ("[video_render] frame-validation LOAI %d/%d clip: %s"
                % (len(dropped), len(validated) + len(dropped),
                   ", ".join(os.path.basename(str(d)) for d in dropped[:8])))
        logger.warning(_msg)
        if os.getenv("VF_BLOCK_ON_CLIP_DROP", "1").strip() == "1":
            raise RuntimeError(_msg + " (dat VF_BLOCK_ON_CLIP_DROP=0 de bo qua)")
    clips = validated
    w, h = _aspect_to_size(aspect)
    tmp_dir = tempfile.mkdtemp(prefix="vf_render_")
    try:
        scale_dir = ckpt_dir if use_ckpt else tmp_dir
        scaled = []
        for i, clip in enumerate(clips):
            # FIX 28/07/2026: key the cached scaled file by clip content, not
            # just array index, so a stale scaled file from a differently-
            # sourced earlier attempt (e.g. Ken-Burns fallback before a
            # Remotion card render worked) is never silently reused for the
            # same index - it would otherwise drop the card with no error.
            try:
                _mt = os.path.getmtime(clip)
            except OSError:
                _mt = 0
            _csig = hashlib.sha256((str(clip) + "|" + str(_mt)).encode()).hexdigest()[:10]
            sp = f"{scale_dir}/scaled_{i:03d}_{_csig}.mp4"
            if use_ckpt and os.path.exists(sp) and await _validate_clip(sp):
                pass  # already scaled in a previous attempt - reuse, skip re-encode
            else:
                sw, sh = await _probe_wh(clip)
                if sw == w and sh == h:
                    shutil.copy(clip, sp)
                else:
                    await _scale_clip(clip, sp, w, h)
            scaled.append(sp)

        if len(scaled) == 1:
            shutil.copy(scaled[0], output_path)
            if use_ckpt:
                shutil.copy(scaled[0], concat_done_path)
                _save_manifest(ckpt_dir, {"sig": sig, "stage": "concat_done"})
            return output_path

        n = len(scaled)
        transitions = ["fade", "dissolve", "slideleft", "wipeleft",
                       "circleopen", "smoothleft", "fadeblack", "slideup"]

        acc_ckpt_path = f"{ckpt_dir}/acc_current.mp4" if use_ckpt else None
        start_i = 1
        acc = scaled[0]
        acc_dur = await _probe_duration(acc)
        acc_is_temp = False

        if use_ckpt:
            manifest = _load_manifest(ckpt_dir)
            if (manifest and manifest.get("sig") == sig
                    and manifest.get("stage") == "concat"
                    and isinstance(manifest.get("next_index"), int)
                    and 1 <= manifest["next_index"] <= n
                    and os.path.exists(acc_ckpt_path)
                    and await _validate_clip(acc_ckpt_path)):
                start_i = manifest["next_index"]
                acc = acc_ckpt_path
                acc_dur = await _probe_duration(acc)  # always re-probe, never trust a cached number blindly
                acc_is_temp = False
            else:
                _save_manifest(ckpt_dir, {"sig": sig, "stage": "concat", "next_index": 1})

        for i in range(start_i, n):
            nxt = scaled[i]
            nxt_dur = await _probe_duration(nxt)
            xf = XFADE_DURATION
            if min(acc_dur, nxt_dur) <= xf:
                xf = max(0.1, min(acc_dur, nxt_dur) / 2.0)
            trans = transitions[(i - 1) % len(transitions)]
            step_out = f"{tmp_dir}/acc_{i:03d}.mp4"

            ok, err = await _retry_pair_fn(_xfade_pair, acc, nxt, step_out, xf, trans, acc_dur)
            new_dur = acc_dur + nxt_dur - xf
            if not ok:
                ok2, err2 = await _retry_pair_fn(_hardcut_pair, acc, nxt, step_out)
                if not ok2:
                    raise RuntimeError(
                        f"concat step {i}/{n - 1} failed: {err} | fallback: {err2}"
                    )
                new_dur = acc_dur + nxt_dur

            if not await _validate_clip(step_out):
                raise RuntimeError(f"concat step {i}/{n - 1} produced an invalid file")

            if use_ckpt:
                # Publish atomically, THEN advance the manifest - at any
                # instant exactly one valid accumulator exists on disk, and
                # it is always the most-advanced verified checkpoint.
                _atomic_publish(step_out, acc_ckpt_path)
                _save_manifest(ckpt_dir, {"sig": sig, "stage": "concat", "next_index": i + 1})
                acc = acc_ckpt_path
                acc_is_temp = False
            else:
                if acc_is_temp:
                    try:
                        os.remove(acc)
                    except OSError:
                        pass
                acc = step_out
                acc_is_temp = True
            acc_dur = new_dur

        shutil.copy(acc, output_path)
        if use_ckpt:
            shutil.copy(acc, concat_done_path)
            _save_manifest(ckpt_dir, {"sig": sig, "stage": "concat_done"})
        return output_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def render_video(
    clips: list,
    audio_path: str,
    output_path: str,
    aspect: str = DEFAULT_ASPECT,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.063,
    subtitle_segments: Optional[list] = None,
    lang_code: str = "en",
    episode_id=None,
    is_two_layer: bool = False,
) -> str:
    """Full render: concat clips -> grade -> mux TTS (stream_loop fills audio) -> BGM.

    Key fix: -stream_loop -1 on the video input means the clip track loops
    indefinitely; -shortest then stops at the end of the audio track.
    This eliminates duration_drift when the total clip duration < audio duration.

    Hotfix v6 (05/07): episode_id checkpoints/resumes the concat step (see
    _concat_clips) and caches the graded output, so a mux-stage failure only
    re-runs the mux, not the whole concat+grade pipeline.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="vf_final_")
    use_ckpt = bool(episode_id)
    ckpt_dir = _ckpt_dir(episode_id, aspect) if use_ckpt else None
    try:
        video_only = f"{tmp_dir}/video_only.mp4"
        await _concat_clips_batched(clips, video_only, aspect, episode_id=episode_id)

        # -- Editorial documentary grade (VF_GRADE=1 by default) ---------------
        graded_ckpt_path = f"{ckpt_dir}/graded_done.mp4" if use_ckpt else None
        if not is_two_layer and _grade_enabled():
            if (use_ckpt and os.path.exists(graded_ckpt_path)
                    and await _validate_clip(graded_ckpt_path)):
                video_only = graded_ckpt_path  # reuse cached grade, skip re-grading
            else:
                graded = f"{tmp_dir}/video_graded.mp4"
                g_cmd = [
                    "ffmpeg", "-y", "-i", video_only,
                    "-vf", _GRADE_VF,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-an", graded,
                ]
                grade_ok = False
                for _attempt in range(2):  # auto-retry a transient grade failure
                    gp = await asyncio.create_subprocess_exec(
                        *g_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    _, gerr = await gp.communicate()
                    if gp.returncode == 0 and await _validate_clip(graded):
                        grade_ok = True
                        break
                if grade_ok:
                    video_only = graded  # grade succeeded -> use graded for mux
                    if use_ckpt:
                        shutil.copy(graded, graded_ckpt_path)
                # grade failure is non-fatal: fall through with ungraded video

        burn_subs = bool(subtitle_segments)
        mux_target = f"{tmp_dir}/muxed.mp4" if burn_subs else output_path

        # Hotfix v4 (05/07): unconditional -stream_loop -1 + "-c:v copy" + "-shortest"
        # caused a runaway mux (video looped near-forever; ffmpeg reported
        # time=12:05:09 / 49GB before "mux failed") when video_only was already >=
        # audio duration (the normal case). Only loop when video is truly shorter.
        #
        # Hotfix v5 (05/07 17:16 postmortem): v4 recurred with an identical
        # symptom (time=12:07:12 / 49GB) because _probe_duration's 5.0-on-failure
        # fallback made a transient ffprobe glitch look like "video is only 5s",
        # wrongly re-arming the infinite loop. Fix, defense-in-depth:
        #   1) use _probe_duration_or_none here (None, not 5.0, on failure) so a
        #      probe glitch can never again look like "video is short";
        #   2) loop_args only arms when BOTH durations are known and video is
        #      genuinely shorter than audio;
        #   3) a hard "-t <cap>" duration cap is always applied to the mux
        #      itself, independent of -shortest/loop_args, so no future edge
        #      case can ever again produce a multi-hour/multi-GB runaway file.
        video_dur = await _probe_duration_or_none(video_only)
        audio_dur = await _probe_duration_or_none(audio_path)
        if video_dur is None and audio_dur is None:
            raise RuntimeError(
                "mux aborted: could not probe duration of video_only or "
                "audio_path (both ffprobe calls failed) - refusing to mux "
                "blind to avoid a repeat of the 05/07 runaway-loop mux failure"
            )
        # FIX 29/07/2026: video coverage gate. Root cause of EP004
        # 'same image at scattered positions': the concatenated video
        # was only ~312s while the narration was ~432s, so the
        # -stream_loop below silently REPLAYED the first ~120s at the
        # end. Never ship that silently again.
        if (video_dur is not None and audio_dur is not None
                and audio_dur > 0):
            _cov = float(video_dur) / float(audio_dur)
            _min_cov = float(os.getenv('VF_MIN_VIDEO_COVERAGE', '0.97'))
            if _cov < _min_cov:
                _msg = ('[S7-coverage] video track %.1fs covers only '
                        '%.1f%% of the %.1fs narration; looping would '
                        'replay %.1fs of earlier footage'
                        % (video_dur, _cov * 100.0, audio_dur,
                           audio_dur - video_dur))
                logger.error(_msg)
                if os.getenv('VF_BLOCK_SHORT_VIDEO', '1') not in ('0', 'false', ''):
                    raise RuntimeError(_msg)
        loop_args = (
            ["-stream_loop", "-1"]
            if (video_dur is not None and audio_dur is not None and video_dur < audio_dur - 0.5)
            else []
        )
        cap_dur = audio_dur if audio_dur is not None else video_dur
        cap_args = ["-t", f"{cap_dur + 0.5:.3f}"]
        if bgm_path and Path(bgm_path).exists():
            # Intelligent Sidechain Ducking + Vocal Clarity EQ (Rule 125 & R3)
            # Replaces legacy aloop with sidechaincompress:
            # - When TTS speaks: BGM ducks smoothly to -18dB..-20dB and dips 2.5kHz vocal zone (-4dB)
            # - When TTS pauses: BGM swells to cinematic level without drowning speech
            # - Eliminates muddy sub-bass hum/drone ("tiếng ù ù")
            bgm_dur = await _probe_duration_or_none(bgm_path)
            bgm_loop = (
                ["-stream_loop", "-1"]
                if (bgm_dur is not None and audio_dur is not None and bgm_dur < audio_dur - 1.0)
                else []
            )
            # Intelligent Sidechain Ducking + Broadcast Vocal Pocket EQ (Rule 125 & R3)
            # - BGM baseline at volume=0.09 (-22dB..-24dB documentary standard)
            # - High-pass filter at 85Hz eliminates muddy sub-bass hum/drone
            # - Vocal pocket EQ dips 2.5kHz presence zone (-5dB) to clear room for speech
            # - Sidechain compressor ducks BGM cleanly without makeup gain boost
            af = (
                "[1:a]volume=1.0,asplit=2[tts_clean][tts_sc];"
                "[2:a]volume=0.09,highpass=f=85,equalizer=f=2500:t=q:w=1.5:g=-5[bgm_eq];"
                "[bgm_eq][tts_sc]sidechaincompress=threshold=0.02:ratio=10:attack=80:release=350[bgm_ducked];"
                "[tts_clean][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,alimiter=limit=0.95:attack=5:release=50[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                *loop_args, "-i", video_only,
                "-i", audio_path,
                *bgm_loop, "-i", bgm_path,
                "-filter_complex", af,
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", *cap_args, mux_target
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                *loop_args, "-i", video_only,
                "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", *cap_args, mux_target
            ]
        mux_ok = False
        mux_err = ""
        for _attempt in range(2):  # auto-retry a transient mux failure
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0:
                mux_ok = True
                break
            mux_err = stderr.decode()[-200:]
        if not mux_ok:
            raise RuntimeError(f"mux failed: {mux_err}")

        def _cleanup_ckpt():
            # Full render succeeded end-to-end: the checkpoint cache for this
            # episode+aspect is no longer needed. Only called on SUCCESS -
            # on any failure above we deliberately keep it for the next retry.
            if use_ckpt:
                shutil.rmtree(ckpt_dir, ignore_errors=True)

        if not burn_subs:
            _cleanup_ckpt()
            return output_path

        srt_path = f"{tmp_dir}/subs.srt"
        cue_count = _write_srt(subtitle_segments, srt_path)
        if cue_count == 0:
            shutil.copy(mux_target, output_path)
            _cleanup_ckpt()
            return output_path

        burn_cmd = [
            "ffmpeg", "-y",
            "-i", mux_target,
            "-vf", f"subtitles=subs.srt:force_style='{_SUB_STYLE}'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path,
        ]
        bproc = await asyncio.create_subprocess_exec(
            *burn_cmd, cwd=tmp_dir,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, berr = await bproc.communicate()
        if bproc.returncode != 0:
            raise RuntimeError(f"subtitle burn failed: {berr.decode()[-200:]}")
        _cleanup_ckpt()
        return output_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ===================== Hotfix v7 (speedup) =====================
# 1) _concat_clips_batched: batched 2-level xfade instead of the O(N^2) rolling
#    fold, so a clip no longer re-encodes the whole growing video every step.
# 2) derive_aspect_blurpad: build 9:16 & 1:1 from the finished 16:9 master with
#    a blurred-background fill, so concat+grade runs ONCE instead of 3x.
async def _ff_run_v7(cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    return proc.returncode, err.decode(errors="ignore")[-600:]


async def _xfade_chain_v7(inputs, output_path, transitions, xf=0.5):
    """xfade-concat pre-scaled clips in ONE ffmpeg filter_complex.

    All inputs share WxH/fps (pre-scaled). Memory is bounded by len(inputs)
    simultaneous decoders, so callers keep batches small.
    """
    if len(inputs) == 1:
        shutil.copy(inputs[0], output_path)
        return output_path
    durs = []
    for p in inputs:
        d = await _probe_duration(p)
        if not d or d <= 0:
            raise RuntimeError("[video_render] bad duration for %s" % p)
        durs.append(d)
    cmd = ["ffmpeg", "-y", "-nostdin"]
    for p in inputs:
        cmd += ["-i", p]
    parts = ["[%d:v]setpts=PTS-STARTPTS[v%d]" % (i, i) for i in range(len(inputs))]
    prev = "v0"
    cum = durs[0]
    for i in range(1, len(inputs)):
        tr = transitions[(i - 1) % len(transitions)]
        offset = cum - xf
        if offset < 0:
            offset = 0.0
        out_lbl = "vout" if i == len(inputs) - 1 else ("x%d" % i)
        parts.append("[%s][v%d]xfade=transition=%s:duration=%.3f:offset=%.3f[%s]"
                     % (prev, i, tr, xf, offset, out_lbl))
        prev = out_lbl
        cum = cum + durs[i] - xf
    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", output_path]
    rc, err = await _ff_run_v7(cmd)
    if rc != 0 or not os.path.exists(output_path) or not await _validate_clip(output_path):
        raise RuntimeError("[video_render] xfade chain failed: %s" % err)
    return output_path


async def _concat_clips_batched(clips, output_path, aspect, episode_id=None):
    """Batched 2-level xfade concat (replaces the O(N^2) rolling fold).

    Level 1 xfade-concats clips in bounded batches (BATCH per ffmpeg pass);
    level 2 xfade-concats the batch outputs. Every adjacent clip boundary still
    gets exactly one xfade, so output is equivalent to the fold but each clip is
    encoded ~twice instead of up to N times. Checkpoints per-clip scaled cache +
    per-batch cache + concat_done marker when episode_id is given.
    """
    BATCH = 8
    XF = 0.5
    transitions = ["fade", "dissolve", "slideleft", "wipeleft",
                   "circleopen", "smoothleft", "fadeblack", "slideup"]
    use_ckpt = bool(episode_id)
    ckpt_dir = _ckpt_dir(episode_id, aspect) if use_ckpt else None
    sig = _clips_signature(clips, aspect) if use_ckpt else None
    concat_done_path = ("%s/concat_done.mp4" % ckpt_dir) if use_ckpt else None

    if use_ckpt:
        m = _load_manifest(ckpt_dir)
        if (m and m.get("sig") == sig and m.get("stage") == "concat_done"
                and os.path.exists(concat_done_path)
                and await _validate_clip(concat_done_path)):
            shutil.copy(concat_done_path, output_path)
            return output_path

    validated, dropped = [], []
    for _c in clips:
        if await _validate_clip(_c):
            validated.append(_c)
        else:
            dropped.append(_c)
    if not validated:
        raise ValueError("[video_render] No valid clips after frame-validation")
    # GATE 29/07/2026: truoc day clip bi loai o day mat hoan toan im lang, nen
    # 12 clip Remotion bien khoi video cuoi ma khong ai biet. Gio phai bao to.
    if dropped:
        _msg = ("[video_render] frame-validation LOAI %d/%d clip: %s"
                % (len(dropped), len(validated) + len(dropped),
                   ", ".join(os.path.basename(str(d)) for d in dropped[:8])))
        logger.warning(_msg)
        if os.getenv("VF_BLOCK_ON_CLIP_DROP", "1").strip() == "1":
            raise RuntimeError(_msg + " (dat VF_BLOCK_ON_CLIP_DROP=0 de bo qua)")
    clips = validated
    w, h = _aspect_to_size(aspect)
    tmp_dir = tempfile.mkdtemp(prefix="vf_render_")
    try:
        work_dir = ckpt_dir if use_ckpt else tmp_dir
        scaled = []
        for i, clip in enumerate(clips):
            # FIX 28/07/2026: see matching fix in _concat_clips - key the
            # cached scaled file by clip content, not just array index, so a
            # stale scaled file from a differently-sourced earlier attempt
            # (e.g. Ken-Burns fallback before a Remotion card render worked)
            # is never silently reused for the same index.
            try:
                _mt = os.path.getmtime(clip)
            except OSError:
                _mt = 0
            _csig = hashlib.sha256((str(clip) + "|" + str(_mt)).encode()).hexdigest()[:10]
            sp = "%s/scaled_%03d_%s.mp4" % (work_dir, i, _csig)
            if use_ckpt and os.path.exists(sp) and await _validate_clip(sp):
                pass
            else:
                sw, sh = await _probe_wh(clip)
                if sw == w and sh == h:
                    shutil.copy(clip, sp)
                else:
                    await _scale_clip(clip, sp, w, h)
            scaled.append(sp)

        if len(scaled) == 1:
            shutil.copy(scaled[0], output_path)
            if use_ckpt:
                shutil.copy(scaled[0], concat_done_path)
                _save_manifest(ckpt_dir, {"sig": sig, "stage": "concat_done"})
            return output_path

        n = len(scaled)
        bounds = [(s, min(s + BATCH, n)) for s in range(0, n, BATCH)]
        batch_files = []
        for bi, (s, e) in enumerate(bounds):
            bpath = "%s/batch_%03d.mp4" % (work_dir, bi)
            if use_ckpt and os.path.exists(bpath) and await _validate_clip(bpath):
                batch_files.append(bpath)
                continue
            rot = bi % len(transitions)
            btrans = transitions[rot:] + transitions[:rot]
            tmpb = bpath + ".tmp.mp4"
            await _xfade_chain_v7(scaled[s:e], tmpb, btrans, xf=XF)
            _atomic_publish(tmpb, bpath)
            batch_files.append(bpath)
            if use_ckpt:
                _save_manifest(ckpt_dir, {"sig": sig, "stage": "batches",
                                          "batches_done": bi + 1})

        if len(batch_files) == 1:
            shutil.copy(batch_files[0], output_path)
        elif len(batch_files) <= BATCH * 2:
            tmp2 = "%s/level2.mp4.tmp.mp4" % work_dir
            await _xfade_chain_v7(batch_files, tmp2, transitions, xf=XF)
            shutil.copy(tmp2, output_path)
        else:
            l2 = "%s/level2.mp4" % work_dir
            await _concat_clips_batched(batch_files, l2, aspect, episode_id=None)
            shutil.copy(l2, output_path)

        if not await _validate_clip(output_path):
            raise RuntimeError("[video_render] batched concat produced invalid file")
        if use_ckpt:
            shutil.copy(output_path, concat_done_path)
            _save_manifest(ckpt_dir, {"sig": sig, "stage": "concat_done"})
        return output_path
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


async def derive_aspect_blurpad(src_path, output_path, aspect):
    """Derive a different aspect ratio from an existing rendered video using a
    blurred-background fill (keeps 100%% of the picture; Reels/TikTok style).
    Audio is copied as-is.
    """
    w, h = _aspect_to_size(aspect)
    fc = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=%d:%d:force_original_aspect_ratio=increase,"
        "crop=%d:%d,gblur=sigma=20[bgb];"
        "[fg]scale=%d:%d:force_original_aspect_ratio=decrease[fgs];"
        "[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[vout]"
    ) % (w, h, w, h, w, h)
    cmd = ["ffmpeg", "-y", "-nostdin", "-i", src_path,
           "-filter_complex", fc, "-map", "[vout]", "-map", "0:a?",
           "-c:a", "copy", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-pix_fmt", "yuv420p", output_path]
    rc, err = await _ff_run_v7(cmd)
    if rc != 0 or not os.path.exists(output_path) or not await _validate_clip(output_path):
        raise RuntimeError("[video_render] blurpad derive failed (%s): %s" % (aspect, err))
    return output_path


_SUB_STYLE_BY_ASPECT = {
    "16:9": _SUB_STYLE,
    "9:16": (
        "Fontname=DejaVu Sans,Fontsize=26,Bold=1,PrimaryColour=&H00FFFFFF&,"
        "OutlineColour=&H90000000&,BorderStyle=3,Outline=2,Shadow=0,"
        "Alignment=2,MarginV=50"
    ),
    "1:1": (
        "Fontname=DejaVu Sans,Fontsize=22,Bold=1,PrimaryColour=&H00FFFFFF&,"
        "OutlineColour=&H90000000&,BorderStyle=3,Outline=2,Shadow=0,"
        "Alignment=2,MarginV=30"
    ),
}


async def burn_subtitles_for_aspect(src_path, output_path, subtitle_segments, aspect):
    """Hotfix v8 (21/07): burn subtitles into an ALREADY aspect-derived video,
    using a style tuned for that aspect's real resolution. Called per-aspect
    AFTER derive_aspect_blurpad/render_video, instead of baking subs into the
    16:9 master before deriving (which shrank/mispositioned subs on 9:16/1:1).
    FIX 12/08/2026 (Rule 90 audit): ffmpeg's `subtitles` filter has no way to
    know the SRT was authored for the OUTPUT resolution, so libass assumed a
    small default script resolution and auto-scaled MarginV ~3-4x, pushing
    subtitles into the upper half of the frame instead of the Rule 90 bottom
    safe zone (measured: 16:9 landed at 19-56% of height instead of 90-100%).
    Passing original_size=WxH (matching the real output resolution) disables
    that auto-scale; MarginV values above are recalibrated for the Rule 90
    bottom-10% safe zone, matching subtitle_karaoke.py's already-correct
    PlayResX/PlayResY-declared ASS approach (which never had this bug).
    Audio is copied as-is.
    """
    style = _SUB_STYLE_BY_ASPECT.get(aspect, _SUB_STYLE)
    w, h = _aspect_to_size(aspect)
    tmp_dir = tempfile.mkdtemp(prefix="vf_subs_")
    try:
        srt_path = f"{tmp_dir}/subs.srt"
        cue_count = _write_srt(subtitle_segments, srt_path)
        if cue_count == 0:
            shutil.copy(src_path, output_path)
            return output_path
        burn_cmd = [
            "ffmpeg", "-y", "-nostdin",
            "-i", src_path,
            "-vf", f"subtitles=subs.srt:original_size={w}x{h}:force_style='{style}'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path,
        ]
        bproc = await asyncio.create_subprocess_exec(
            *burn_cmd, cwd=tmp_dir,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, berr = await bproc.communicate()
        if bproc.returncode != 0:
            raise RuntimeError(f"[video_render] subtitle burn failed ({aspect}): {berr.decode()[-200:]}")
        return output_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
