#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run B3.6 Visual Convergence Audit for an episode."""

import sys
sys.path.insert(0, "/root/video_factory")
from app.services.b36_visual_convergence import run_b36_visual_convergence

if __name__ == "__main__":
    ep_id = sys.argv[1] if len(sys.argv) > 1 else "EN_EP0006_foreign_capital_us_stocks"
    market = sys.argv[2] if len(sys.argv) > 2 else ep_id.split("_")[0].upper()
    print(f"=== RUNNING B3.6 AUDIT FOR {ep_id} ({market}) ===")
    res = run_b36_visual_convergence(ep_id, market=market)
    print(f"B3.6 AUDIT COMPLETE: Score={res.get('final_score')} | Converged={res.get('converged')} | Rounds={res.get('rounds_count')}")
