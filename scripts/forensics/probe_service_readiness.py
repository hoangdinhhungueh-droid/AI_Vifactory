#!/usr/bin/env python3
"""scripts/forensics/probe_service_readiness.py — Fail-Closed FastAPI Service Readiness Probe (Rule 121 & Rule 139).
Restarts vf-api via PM2 and polls health endpoint with strict JSON parsing and a single monotonic 25.0s deadline
spanning PM2 restart, health polling with bounded body size, PM2 descriptor validation, and final status check.
Fails closed (exit code 1) on restart failure, budget expiration, or invalid process status.
"""

import json
import math
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional, Tuple

MAX_HEALTH_BODY_BYTES = 65536  # 64 KB safety bound against trickling or unbounded payloads
READINESS_OVERALL_BUDGET_SEC = 25.0


def check_health(
    url: str = "http://127.0.0.1:8000/api/v1/health",
    timeout_sec: float = 2.0,
    max_body_bytes: int = MAX_HEALTH_BODY_BYTES,
) -> Tuple[bool, Optional[str]]:
    """Polls health endpoint and validates parsed JSON status == 'ok' using standard socket transport
    governed by an absolute monotonic deadline covering connection, headers, and body read.
    Dynamically applies remaining monotonic deadline to every blocking operation.
    """
    call_start = time.monotonic()
    call_deadline = call_start + timeout_sec
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    try:
        rem_connect = call_deadline - time.monotonic()
        if rem_connect <= 0:
            return False, f"Initial deadline exhausted before connection ({timeout_sec}s budget)"

        sock = socket.create_connection((host, port), timeout=rem_connect)
        with sock:
            # Send HTTP request with Connection: close
            rem_send = call_deadline - time.monotonic()
            if rem_send <= 0:
                return False, f"Deadline exhausted before request transmission ({timeout_sec}s budget)"
            sock.settimeout(rem_send)
            req_data = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"User-Agent: VF-HealthProbe/1.0\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("utf-8")
            sock.sendall(req_data)

            # Read response chunks under monotonic deadline
            raw_chunks = []
            total_bytes = 0
            while True:
                rem_read = call_deadline - time.monotonic()
                if rem_read <= 0:
                    return False, f"Total body read duration exceeded timeout of {timeout_sec}s"
                sock.settimeout(rem_read)
                chunk = sock.recv(4096)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_body_bytes:
                    return False, f"Response body exceeded maximum bound of {max_body_bytes} bytes"
                raw_chunks.append(chunk)

            raw_bytes = b"".join(raw_chunks)
            if not raw_bytes:
                return False, "Empty HTTP response from server"

            header_bytes, sep, body_bytes = raw_bytes.partition(b"\r\n\r\n")
            if not sep:
                return False, "Malformed HTTP response: missing header/body separator"

            lines = header_bytes.split(b"\r\n")
            status_line = lines[0].decode("latin-1", errors="replace")
            status_parts = status_line.split(" ", 2)
            if len(status_parts) < 2 or not status_parts[1].isdigit():
                return False, f"Malformed HTTP status line: {status_line}"

            status_code = int(status_parts[1])
            if status_code != 200:
                return False, f"HTTP status {status_code}"

            body_str = body_bytes.decode("utf-8")
            data = json.loads(body_str)
            if isinstance(data, dict) and data.get("status") == "ok":
                return True, "status=ok"
            return False, f"Unexpected health payload: {data}"
    except (
        TimeoutError,
        socket.timeout,
        ConnectionResetError,
        ConnectionRefusedError,
        ConnectionAbortedError,
        BrokenPipeError,
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


def run_service_readiness_probe(
    restart_fn: Optional[Callable[[float], Tuple[int, str]]] = None,
    poll_fn: Optional[Callable[[float], Tuple[bool, str]]] = None,
    inspect_fn: Optional[Callable[[float], Tuple[bool, str]]] = None,
    status_fn: Optional[Callable[[float], Tuple[int, str]]] = None,
    cleanup_fn: Optional[Callable[[float], Tuple[int, str]]] = None,
    budget_sec: float = READINESS_OVERALL_BUDGET_SEC,
) -> int:
    """Executes the 6-phase fail-closed readiness probe bounded by budget_sec.
    Supports dependency injection of phase callables for hermetic lifecycle validation.
    Phases: 1. Restart, 2. Polling, 3. Inspect, 4. Status, 5. Cleanup, 6. Final monotonic completion.
    """
    print("--- VF-API PM2 RESTART & HEALTH POLLING PROBE ---")
    overall_start_mono = time.monotonic()
    overall_deadline = overall_start_mono + budget_sec

    # 1. PM2 Restart step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before PM2 restart ({now - overall_start_mono:.2f}s >= {budget_sec}s)", file=sys.stderr)
        return 1
    rem_restart = overall_deadline - now
    if restart_fn is not None:
        code_restart, out_restart = restart_fn(rem_restart)
    else:
        try:
            res_restart = subprocess.run(
                ["pm2", "restart", "vf-api"],
                capture_output=True,
                text=True,
                timeout=min(10.0, rem_restart),
                check=False,
            )
            code_restart = res_restart.returncode
            out_restart = res_restart.stderr.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            print(f"❌ FAIL: PM2 restart execution failed ({type(exc).__name__}): {exc}", file=sys.stderr)
            return 1

    if code_restart != 0:
        print(f"❌ FAIL: PM2 restart returned exit code {code_restart}: {out_restart}", file=sys.stderr)
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
        if poll_fn is not None:
            ok, diag = poll_fn(http_timeout)
        else:
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
            f"❌ FAIL: vf-api failed readiness predicate within {budget_sec}s budget "
            f"({elapsed}s elapsed, last error: {last_diag})",
            file=sys.stderr,
        )
        return 1

    # 3. PM2 Process State Inspection step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before PM2 inspection ({now - overall_start_mono:.2f}s >= {budget_sec}s)", file=sys.stderr)
        return 1
    rem_inspect = overall_deadline - now

    if inspect_fn is not None:
        pm2_ok, pm2_msg = inspect_fn(rem_inspect)
    else:
        pm2_ok, pm2_msg = verify_pm2_process_state("vf-api", timeout_sec=min(5.0, rem_inspect))

    if not pm2_ok:
        print(f"❌ FAIL: PM2 post-polling process state validation failed: {pm2_msg}", file=sys.stderr)
        return 1
    print(f"✅ PM2 Process State Verified: {pm2_msg}")

    # 4. Final PM2 Status step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before final pm2 status command ({now - overall_start_mono:.2f}s >= {budget_sec}s)", file=sys.stderr)
        return 1
    rem_status = overall_deadline - now

    if status_fn is not None:
        code_status, out_status = status_fn(rem_status)
    else:
        try:
            res_status = subprocess.run(
                ["pm2", "status", "vf-api"],
                capture_output=True,
                text=True,
                timeout=min(5.0, rem_status),
                check=False,
            )
            code_status = res_status.returncode
            out_status = res_status.stdout if code_status == 0 else res_status.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            print(f"❌ FAIL: pm2 status execution failed ({type(exc).__name__}): {exc}", file=sys.stderr)
            return 1

    if code_status != 0:
        print(f"❌ FAIL: pm2 status returned exit code {code_status}: {out_status.strip()}", file=sys.stderr)
        return 1
    print(out_status)

    # 5. Optional PM2/Readiness Cleanup step under overall budget
    now = time.monotonic()
    if now >= overall_deadline:
        print(f"❌ FAIL: Overall budget exhausted before cleanup ({now - overall_start_mono:.2f}s >= {budget_sec}s)", file=sys.stderr)
        return 1
    rem_cleanup = overall_deadline - now

    if cleanup_fn is not None:
        code_cleanup, out_cleanup = cleanup_fn(rem_cleanup)
        if code_cleanup != 0:
            print(f"❌ FAIL: PM2 cleanup execution failed with exit code {code_cleanup}: {out_cleanup}", file=sys.stderr)
            return 1

    # 6. Final unrounded monotonic budget verification across entire probe and completion
    finish_mono = time.monotonic()
    if finish_mono > overall_deadline:
        print(f"❌ FAIL: Overall readiness budget exceeded at completion ({finish_mono - overall_start_mono:.3f}s > {budget_sec}s)", file=sys.stderr)
        return 1

    total_elapsed = round(finish_mono - overall_start_mono, 2)
    print(f"✅ SERVICE READINESS PROBE PASSED: Completed in {total_elapsed}s (within {budget_sec}s budget)")
    return 0


def main() -> int:
    return run_service_readiness_probe()


if __name__ == "__main__":
    sys.exit(main())
