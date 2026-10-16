#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/forensics/probe_s05_live.py — Programmatic live runtime execution probe for Stage S05 (Rule 127).

Hermetically executes Stage S05 against real filesystem paths and verifies:
1. S3 payload loading from disk without NameError or KeyError.
2. Scene and Shot planning with Universal Video Prompt generation.
3. Successful artifact emission with status='ok' and scenes count == 1.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import RunContext, load_profile
from core.contracts.stages import Provenance, StageArtifact, StageID
from core.paths import resolve_run_paths
from core.run_manifest import RunManifest
from stages.s05_director_plan import run as run_s05


def probe_s05() -> int:
    tmp = tempfile.mkdtemp(prefix="probe_s05_")
    try:
        rp = resolve_run_paths("test_s05_live", repo_root=Path(tmp))
        rp.ensure_dirs()
        s3_path = rp.artifact_file(StageID.S3_SCRIPT.value)
        s3_path.parent.mkdir(parents=True, exist_ok=True)
        s3_payload = {
            "scenes": [
                {
                    "scene_id": "SC_01",
                    "narration": "Liquidity contraction triggers systemic failure.",
                    "visual_metaphor": "paper desk dossier",
                    "headline": "Global Shock",
                    "color_accent": "Vox Yellow #F2C230",
                }
            ],
            "script_text": "Liquidity contraction triggers systemic failure.",
        }
        s3_art = StageArtifact(
            run_id="test_s05_live",
            stage=StageID.S3_SCRIPT,
            status="ok",
            payload=s3_payload,
            provenance=Provenance(generator="probe", latency_sec=0.1),
        )
        s3_path.write_text(json.dumps(s3_art.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        cfg = load_profile("e2e_min")
        manifest = RunManifest.create_new("test_s05_live", profile="e2e_min")
        ctx = RunContext(run_id="test_s05_live", config=cfg, paths=rp, manifest=manifest, force=True, dry_run=False)
        res = run_s05(ctx)
        assert res.status == "ok", f"Expected res.status == 'ok', got {res.status}"
        scenes = res.payload.get("scenes", [])
        assert len(scenes) == 1, f"Expected 1 scene, got {len(scenes)}"
        print(f"S05_LIVE_RUNTIME_EXECUTION_PASS: Stage S05 ran against real directory with status=ok, scenes={len(scenes)}")
        return 0
    except Exception as ex:
        print(f"S05_LIVE_RUNTIME_EXECUTION_FAIL: {ex}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(probe_s05())
