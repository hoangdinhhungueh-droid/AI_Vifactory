#!/usr/bin/env python3
"""scripts/forensics/probe_service_readiness.py — Fail-Closed FastAPI Service Readiness Probe (Rule 121 & Rule 139).
Restarts vf-api via PM2 and polls health endpoint with strict JSON parsing and monotonic deadline.
Fails closed (exit code 1) on restart failure, budget expiration, or invalid process status.
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple


def check_health(url: str = "http://127.0.0.1:8000/api/v1/health", timeout_sec: float = 2.0) -> Tuple[bool, Optional[str]]:
    """Polls health endpoint and validates parsed JSON status == 'ok' with narrow transport exception handling."""
    req = urllib.request.Request(url, headers={"User-Agent": "VF-HealthProbe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status != 200:
                return False, f"HTTP status {resp.status}"
            raw_bytes = resp.read()
            body_str = raw_bytes.decode("utf-8")
            data = json.loads(body_str)
            if isinstance(data, dict) and data.get("status") == "ok":
                return True, "status=ok"
            return False, f"Unexpected health payload: {data}"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionResetError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def verify_pm2_process_state(process_name: str = "vf-api", timeout_sec: float = 10.0) -> Tuple[bool, str]:
    """Inspects PM2 process state using jlist to ensure process is active and status is 'online'."""
    try:
        res = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=timeout_sec, check=False)
        if res.returncode != 0:
            return False, f"pm2 jlist failed with exit code {res.returncode}: {res.stderr.strip()}"
        procs = json.loads(res.stdout)
        target = next((p for p in procs if p.get("name") == process_name), None)
        if not target:
            return False, f"Process '{process_name}' not found in PM2 process inventory"
        status = target.get("pm2_env", {}).get("status")
        if status != "online":
            return False, f"Process '{process_name}' status is '{status}', expected 'online'"
        pid = target.get("pid")
        uptime = target.get("pm2_env", {}).get("pm_uptime")
        return True, f"Process '{process_name}' online (PID {pid}, uptime_ts {uptime})"
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, FileNotFoundError, OSError) as exc:
        return False, f"PM2 inspection failure: {type(exc).__name__}: {exc}"


def main() -> int:
    print("--- VF-API PM2 RESTART & HEALTH POLLING PROBE ---")
    try:
        res_restart = subprocess.run(["pm2", "restart", "vf-api"], capture_output=True, text=True, timeout=10.0, check=False)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"❌ FAIL: PM2 restart execution failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    if res_restart.returncode != 0:
        print(f"❌ FAIL: PM2 restart returned exit code {res_restart.returncode}: {res_restart.stderr.strip()}", file=sys.stderr)
        return 1

    start_mono = time.monotonic()
    deadline = start_mono + 25.0
    attempt = 0
    online = False
    last_diag = ""

    while time.monotonic() < deadline:
        attempt += 1
        time.sleep(0.5)
        remaining = max(0.0, deadline - time.monotonic())
        http_timeout = min(2.0, remaining)
        if http_timeout <= 0.05:
            break
        ok, diag = check_health(timeout_sec=http_timeout)
        last_diag = diag or ""
        if ok:
            online = True
            elapsed = round(time.monotonic() - start_mono, 2)
            print(f"✅ VF_API_ONLINE confirmed on attempt {attempt} in {elapsed}s: {diag}")
            break

    if not online:
        elapsed = round(time.monotonic() - start_mono, 2)
        print(f"❌ FAIL: vf-api failed readiness predicate within 25.0s budget ({elapsed}s elapsed, last error: {last_diag})", file=sys.stderr)
        return 1

    pm2_ok, pm2_msg = verify_pm2_process_state("vf-api")
    if not pm2_ok:
        print(f"❌ FAIL: PM2 post-polling process state validation failed: {pm2_msg}", file=sys.stderr)
        return 1
    print(f"✅ PM2 Process State Verified: {pm2_msg}")

    res_status = subprocess.run(["pm2", "status", "vf-api"], capture_output=True, text=True, timeout=10.0, check=False)
    if res_status.returncode != 0:
        print(f"❌ FAIL: pm2 status returned exit code {res_status.returncode}: {res_status.stderr.strip()}", file=sys.stderr)
        return 1
    print(res_status.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
