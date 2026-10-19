#!/usr/bin/env python3
"""scripts/forensics/probe_service_readiness.py — Fail-Closed FastAPI Service Readiness Probe (Rule 121 & Rule 139).
Restarts vf-api via PM2 and polls health endpoint with timeout. Fails closed (exit code 1) on budget expiration.
"""

import subprocess
import sys
import time
import urllib.request


def check_health(url: str = "http://127.0.0.1:8000/api/v1/health") -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VF-HealthProbe/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                body = resp.read().decode("utf-8", errors="replace")
                return "ok" in body.lower()
    except Exception:
        return False
    return False


def main() -> int:
    print("--- VF-API PM2 RESTART & HEALTH POLLING PROBE ---")
    res_restart = subprocess.run(["pm2", "restart", "vf-api"], capture_output=True, text=True, check=False)
    if res_restart.returncode != 0:
        print(f"❌ FAIL: PM2 restart returned exit code {res_restart.returncode}: {res_restart.stderr}", file=sys.stderr)
        return 1

    start_ts = time.time()
    online = False
    for attempt in range(1, 26):
        time.sleep(1.0)
        if check_health():
            online = True
            latency = round(time.time() - start_ts, 2)
            print(f"✅ VF_API_ONLINE confirmed on attempt {attempt}/25 ({latency}s)")
            break

    if not online:
        print("❌ FAIL: Service vf-api failed to return HTTP 200 within 25s budget (fail-closed)", file=sys.stderr)
        return 1

    res_status = subprocess.run(["pm2", "status", "vf-api"], capture_output=True, text=True, check=False)
    print(res_status.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
