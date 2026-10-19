#!/usr/bin/env python3
"""scripts/forensics/probe_service_readiness.py — Fail-Closed FastAPI Service Readiness Probe (Rule 121 & Rule 139).
Restarts vf-api via PM2 and polls health endpoint with strict JSON parsing and a single monotonic 25.0s deadline
spanning PM2 restart, health polling with bounded body size, PM2 descriptor validation, and final status check.
Fails closed (exit code 1) on restart failure, budget expiration, or invalid process status.
"""

import http.client
import json
import math
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple

MAX_HEALTH_BODY_BYTES = 65536  # 64 KB safety bound against trickling or unbounded payloads
READINESS_OVERALL_BUDGET_SEC = 25.0


def check_health(
    url: str = "http://127.0.0.1:8000/api/v1/health",
    timeout_sec: float = 2.0,
    max_body_bytes: int = MAX_HEALTH_BODY_BYTES,
) -> Tuple[bool, Optional[str]]:
    """Polls health endpoint and validates parsed JSON status == 'ok' with chunked bounded body read
    governed by an absolute monotonic read duration ceiling and comprehensive transport exception handling.
    """
    call_start = time.monotonic()
    call_deadline = call_start + timeout_sec
    req = urllib.request.Request(url, headers={"User-Agent": "VF-HealthProbe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status != 200:
                return False, f"HTTP status {resp.status}"

            chunks = []
            total_read = 0
            chunk_size = 4096
            while True:
                if time.monotonic() >= call_deadline:
                    return False, f"Total body read duration exceeded timeout of {timeout_sec}s"
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                total_read += len(chunk)
                if total_read > max_body_bytes:
                    return False, f"Response body exceeded maximum bound of {max_body_bytes} bytes"
                chunks.append(chunk)

            body_str = b"".join(chunks).decode("utf-8")
            data = json.loads(body_str)
            if isinstance(data, dict) and data.get("status") == "ok":
                return True, "status=ok"
            return False, f"Unexpected health payload: {data}"
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ConnectionResetError,
        ConnectionRefusedError,
        http.client.IncompleteRead,
        http.client.HTTPException,
        socket.timeout,
        json.JSONDecodeError,
        UnicodeDecodeError,
        OSError,
    ) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def verify_pm2_process_state(
    process_name: str = "vf-api",
    timeout_sec: float = 10.0,
    raw_inventory_json: Optional[str] = None,
) -> Tuple[bool, str]:
    """Inspects PM2 process state ensuring process is active, unique, online, with positive non-boolean PID and finite valid uptime."""
    try:
        if raw_inventory_json is None:
            res = subprocess.run(
                ["pm2", "jlist"],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            if res.returncode != 0:
                return False, f"pm2 jlist failed with exit code {res.returncode}: {res.stderr.strip()}"
            raw_text = res.stdout
        else:
            raw_text = raw_inventory_json

        procs = json.loads(raw_text)
        if not isinstance(procs, list):
            return False, f"PM2 process inventory must be a JSON list, got {type(procs).__name__}"

        matching = [p for p in procs if isinstance(p, dict) and p.get("name") == process_name]
        if len(matching) == 0:
            return False, f"Process '{process_name}' not found in PM2 process inventory"
        if len(matching) > 1:
            return False, f"Ambiguous PM2 state: multiple ({len(matching)}) processes named '{process_name}'"

        target = matching[0]
        pm2_env = target.get("pm2_env")
        if not isinstance(pm2_env, dict):
            return False, f"Process '{process_name}' pm2_env must be a dictionary, got {type(pm2_env).__name__}"

        status = pm2_env.get("status")
        if status != "online":
            return False, f"Process '{process_name}' status is '{status}', expected 'online'"

        pid = target.get("pid")
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            return False, f"Invalid PID {pid!r} for process '{process_name}': expected positive non-boolean integer"

        uptime = pm2_env.get("pm_uptime")
        if (
            isinstance(uptime, bool)
            or not isinstance(uptime, (int, float))
            or not math.isfinite(uptime)
            or uptime <= 0
        ):
            return False, f"Invalid uptime {uptime!r} for process '{process_name}': expected finite positive numeric timestamp"

        return True, f"Process '{process_name}' online (PID {pid}, uptime_ts {uptime})"
    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        KeyError,
        FileNotFoundError,
        OSError,
    ) as exc:
        return False, f"PM2 inspection failure: {type(exc).__name__}: {exc}"


def main() -> int:
    print("--- VF-API PM2 RESTART & HEALTH POLLING PROBE ---")
    overall_start_mono = time.monotonic()
    overall_deadline = overall_start_mono + READINESS_OVERALL_BUDGET_SEC

    # 1. PM2 Restart step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before PM2 restart ({now - overall_start_mono:.2f}s >= {READINESS_OVERALL_BUDGET_SEC}s)", file=sys.stderr)
        return 1
    rem_restart = overall_deadline - now
    try:
        res_restart = subprocess.run(
            ["pm2", "restart", "vf-api"],
            capture_output=True,
            text=True,
            timeout=min(10.0, rem_restart),
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"❌ FAIL: PM2 restart execution failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    if res_restart.returncode != 0:
        print(f"❌ FAIL: PM2 restart returned exit code {res_restart.returncode}: {res_restart.stderr.strip()}", file=sys.stderr)
        return 1

    # 2. HTTP Polling step under overall budget
    attempt = 0
    online = False
    last_diag = ""

    while time.monotonic() < overall_deadline:
        attempt += 1
        time.sleep(0.5)
        now = time.monotonic()
        if now >= overall_deadline:
            break
        remaining = overall_deadline - now
        http_timeout = min(2.0, remaining)
        if http_timeout <= 0.05:
            break
        ok, diag = check_health(timeout_sec=http_timeout)
        last_diag = diag or ""
        if ok:
            online = True
            elapsed = round(time.monotonic() - overall_start_mono, 2)
            print(f"✅ VF_API_ONLINE confirmed on attempt {attempt} in {elapsed}s: {diag}")
            break

    if not online:
        elapsed = round(time.monotonic() - overall_start_mono, 2)
        print(
            f"❌ FAIL: vf-api failed readiness predicate within {READINESS_OVERALL_BUDGET_SEC}s budget "
            f"({elapsed}s elapsed, last error: {last_diag})",
            file=sys.stderr,
        )
        return 1

    # 3. PM2 Process State Inspection step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before PM2 inspection ({now - overall_start_mono:.2f}s >= {READINESS_OVERALL_BUDGET_SEC}s)", file=sys.stderr)
        return 1
    rem_inspect = overall_deadline - now

    pm2_ok, pm2_msg = verify_pm2_process_state("vf-api", timeout_sec=min(5.0, rem_inspect))
    if not pm2_ok:
        print(f"❌ FAIL: PM2 post-polling process state validation failed: {pm2_msg}", file=sys.stderr)
        return 1
    print(f"✅ PM2 Process State Verified: {pm2_msg}")

    # 4. Final PM2 Status step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before final pm2 status command ({now - overall_start_mono:.2f}s >= {READINESS_OVERALL_BUDGET_SEC}s)", file=sys.stderr)
        return 1
    rem_status = overall_deadline - now

    try:
        res_status = subprocess.run(
            ["pm2", "status", "vf-api"],
            capture_output=True,
            text=True,
            timeout=min(5.0, rem_status),
            check=False,
        )
        if res_status.returncode != 0:
            print(f"❌ FAIL: pm2 status returned exit code {res_status.returncode}: {res_status.stderr.strip()}", file=sys.stderr)
            return 1
        print(res_status.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        print(f"❌ FAIL: pm2 status execution failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1

    # 5. Final unrounded monotonic budget verification
    finish_mono = time.monotonic()
    if finish_mono > overall_deadline:
        print(f"❌ FAIL: Overall readiness budget exceeded ({finish_mono - overall_start_mono:.3f}s > {READINESS_OVERALL_BUDGET_SEC}s)", file=sys.stderr)
        return 1

    total_elapsed = round(finish_mono - overall_start_mono, 2)
    print(f"✅ SERVICE READINESS PROBE PASSED: Completed in {total_elapsed}s (within {READINESS_OVERALL_BUDGET_SEC}s budget)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
