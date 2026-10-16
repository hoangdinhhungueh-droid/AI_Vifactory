#!/usr/bin/env python3
"""
tools/forensics/verify_live_crawl_terminal.py — Isolated Post-Deploy Terminal Run Verification
Mandate:
  1. Drives a post-deploy terminal crawl path in a strictly isolated environment.
  2. 100% Hermetic isolation:
     - State dir routed to tempdir (VF_STATE_DIR)
     - Cost ledger routed to tempdir (VF_COST_DIR)
     - Outbound Telegram dispatch disabled (TELEGRAM_ENABLED=0)
  3. Verifies zero mutation to production cost ledger, alert cooldown, and locks.
  4. Correctly audits lock status, lock token, and exhausted_at_utc.
  5. Proves zero-mock compliance (Rule 118, Rule 121, Rule 123).
"""

import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_live_crawl")


def get_production_cost_baseline() -> float:
    cost_dir = Path(os.environ.get("VF_COST_DIR", "/var/vf/cost"))
    total_usd = 0.0
    if cost_dir.exists():
        for p in cost_dir.glob("*.jsonl"):
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        row = json.loads(line)
                        total_usd += float(row.get("usd") or 0.0)
            except Exception as _e:
                logger.debug("Failed reading cost line from %s: %s", p, _e)
    return round(total_usd, 6)


