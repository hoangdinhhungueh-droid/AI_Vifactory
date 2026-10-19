#!/usr/bin/env python3
"""
scripts/run_trend_pipeline.py — UNIFIED CANONICAL TREND & PRODUCTION PIPELINE (B1 ➔ B1.5 ➔ B2 ➔ B3)
Standardized Architecture (06/09/2026):
  1. Weekly Staggered Market Production Scheduler:
     - Prevents VPS resource exhaustion and infrastructure crashes by ensuring
       exactly 1 video is produced per day across target markets:
         * Monday & Thursday   ➔ EN (English)
         * Tuesday & Friday     ➔ KR (Korean)
         * Wednesday & Saturday ➔ JP (Japanese)
         * Sunday               ➔ System Rest & B11 Analytics Maintenance (0 new videos)
     - Mandatory Timezone Anchor: Evaluated strictly in Vietnam Time (Asia/Ho_Chi_Minh / UTC+7).
  2. Direct Google & YouTube Trends Ingestion (Zero-Mock Data, Multi-Geo Fan-Out)
  3. B1.5 Competitor Recon & Blue Ocean Differentiation Gap Integrated
  4. Automatic Multi-Candidate Scan & Permanent History Deduplication
  5. Human Gate 1 Pure Informative Broadcast on Telegram (0 interactive buttons)
  6. Automated B2 Story Engine (12-15 min docudrama) & B3 2-Layer Director Plan
  7. Story Gate Self-Repair & Candidate Fallback Protection

Usage:
  python3 scripts/run_trend_pipeline.py                         # Auto-scheduled single market for today
  python3 scripts/run_trend_pipeline.py --market EN             # CLI override: specific market
  python3 scripts/run_trend_pipeline.py --markets EN KR         # CLI override: multiple markets
  python3 scripts/run_trend_pipeline.py --force-all-markets     # Emergency override: all 3 markets
  python3 scripts/run_trend_pipeline.py --term "topic" --market EN # Custom seed term
  python3 scripts/run_trend_pipeline.py --no-produce            # Discovery only (skip B2/B3 production)
  python3 scripts/run_trend_pipeline.py --dry-run               # Inspect scheduled market without running
"""
import logging
import os
import sys
from datetime import datetime, timezone

# Ensure project root in sys.path
sys.path.insert(0, "/root/video_factory")

def _load_system_secrets():
    """Ensure all secrets from /root/secrets/.env are loaded into os.environ for cron execution."""
    for env_path in ["/root/secrets/.env", "/root/video_factory/.env", ".env"]:
        try:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k and v and k not in os.environ:
                                os.environ[k] = v
        except Exception as _ex:
            logger.debug(f"Secret file read notice: {_ex}")

_load_system_secrets()

from app.services.daily_market_lock import is_market_done_today
from app.services.market_scheduler import (
    get_market_schedule_info,
    get_vn_now,
    run_sunday_maintenance,
)
from app.services.trend_engine_b1 import MAX_B2_ATTEMPTS_DEFAULT, discover_and_produce_market_trend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_trend_pipeline")


def _notify_telegram(msg: str):
    """Send summary notification to Telegram."""
    try:
        from app.services.telegram_buttons import send_telegram_broadcast
        send_telegram_broadcast(msg)
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


