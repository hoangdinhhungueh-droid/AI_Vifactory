#!/usr/bin/env python3
"""
scripts/run_trend_pipeline.py — UNIFIED CANONICAL TREND PIPELINE (B1 ➔ B1.5 ➔ B2 ➔ B3)
Standardized Architecture (05/09/2026):
  1. Direct Google & YouTube Trends Ingestion (Zero-Mock Data, Multi-Geo Fan-Out)
  2. B1.5 Competitor Recon & Blue Ocean Differentiation Gap Integrated
  3. Automatic Multi-Candidate Scan & Permanent History Deduplication
  4. Human Gate 1 Pure Informative Broadcast on Telegram (0 interactive buttons)
  5. Automated B2 Story Engine (12-15 min docudrama) & B3 2-Layer Director Plan
  6. Story Gate Self-Repair & Candidate Fallback Protection

Usage:
  python3 scripts/run_trend_pipeline.py                         # All 3 markets (EN, JP, KR) auto-produced
  python3 scripts/run_trend_pipeline.py --markets EN            # Specific market auto-produced
  python3 scripts/run_trend_pipeline.py --term "topic" --market EN # Custom seed term
  python3 scripts/run_trend_pipeline.py --no-produce            # Discovery only (skip B2/B3 production)
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone

# Ensure project root in sys.path
sys.path.insert(0, "/root/video_factory")

from app.services.trend_engine_b1 import (
    discover_and_produce_market_trend,
    run_daily_all_markets
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_trend_pipeline")


def _notify_telegram(msg: str):
    """Send summary notification to Telegram."""
    try:
        from app.llm_router import _send_telegram
        _send_telegram(msg)
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


def main():
    args = sys.argv[1:]
    markets = ["EN", "JP", "KR"]
    custom_term = None
    custom_market = "EN"
    auto_produce = "--no-produce" not in args

    if "--markets" in args:
        idx = args.index("--markets")
        markets = [m.upper() for m in args[idx + 1:] if not m.startswith("--")]

    if "--term" in args:
        idx = args.index("--term")
        custom_term = args[idx + 1] if idx + 1 < len(args) else None

    if "--market" in args:
        idx = args.index("--market")
        custom_market = args[idx + 1].upper() if idx + 1 < len(args) else "EN"

    print("=======================================================")
    print("🚀 LAUNCHING UNIFIED TREND & PRODUCTION PIPELINE (B1 ➔ B1.5 ➔ B2)")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Auto-Produce B2/B3: {auto_produce}")
    print("=======================================================")

    results = {"success": True, "approved_topics": []}

    if custom_term:
        print(f"Processing single custom term '{custom_term}' for market {custom_market}...")
        topics = discover_and_produce_market_trend(
            market=custom_market,
            custom_seed=custom_term,
            auto_produce=auto_produce
        )
        results["approved_topics"].extend(topics)
    else:
        for mkt in markets:
            print(f"\n--- Running Daily Cycle for Market: {mkt} ---")
            try:
                topics = discover_and_produce_market_trend(
                    market=mkt,
                    auto_produce=auto_produce
                )
                results["approved_topics"].extend(topics)
            except Exception as e:
                logger.error(f"Error during daily cycle for {mkt}: {e}")

    # Build summary and send Telegram alert
    total = len(results["approved_topics"])
    print("\n=======================================================")
    print(f"🎯 PIPELINE COMPLETED: {total} TOPICS PRODUCED & COMMITTED")
    print("=======================================================")

    tg_lines = [f"🚀 <b>VF Daily Trend & Story Pipeline (B1 ➔ B3)</b> — {total} Đề tài hoàn tất:"]
    for t in results["approved_topics"]:
        print(f"[{t['market']}] {t.get('topic_name_vi')} (Slug: {t.get('task_slug')})")
        print(f"   Angle: '{t.get('specific_viral_angle')}'")
        print(f"   Blue Ocean Gap: {t.get('competitor_differentiation_gap')}")
        print(f"   Task ID: {t.get('task_id')}")

        tg_lines.append(
            f"\n🌍 <b>Thị trường {t['market']}</b>: <b>{t.get('topic_name_vi')}</b>\n"
            f"• <i>Viral Angle</i>: {t.get('specific_viral_angle')}\n"
            f"• <i>Khác biệt đối thủ</i>: {t.get('competitor_differentiation_gap')}\n"
            f"• <i>Task ID</i>: <code>{t.get('task_id')}</code>\n"
            f"• <i>Status</i>: ✅ <b>Kịch bản 12-15 phút & Visual Plan sẵn sàng</b>"
        )

    if total > 0:
        _notify_telegram("\n".join(tg_lines))


if __name__ == "__main__":
    main()
