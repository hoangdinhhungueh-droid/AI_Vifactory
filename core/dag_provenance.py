#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/dag_provenance.py — Deterministic DAG Provenance, Complete Export Purging & Episode Lock.

Fixes pipeline architecture gaps:
1. Full DAG input/config SHA-256 provenance tracking (including external seeds like grounding_intel.json).
2. Declarative consumer/export registry per stage so invalidation & mid-stage crash recovery remove
   all secondary root files, subdirectories, and stage intermediates without relying on a 6-file list.
3. Cross-process per-episode FileLock guarding manifest & artifact mutations against concurrent races.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from filelock import FileLock, Timeout

from core.atomic_io import atomic_write_json
from core.contracts.stages import StageID
from core.paths import RunPaths

logger = logging.getLogger(__name__)

# Full upstream stage dependencies beyond direct linear predecessor
STAGE_DAG_PARENTS: Dict[StageID, List[StageID]] = {
    StageID.S1_IDEATION: [],
    StageID.S2_RESEARCH: [StageID.S1_IDEATION],
    StageID.S3_SCRIPT: [StageID.S1_IDEATION, StageID.S2_RESEARCH],
    StageID.S4_CRITIC_SCRIPT: [StageID.S1_IDEATION, StageID.S2_RESEARCH, StageID.S3_SCRIPT],
    StageID.S5_DIRECTOR_PLAN: [StageID.S1_IDEATION, StageID.S3_SCRIPT, StageID.S4_CRITIC_SCRIPT],
    StageID.S6_CRITIC_VISUAL: [StageID.S5_DIRECTOR_PLAN],
    StageID.S7_IMAGE_GEN: [StageID.S5_DIRECTOR_PLAN, StageID.S6_CRITIC_VISUAL],
    StageID.S8_VIDEO_GEN: [StageID.S5_DIRECTOR_PLAN, StageID.S7_IMAGE_GEN],
    StageID.S9_VOICE_TTS: [StageID.S1_IDEATION, StageID.S3_SCRIPT],
    StageID.S10_RENDER: [
        StageID.S3_SCRIPT,
        StageID.S5_DIRECTOR_PLAN,
        StageID.S8_VIDEO_GEN,
        StageID.S9_VOICE_TTS,
    ],
    StageID.S11_QC: [StageID.S4_CRITIC_SCRIPT, StageID.S5_DIRECTOR_PLAN, StageID.S10_RENDER],
}

# Optional cross-stage inputs that invalidate downstream when already consumed
STAGE_OPTIONAL_PARENTS: Dict[StageID, List[StageID]] = {
    StageID.S8_VIDEO_GEN: [StageID.S9_VOICE_TTS],
}

# Episode-root non-stage seed inputs whose mutation must invalidate dependent stages
STAGE_EXTRA_ROOT_INPUTS: Dict[StageID, List[str]] = {
    StageID.S1_IDEATION: ["grounding_intel.json"],
    StageID.S2_RESEARCH: ["grounding_intel.json"],
    StageID.S3_SCRIPT: ["grounding_intel.json"],
    StageID.S4_CRITIC_SCRIPT: ["grounding_intel.json"],
}

