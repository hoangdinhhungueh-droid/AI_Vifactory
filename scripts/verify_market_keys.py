"""Verify all YouTube OAuth keys (EN/JP/KR) are active and correctly set.

Non-destructive: GET only -- calls channels().list(mine=True) for each market.
Added by [AG] 21/08/2026.

Usage:
  python3 scripts/verify_market_keys.py          # verify all 3
  python3 scripts/verify_market_keys.py en        # verify EN only
  python3 scripts/verify_market_keys.py jp        # verify JP only
  python3 scripts/verify_market_keys.py kr        # verify KR only
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yt_oauth_setup_market import verify_market_channel
import json

MARKETS = ["en", "jp", "kr"]


def run(markets=None):
    targets = markets or MARKETS
    results = []
    all_ok = True
    print("\n=" * 60)
    print("  YouTube OAuth Key Verification -- VF Multi-Market")
    print("=" * 60)
    for m in targets:
        print(f"\n[{m.upper()}] Verifying...")
        r = verify_market_channel(m)
        results.append(r)
        if r.get("status") == "ACTIVE":
            print(f"  STATUS : ACTIVE ✅")
            print(f"  Channel: {r.get('title')} ({r.get('customUrl')})")
            print(f"  ID     : {r.get('channelId')}")
            print(f"  Country: {r.get('country')}")
            print(f"  Subs   : {r.get('subscriberCount')}")
            print(f"  Videos : {r.get('videoCount')}")
        else:
            print(f"  STATUS : ERROR ❌")
            print(f"  Error  : {r.get('error')}")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print(f"  RESULT: ALL {len(targets)} MARKET(S) ACTIVE ✅")
    else:
        failed = [r['market'] for r in results if r.get('status') != 'ACTIVE']
        print(f"  RESULT: FAILED markets: {', '.join(failed)} ❌")
    print("=" * 60 + "\n")
    return results, all_ok


if __name__ == "__main__":
    markets = [a.lower() for a in sys.argv[1:]] if len(sys.argv) > 1 else None
    results, all_ok = run(markets)
    sys.exit(0 if all_ok else 1)