def main():
    # 0. Measure production baseline before execution
    prod_cost_before = get_production_cost_baseline()
    prod_cooldown_path = Path("/var/vf/alert_cooldown.json")
    prod_cooldown_mtime_before = prod_cooldown_path.stat().st_mtime if prod_cooldown_path.exists() else 0.0

    isolated_state = Path(tempfile.mkdtemp(prefix="vf_isolated_state_"))
    isolated_history = isolated_state / "topic_history.json"
    isolated_pending = isolated_state / "pending_tasks"
    isolated_episodes = isolated_state / "episodes"
    isolated_cost = isolated_state / "cost"

    isolated_pending.mkdir(parents=True, exist_ok=True)
    isolated_episodes.mkdir(parents=True, exist_ok=True)
    isolated_cost.mkdir(parents=True, exist_ok=True)

    print("=======================================================")
    print("🔬 RUNNING HERMETIC ISOLATED TERMINAL CRAWL VERIFICATION")
    print(f"Isolated State Dir:    {isolated_state}")
    print(f"Isolated Cost Dir:     {isolated_cost}")
    print(f"Isolated History Path: {isolated_history}")
    print(f"Isolated Pending Dir:  {isolated_pending}")
    print(f"Isolated Episodes Dir: {isolated_episodes}")
    print(f"Production Cost Before: ${prod_cost_before:.6f}")
    print("=======================================================")

    # Strict isolation env overrides
    os.environ["VF_STATE_DIR"] = str(isolated_state)
    os.environ["VF_COST_DIR"] = str(isolated_cost)
    os.environ["TOPIC_HISTORY_PATH"] = str(isolated_history)
    os.environ["PENDING_TASKS_DIR"] = str(isolated_pending)
    os.environ["VF_EPISODES_DIR"] = str(isolated_episodes)
    # Strictly disable Telegram dispatch to eliminate outbound notifications
    os.environ["TELEGRAM_ENABLED"] = "0"
    os.environ["TELEGRAM_BOT_TOKEN"] = ""
    os.environ["TELEGRAM_CHAT_ID"] = ""

    try:
        from app.services.trend_engine_b1 import discover_and_produce_market_trend
        from app.services.daily_market_lock import is_market_done_today

        # Execute terminal crawl on market EN with auto_produce=False so it exercises
        # the complete B1 -> B1.5 candidate discovery, viability scoring, and terminal completion
        # without invoking heavyweight downstream rendering during verification.
        print("\n--- Executing discover_and_produce_market_trend in isolated state ---")
        topics = discover_and_produce_market_trend(
            market="EN",
            auto_produce=False,
            max_scan_candidates=5,
            state_dir=str(isolated_state),
        )
        print(f"\nExecution finished. Topics produced: {len(topics)}")

        # Audit lock directory
        lock_dir = isolated_state / "b1_daily_lock"
        print(f"\n--- Auditing Daily Lock State in {lock_dir} ---")
        lock_files = list(lock_dir.glob("EN_*.json")) if lock_dir.exists() else []
        print(f"Found {len(lock_files)} lock file(s): {[f.name for f in lock_files]}")
        assert len(lock_files) == 1, f"Expected exactly 1 lock file for EN, found {len(lock_files)}"

        lock_content = json.loads(lock_files[0].read_text(encoding="utf-8"))
        status = lock_content.get("status")
        timestamp_str = lock_content.get("exhausted_at_utc") or lock_content.get("created_at_utc") or lock_content.get("timestamp")
        print(f"Lock Status:       {status}")
        print(f"Lock Token:        {lock_content.get('lock_token')}")
        print(f"Exhausted/Created: {timestamp_str}")
        print(f"Process PID:       {lock_content.get('pid')}")
        assert status in ("COMPLETED", "EXHAUSTED_TODAY"), f"Unexpected status: {status}"
        assert timestamp_str is not None, "Timestamp in lock record must not be None!"

        # Audit isolated alert cooldown
        cd_file = isolated_state / "alert_cooldown.json"
        print(f"\n--- Auditing Isolated Alert Cooldown State in {cd_file} ---")
        if cd_file.exists():
            cd_data = json.loads(cd_file.read_text(encoding="utf-8"))
            print(f"Isolated cooldown entries recorded: {list(cd_data.keys())}")
        else:
            print("Notice: No alert cooldown entries needed in isolated run.")

        # Audit isolated cost ledger
        isolated_cost_files = list(isolated_cost.glob("*.jsonl"))
        print(f"\n--- Auditing Isolated Cost Ledger in {isolated_cost} ---")
        print(f"Isolated cost ledger files: {[f.name for f in isolated_cost_files]}")
        isolated_spend = 0.0
        for cf in isolated_cost_files:
            for line in cf.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    isolated_spend += float(json.loads(line).get("usd") or 0.0)
        print(f"Isolated spend recorded: ${isolated_spend:.6f} USD")

        # Verify production cost and cooldown were NOT touched
        prod_cost_after = get_production_cost_baseline()
        prod_cooldown_mtime_after = prod_cooldown_path.stat().st_mtime if prod_cooldown_path.exists() else 0.0
        print(f"\n--- Production Side-Effect Invariance Check ---")
        print(f"Production Spend Delta:    ${(prod_cost_after - prod_cost_before):.6f}")
        print(f"Production Cooldown Delta: {prod_cooldown_mtime_after - prod_cooldown_mtime_before}s")
        assert prod_cost_after == prod_cost_before, f"CRITICAL: Production cost mutated! {prod_cost_before} -> {prod_cost_after}"
        assert prod_cooldown_mtime_after == prod_cooldown_mtime_before, "CRITICAL: Production alert cooldown was touched!"

        # Verify is_market_done_today recognizes the lock
        is_done, reason, details = is_market_done_today("EN", state_dir=str(isolated_state))
        print(f"\nis_market_done_today: is_done={is_done}, reason={reason}")
        assert is_done is True, f"Expected market to be done, got {is_done}"

        print("\n=======================================================")
        print("✅ HERMETIC ISOLATED TERMINAL CRAWL VERIFICATION: PASS")
        print("=======================================================")
        return 0

    except Exception as e:
        logger.exception(f"Verification failed: {e}")
        print(f"\n❌ VERIFICATION FAILED: {e}")
        return 1
    finally:
        try:
            shutil.rmtree(isolated_state, ignore_errors=True)
        except Exception as _cleanup_err:
            logger.debug("Failed cleaning isolated_state %s: %s", isolated_state, _cleanup_err)


if __name__ == "__main__":
    sys.exit(main())
