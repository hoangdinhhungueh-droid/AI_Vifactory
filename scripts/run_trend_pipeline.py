#!/usr/bin/env python3
"""run_trend_pipeline.py — Auto-chain B1.1->B1.2->B1.3 trên VPS.
Không phụ thuộc MCP. Chỉ B1.3 (virality) gửi Telegram alert.
Dùng cho cả cron daily + manual trigger qua MCP (1 lệnh duy nhất).

UPDATE (12/08/2026 decision - Decisions Log): default market "US" -> "EN"
(EN = 1 logical market fanning out to 6 core English sub-geos US/GB/DE/AU/CA/NZ
inside trend_gate_ai.py; commit cap stays 3/day for EN, NOT x6). Cron time moved
from 9h to 7h VN (00:00 UTC) - see scripts/update_trend_cron.py.

Usage:
  python3 scripts/run_trend_pipeline.py                    # full chain
  python3 scripts/run_trend_pipeline.py --skip-raw          # bỏ qua B1.1
  python3 scripts/run_trend_pipeline.py --markets EN JP KR  # chọn market
"""
import json, subprocess, sys, time

BASE = "http://127.0.0.1:8000"
TIMEOUT_RAW = 900
TIMEOUT_REFINE = 600
TIMEOUT_VIRALITY = 1200  # tăng 600→1200 do GT 429 retry chậm

def post(endpoint, payload, timeout):
    """POST to VPS endpoint, return (ok, parsed_json_or_error_dict)."""
    cmd = [
        "curl", "-s", "-m", str(timeout),
        "-X", "POST", BASE + endpoint,
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
    if proc.returncode != 0:
        return False, {"error": "curl rc=%d: %s" % (proc.returncode, proc.stderr[:300])}
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return False, {"error": "non-JSON: %s" % proc.stdout[:300]}
    # Endpoint trả 200 OK + data → success (không cần field 'ok')
    # Chỉ fail nếu có 'ok': false hoặc 'error' mà không có 'generated_at'
    if isinstance(data, dict):
        if data.get("ok") is False:
            return False, data
        if "error" in data and "generated_at" not in data:
            return False, data
    return True, data

def main():
    args = sys.argv[1:]
    skip_raw = "--skip-raw" in args
    markets = ["EN", "JP", "KR"]
    if "--markets" in args:
        idx = args.index("--markets")
        markets = args[idx + 1: idx + 4]

    results = {"steps": []}

    # B1.1 — RAW Pool (silent, no Telegram)
    if not skip_raw:
        print("[B1.1] RAW Pool starting...", flush=True)
        ok1, r1 = post("/api/v1/trend-raw", {"markets": markets, "refresh": True}, TIMEOUT_RAW)
        results["steps"].append({"step": "raw", "ok": ok1, "detail": str(r1)[:500]})
        print("[B1.1] done: ok=%s" % ok1, flush=True)
        if not ok1:
            print("[B1.1] FAILED — aborting chain", flush=True)
            results["ok"] = False
            print(json.dumps(results))
            sys.exit(1)
        time.sleep(5)
    else:
        print("[B1.1] SKIPPED (--skip-raw)", flush=True)
        results["steps"].append({"step": "raw", "ok": True, "detail": "skipped"})

    # B1.2 — Refine (silent, no Telegram)
    print("[B1.2] Refine starting...", flush=True)
    ok2, r2 = post("/api/v1/trend-refine", {"max_searches_per_market": 5}, TIMEOUT_REFINE)
    results["steps"].append({"step": "refine", "ok": ok2, "detail": str(r2)[:500]})
    print("[B1.2] done: ok=%s" % ok2, flush=True)
    if not ok2:
        print("[B1.2] FAILED — continuing to virality anyway (refine is best-effort)", flush=True)
    time.sleep(5)

    # B1.3 — Virality (THIS step sends Telegram alert internally)
    print("[B1.3] Virality starting...", flush=True)
    ok3, r3 = post("/api/v1/trend-virality", {}, TIMEOUT_VIRALITY)
    results["steps"].append({"step": "virality", "ok": ok3, "detail": str(r3)[:500]})
    print("[B1.3] done: ok=%s" % ok3, flush=True)

    results["ok"] = all(s["ok"] for s in results["steps"] if s["step"] != "refine")
    print(json.dumps(results))

main()