# Complete registry of secondary exports and subdirectories owned by each stage
STAGE_EXPORT_SPECS: Dict[StageID, Dict[str, List[str]]] = {
    StageID.S1_IDEATION: {
        "root_files": [],
        "root_dirs": [],
        "root_globs": [],
    },
    StageID.S2_RESEARCH: {
        "root_files": ["competitor_intel_card.json"],
        "root_dirs": [],
        "root_globs": [],
    },
    StageID.S3_SCRIPT: {
        "root_files": [
            "spoken_script.txt",
            "spoken_sentences.json",
            "story.txt",
            "beats.json",
        ],
        "root_dirs": [],
        "root_globs": [],
    },
    StageID.S4_CRITIC_SCRIPT: {
        "root_files": ["story_critic.json"],
        "root_dirs": [],
        "root_globs": [],
    },
    StageID.S5_DIRECTOR_PLAN: {
        "root_files": [
            "director_plan.json",
            "dp_plan.json",
            "flow_video_manifest.json",
            "bulk_image_prompts.txt",
            "bulk_video_prompts.txt",
            "diorama_video_prompts.json",
            "prompts.json",
            "prompts_manifest.json",
            "vox_scene_manifest.json",
            "whisper_segments.json",
        ],
        "root_dirs": ["master_sheets"],
        "root_globs": [],
    },
    StageID.S6_CRITIC_VISUAL: {
        "root_files": [
            "visual_forensic_health_card.json",
            "visual_forensic_health_card.md",
        ],
        "root_dirs": ["visual_audit"],
        "root_globs": [],
    },
    StageID.S7_IMAGE_GEN: {
        "root_files": ["images_manifest.json"],
        "root_dirs": ["images", "assets", "composite_seeds"],
        "root_globs": [],
    },
    StageID.S8_VIDEO_GEN: {
        "root_files": [
            "video_manifest.json",
            "pilot_30s.mp4",
            "pilot_manifest.json",
        ],
        "root_dirs": ["video_clips", "chained_frames", "blocks", "pilot_30s"],
        "root_globs": ["clip_*.mp4"],
    },
    StageID.S9_VOICE_TTS: {
        "root_files": [
            "narration.mp3",
            "narration.wav",
            "whisper_segments.json",
            "subtitles.srt",
            "subtitles.ass",
        ],
        "root_dirs": ["audio"],
        "root_globs": [],
    },
    StageID.S10_RENDER: {
        "root_files": [
            "remotion_props.json",
            "final.mp4",
            "thumbnail.png",
            "thumbnail.jpg",
            "subtitles.srt",
            "subtitles.ass",
        ],
        "root_dirs": ["10_render"],
        "root_globs": [],
    },
    StageID.S11_QC: {
        "root_files": ["seo_package.json", "brain_input.json", "qc_report.json"],
        "root_dirs": [],
        "root_globs": [],
    },
}


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_file_sha256(path: Path) -> str:
    """Compute SHA-256 of an existing regular file, returning 'ABSENT' if missing."""
    if not path.exists() or not path.is_file():
        return "ABSENT"
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def compute_stage_config_sha256(
    stage: StageID,
    preset_name: Optional[str] = None,
    repo_root: Optional[Path] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> str:
    """Hash active preset, stage prompt markdown, and runtime parameters for provenance."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    components: Dict[str, Any] = {
        "stage": stage.value,
        "preset_name": preset_name or "",
        "extra_params": extra_params or {},
        "files": {},
    }

    candidate_files: List[Path] = []
    if preset_name:
        clean = str(preset_name).removesuffix(".yaml").removesuffix(".yml")
        candidate_files.extend([
            root / "config" / "presets" / f"{clean}.yaml",
            root / "config" / "presets" / f"{clean}.yml",
        ])
    candidate_files.extend([
        root / "config" / "prompts" / "story_forensic" / f"{stage.value}.md",
        root / "config" / "prompts" / f"{stage.value}.md",
    ])

    for fpath in candidate_files:
        if fpath.exists() and fpath.is_file():
            try:
                rel = str(fpath.relative_to(root)).replace("\\", "/")
            except ValueError:
                rel = str(fpath)
            components["files"][rel] = safe_file_sha256(fpath)

    serialized = json.dumps(components, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return compute_sha256_bytes(serialized)


def compute_stage_input_provenance(
    stage: StageID,
    paths: RunPaths,
    config_sha256: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    """Compute canonical combined input hash and per-dependency hash ledger for a stage."""
    upstream_map: Dict[str, str] = {}

    for parent in STAGE_DAG_PARENTS.get(stage, []):
        upstream_map[parent.value] = safe_file_sha256(paths.artifact_file(parent.value))

    for opt_parent in STAGE_OPTIONAL_PARENTS.get(stage, []):
        opt_path = paths.artifact_file(opt_parent.value)
        if opt_path.exists():
            upstream_map[opt_parent.value] = safe_file_sha256(opt_path)

    for rel_input in STAGE_EXTRA_ROOT_INPUTS.get(stage, []):
        upstream_map[f"root:{rel_input}"] = safe_file_sha256(paths.root / rel_input)

    payload = {
        "stage": stage.value,
        "upstream": upstream_map,
        "config_sha256": config_sha256 or "",
    }
    combined = compute_sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return combined, upstream_map


def _is_safe_child(target: Path, episode_root: Path) -> bool:
    """Strictly contain deletions within episode_root and reject symlinks (Rule 137)."""
    if target.is_symlink():
        return False
    try:
        resolved_root = episode_root.resolve()
        resolved_target = target.resolve()
        return resolved_target != resolved_root and resolved_target.is_relative_to(resolved_root)
    except OSError:
        return False


def purge_stage_outputs(
    stage: StageID,
    paths: RunPaths,
    include_artifact_file: bool = True,
) -> List[str]:
    """Delete artifact, stage working files, and secondary root exports owned by `stage`."""
    purged: List[str] = []
    episode_root = paths.root
    spec = STAGE_EXPORT_SPECS.get(stage, {})

    if include_artifact_file:
        art_file = paths.artifact_file(stage.value)
        if art_file.exists() and _is_safe_child(art_file, episode_root):
            try:
                art_file.unlink()
                purged.append(str(art_file.relative_to(episode_root)).replace("\\", "/"))
            except OSError as exc:
                logger.warning(f"[dag_provenance] Failed to unlink {art_file}: {exc}")

    # Clean non-artifact intermediate files inside the stage directory
    sdir = paths.stage_dir(stage.value)
    if sdir.exists() and sdir.is_dir() and _is_safe_child(sdir, episode_root):
        for child in list(sdir.iterdir()):
            if child.name == "artifact.json" and not include_artifact_file:
                continue
            if not _is_safe_child(child, episode_root):
                continue
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                purged.append(str(child.relative_to(episode_root)).replace("\\", "/"))
            except OSError as exc:
                logger.warning(f"[dag_provenance] Failed to clean stage child {child}: {exc}")

    # Purge root-level secondary files
    for rel_file in spec.get("root_files", []):
        target = episode_root / rel_file
        if target.exists() and target.is_file() and _is_safe_child(target, episode_root):
            try:
                target.unlink()
                purged.append(rel_file)
            except OSError as exc:
                logger.warning(f"[dag_provenance] Failed to unlink root export {target}: {exc}")

    # Purge root-level globs (e.g. clip_*.mp4)
    for pattern in spec.get("root_globs", []):
        for match in episode_root.glob(pattern):
            if match.is_file() and _is_safe_child(match, episode_root):
                try:
                    match.unlink()
                    purged.append(str(match.relative_to(episode_root)).replace("\\", "/"))
                except OSError as exc:
                    logger.warning(f"[dag_provenance] Failed to unlink glob match {match}: {exc}")

    # Purge owned root subdirectories
    for rel_dir in spec.get("root_dirs", []):
        target_dir = episode_root / rel_dir
        if target_dir.exists() and target_dir.is_dir() and _is_safe_child(target_dir, episode_root):
            try:
                shutil.rmtree(target_dir)
                purged.append(rel_dir)
            except OSError as exc:
                logger.warning(f"[dag_provenance] Failed to remove root dir {target_dir}: {exc}")

    return purged


@contextlib.contextmanager
def acquire_run_lock(paths: RunPaths, timeout_sec: float = 30.0) -> Iterator[Path]:
    """Acquire an exclusive per-episode file lock to prevent concurrent manifest/artifact races."""
    paths.root.mkdir(parents=True, exist_ok=True)
    lock_path = paths.root / ".pipeline_run.lock"
    lock = FileLock(str(lock_path), timeout=timeout_sec)
    try:
        with lock:
            # Record lightweight diagnostics without interfering with FileLock fd
            meta_path = paths.root / ".pipeline_run.owner"
            try:
                meta_path.write_text(
                    json.dumps({"pid": os.getpid(), "run_id": paths.run_id}),
                    encoding="utf-8",
                )
            except OSError as meta_err:
                logger.debug(f"[dag_provenance] Notice writing lock owner metadata: {meta_err}")
            try:
                yield lock_path
            finally:
                try:
                    if meta_path.exists():
                        meta_path.unlink()
                except OSError as rm_err:
                    logger.debug(f"[dag_provenance] Notice cleaning lock owner metadata: {rm_err}")
    except Timeout as exc:
        raise TimeoutError(
            f"Timed out after {timeout_sec:.1f}s waiting for exclusive pipeline lock at {lock_path}"
        ) from exc


def check_stage_cache_valid(
    stage: StageID,
    paths: RunPaths,
    state: Any,
    expected_in_sha: str,
    cfg_sha: str,
    sha_now: str,
) -> Tuple[bool, str]:
    """Verify both SHA-256 on disk AND full DAG input/config provenance before idempotent skip."""
    from core.gates import validate_artifact

    if state is None or state.status not in ("done", "skipped"):
        return False, "stage_not_done"
    if not state.artifact_sha256 or state.artifact_sha256 != sha_now:
        return False, "artifact_sha_mismatch"
    if not state.input_sha256 or state.input_sha256 != expected_in_sha:
        return False, "input_provenance_changed"
    if not state.config_sha256 or state.config_sha256 != cfg_sha:
        return False, "config_provenance_changed"

    art_path = paths.artifact_file(stage.value)
    if not art_path.exists():
        return False, "artifact_missing"
    try:
        raw_art = json.loads(art_path.read_text(encoding="utf-8"))
        parsed_art = validate_artifact(stage, raw_art)
    except Exception as exc:
        return False, f"schema_invalid:{exc}"

    if parsed_art.run_id != paths.run_id:
        return False, "run_id_mismatch"
    if parsed_art.provenance.input_sha256 and parsed_art.provenance.input_sha256 != expected_in_sha:
        return False, "artifact_input_sha_mismatch"
    return True, "ok"


def stamp_artifact_provenance(
    art_path: Path,
    input_sha256: str,
    config_sha256: str,
    upstream_artifacts: Dict[str, str],
    run_nonce: str,
) -> None:
    """Persist cryptographic input/config provenance onto a generated StageArtifact file atomically."""
    if not art_path.exists():
        return
    try:
        raw = json.loads(art_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"[dag_provenance] Could not parse artifact {art_path} for provenance stamp: {exc}")
        return
    if not isinstance(raw, dict):
        return
    prov = raw.get("provenance")
    if not isinstance(prov, dict):
        prov = {}
        raw["provenance"] = prov
    prov["input_sha256"] = input_sha256
    prov["config_sha256"] = config_sha256
    prov["upstream_artifacts"] = dict(upstream_artifacts)
    prov["run_nonce"] = run_nonce
    atomic_write_json(art_path, raw, indent=2)