def main():
    args = sys.argv[1:]
    custom_term = None
    custom_market = "EN"
    auto_produce = "--no-produce" not in args
    is_dry_run = "--dry-run" in args
    force_all = "--force-all-markets" in args
    force_crawl = "--force" in args or "--force-crawl" in args or os.getenv("B1_FORCE_CRAWL") == "1"
    if force_crawl:
        os.environ["B1_FORCE_CRAWL"] = "1"

    cli_markets = None
    if "--markets" in args:
        idx = args.index("--markets")
        cli_markets = [m.upper() for m in args[idx + 1:] if not m.startswith("--")]

    if "--market" in args:
        idx = args.index("--market")
        custom_market = args[idx + 1].upper() if idx + 1 < len(args) else "EN"
        cli_markets = [custom_market]

    if "--term" in args:
        idx = args.index("--term")
        custom_term = args[idx + 1] if idx + 1 < len(args) else None

    max_b2_attempts = int(os.getenv("MAX_B2_ATTEMPTS_PER_RUN", str(MAX_B2_ATTEMPTS_DEFAULT)))
    if "--max-b2-attempts" in args:
        idx = args.index("--max-b2-attempts")
        try:
            max_b2_attempts = int(args[idx + 1])
        except (IndexError, ValueError):
            max_b2_attempts = MAX_B2_ATTEMPTS_DEFAULT

    max_candidates = int(os.getenv("MAX_SCAN_CANDIDATES", "30"))
    if "--max-candidates" in args:
        idx = args.index("--max-candidates")
        try:
            max_candidates = int(args[idx + 1])
        except (IndexError, ValueError):
            max_candidates = 30

    # 1. Evaluate schedule based on Vietnam Timezone (UTC+7)
    schedule_info = get_market_schedule_info()

    if custom_term:
        markets = [custom_market]
        print(f"🎯 [CLI OVERRIDE] Custom seed '{custom_term}' for market {custom_market}")
    elif cli_markets:
        markets = cli_markets
        print(f"🎯 [CLI OVERRIDE] Explicit markets specified: {markets}")
    elif force_all:
        markets = ["EN", "JP", "KR"]
        print("⚠️ [FORCE ALL] Bypassing daily schedule: running all 3 markets (EN, JP, KR)")
    else:
        # Canonical weekly stagger schedule
        if not schedule_info["is_production_day"]:
            print("=======================================================")
            print(f"🛑 [MARKET SCHEDULER] TODAY IS {schedule_info['day_vi'].upper()} ({schedule_info['day_en'].upper()})")
            print(f"Time (VN UTC+7): {schedule_info['timestamp_vn']}")
            print("Weekly schedule designates Sunday as REST & MAINTENANCE DAY (0 new videos).")
            print("=======================================================")
            if is_dry_run:
                print("DRY-RUN: Would execute Sunday maintenance & B11 weekly dreaming.")
                return
            maint_res = run_sunday_maintenance()
            print(f"🧹 Sunday Maintenance Finished: {maint_res['cleanup']}")
            print(f"📊 B11 Routine Status: {maint_res['b11_status']}")
            return

        scheduled_mkt = schedule_info["scheduled_market"]
        markets = [scheduled_mkt]
        print("=======================================================")
        print("📅 [MARKET SCHEDULER] DAILY PRODUCTION CADENCE (1 VIDEO/DAY)")
        print(f"Time (VN UTC+7): {schedule_info['timestamp_vn']} | Day: {schedule_info['day_vi']} ({schedule_info['day_en']})")
        print(f"Assigned Market Today: 🚀 {scheduled_mkt} (Single Market Execution)")
        print("Prevents VPS CPU/RAM crash by isolating production workloads.")
        print("=======================================================")

    if is_dry_run:
        print(f"DRY-RUN EVALUATION: Target markets in scope: {markets}. Auto-produce: {auto_produce}")
        for mkt in markets:
            if not force_crawl:
                is_done, reason, details = is_market_done_today(mkt)
                if is_done:
                    status_name = details.get("status") or reason
                    topic_name = details.get("topic_id") or details.get("raw_term") or ""
                    vn_d = details.get("vn_date") or ""
                    print(f"  🛑 {mkt}: SKIP ({status_name}) — VN Date: {vn_d} {topic_name}".strip())
                else:
                    print(f"  🚀 {mkt}: CRAWL (READY) — Not produced yet today.")
            else:
                print(f"  ⚠️ {mkt}: CRAWL (FORCED) — Bypassing lock due to --force / B1_FORCE_CRAWL=1.")
        return

    # Track baseline cost before execution for session cost telemetry
    initial_month_cost = 0.0
    try:
        from app.services.cost_tracker import get_global_tracker
        initial_month_cost = sum(get_global_tracker().monthly_report().values())
    except Exception as _ex:
        logger.debug(f"Initial cost calculation notice: {_ex}")

    print("=======================================================")
    print("🚀 LAUNCHING UNIFIED TREND & PRODUCTION PIPELINE (B1 ➔ B1.5 ➔ B2)")
    print(f"Execution Time (UTC): {datetime.now(timezone.utc).isoformat()}")
    print(f"Execution Time (VN):  {get_vn_now().isoformat()}")
    print(f"Markets in scope:     {markets}")
    print(f"Auto-Produce B2/B3:   {auto_produce}")
    print(f"Max B2 Attempts:      {max_b2_attempts}")
    print("=======================================================")

    results = {"success": True, "approved_topics": []}

    if custom_term:
        print(f"Processing single custom term '{custom_term}' for market {custom_market}...")
        topics = discover_and_produce_market_trend(
            market=custom_market,
            custom_seed=custom_term,
            auto_produce=auto_produce,
            max_scan_candidates=max_candidates,
            max_b2_attempts=max_b2_attempts
        )
        results["approved_topics"].extend(topics)
    else:
        for mkt in markets:
            print(f"\n--- Running Daily Cycle for Market: {mkt} ---")
            try:
                topics = discover_and_produce_market_trend(
                    market=mkt,
                    auto_produce=auto_produce,
                    max_scan_candidates=max_candidates,
                    max_b2_attempts=max_b2_attempts,
                )
                results["approved_topics"].extend(topics)
            except Exception as e:
                logger.error(f"Error during daily cycle for {mkt}: {e}")


    # Output session cost telemetry
    try:
        from app.services.cost_tracker import get_global_tracker
        final_month_cost = sum(get_global_tracker().monthly_report().values())
        session_cost = max(0.0, final_month_cost - initial_month_cost)
        print("\n-------------------------------------------------------")
        print(f"📊 [COST TELEMETRY] Session Cost: {session_cost:,.2f} VND | Month Total: {final_month_cost:,.2f} VND")
        print("-------------------------------------------------------")
    except Exception as _ex:
        logger.debug(f"Final cost calculation notice: {_ex}")

    # Print summary to console logs (Rule 125: Telegram already notified via Human Gate 1 & Human Gate 2)
    total = len(results["approved_topics"])
    print("\n=======================================================")
    print(f"🎯 PIPELINE COMPLETED: {total} TOPICS PRODUCED & COMMITTED")
    print("=======================================================")

    for t in results["approved_topics"]:
        native_topic = t.get('topic') or t.get('title_a') or t.get('topic_name_vi') or t.get('task_slug')
        print(f"[{t['market']}] {native_topic} (Slug: {t.get('task_slug')})")
        print(f"   Angle: '{t.get('specific_viral_angle')}'")
        print(f"   Blue Ocean Gap: {t.get('competitor_differentiation_gap')}")
        print(f"   Task ID: {t.get('task_id')}")
        print("   Status: Human Gate 1 & Human Gate 2 dispatched.")



if __name__ == "__main__":
    main()
