#!/usr/bin/env python3
"""Simulated-output safety gate (Rule 70, muc 5) -- CLI-callable shim.

STATUS: WIRED IN (07/08/2026). The real implementation now lives in
app/services/simulated_asset_gate.py so app/pipeline/stages/s4_tts.py,
s5_visuals.py, s6_subtitle.py, s7_render.py, and app/pipeline/run_episode.py
can import it directly as a normal package module. This scripts/ copy is
kept ONLY as a thin re-export so any existing standalone CLI usage /
muscle-memory (`python3 scripts/simulated_asset_gate.py ...`) still works
unchanged. Edit app/services/simulated_asset_gate.py, not this file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app.services.simulated_asset_gate import (  # noqa: F401
        mark_simulated,
        is_simulated,
        assert_not_simulated,
        clear_simulated,
    )
except Exception:  # pragma: no cover - fallback to a local copy if app/ path differs
    import json
    import time

    def _sidecar_path(asset_path: str) -> str:
        return asset_path + ".simulated.json"

    def mark_simulated(asset_path: str, reason: str, stage: str) -> str:
        sidecar = _sidecar_path(asset_path)
        payload = {
            "asset_path": asset_path, "reason": reason, "stage": stage,
            "marked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return sidecar

    def is_simulated(asset_path: str):
        sidecar = _sidecar_path(asset_path)
        if not os.path.exists(sidecar):
            return None
        with open(sidecar, "r", encoding="utf-8") as f:
            return json.load(f)

    def assert_not_simulated(asset_paths):
        problems = [is_simulated(p) for p in asset_paths if is_simulated(p) is not None]
        if problems:
            raise RuntimeError(
                "BLOCKED: %d simulated/placeholder asset(s) would have been rendered "
                "silently: %s" % (len(problems), json.dumps(problems, ensure_ascii=False)))
        return True

    def clear_simulated(asset_path: str) -> bool:
        sidecar = _sidecar_path(asset_path)
        if os.path.exists(sidecar):
            os.remove(sidecar)
            return True
        return False
