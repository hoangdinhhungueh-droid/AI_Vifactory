#!/usr/bin/env python3
"""scripts/forensics/probe_fastapi_http.py
Authoritative HTTP verification probe for FastAPI endpoints.
Complies with Rule 118 (Zero-Mock), Rule 121 (Forensic Verification Protocol),
and Boss Round 3 Supervisory Audit requirements.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def resolve_token() -> str:
    """Resolves VF_API_TOKEN from environment or approved secret locations without fallback."""
    token = os.getenv("VF_API_TOKEN", "").strip()
    if token:
        return token

    secret_paths = [
        Path("/root/secrets/.env"),
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for sp in secret_paths:
        if sp.exists():
            try:
                for line in sp.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("VF_API_TOKEN="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except (OSError, UnicodeDecodeError) as e:
                sys.stderr.write(f"[probe_fastapi_http] Notice: unable to read {sp}: {e}\n")
                continue
    return ""


def main() -> int:
    base_url = os.getenv("VF_API_BASE_URL", "").strip()
    if not base_url:
        print("CRITICAL: VF_API_BASE_URL is mandatory and missing from environment (fail-closed, Rule 118 & 121).", file=sys.stderr)
        return 1

    expected_sha = os.getenv("EXPECTED_GIT_SHA", "").strip()
    if not expected_sha:
        print("CRITICAL: EXPECTED_GIT_SHA environment variable is mandatory and missing (fail-closed, Rule 118 & 121).", file=sys.stderr)
        return 1

    token = resolve_token()
    if not token:
        print("CRITICAL: VF_API_TOKEN not found in environment or secrets file.", file=sys.stderr)
        return 1

    headers_auth = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    failures = []

    print("======================================================================")
    print("🔒 FASTAPI AUTHENTICATED RUNTIME ENDPOINT PROBES (Rule 121)")
    print(f"   Expected Audited Git SHA: {expected_sha}")
    print("======================================================================")

    # 1. Authenticated GET endpoints (must all return HTTP 200)
    auth_get_endpoints = [
        "/api/v1/health",
        "/api/v1/diag",
        "/v1/models",
        "/v1/budget",
        "/metrics",
    ]

    for ep in auth_get_endpoints:
        url = f"{base_url}{ep}"
        try:
            req = urllib.request.Request(url, headers=headers_auth)
            resp = urllib.request.urlopen(req, timeout=15)
            code = resp.getcode()
            if code != 200:
                failures.append(f"Auth GET {ep} expected 200, got {code}")
            else:
                body = resp.read().decode("utf-8", errors="replace")
                if ep == "/api/v1/health":
                    h_json = json.loads(body)
                    sha = h_json.get("git_sha", "MISSING")
                    if sha == "MISSING" or not sha:
                        failures.append(f"Auth GET {ep} missing git_sha in response payload: {body}")
                    elif sha != expected_sha:
                        failures.append(f"Auth GET {ep} git_sha mismatch: expected exact '{expected_sha}', got '{sha}'")
                    else:
                        print(f"  [PASS] {ep:20} -> HTTP 200 OK | git_sha={sha} (exact match with EXPECTED_GIT_SHA)")
                elif ep == "/metrics":
                    print(f"  [PASS] {ep:20} -> HTTP 200 OK | Prometheus metrics ({len(body)} bytes)")
                else:
                    print(f"  [PASS] {ep:20} -> HTTP 200 OK")
        except Exception as e:
            failures.append(f"Auth GET {ep} raised: {e}")

    # 2. Authenticated POST /api/v1/llm (must return HTTP 200)
    llm_payload = json.dumps({"prompt": "ping"}).encode("utf-8")
    llm_ok = False
    last_llm_err = None
    for attempt in range(1, 3):
        try:
            req_llm = urllib.request.Request(f"{base_url}/api/v1/llm", data=llm_payload, headers=headers_auth)
            resp_llm = urllib.request.urlopen(req_llm, timeout=90)
            code_llm = resp_llm.getcode()
            if code_llm != 200:
                last_llm_err = f"Auth POST /api/v1/llm expected 200, got {code_llm}"
            else:
                print(f"  [PASS] {'/api/v1/llm':20} -> HTTP 200 OK (payload: ping)")
                llm_ok = True
                break
        except Exception as e:
            last_llm_err = f"Auth POST /api/v1/llm raised: {e}"
            if attempt < 2:
                import time as _t
                _t.sleep(2)
    if not llm_ok and last_llm_err:
        failures.append(last_llm_err)

    # 3. Authenticated POST /v1/chat/completions (tool-calling dispatch)
    chat_payload = json.dumps({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Query Notion database"}],
        "tools": [{"type": "function", "function": {"name": "API-query-data-source", "parameters": {"type": "object"}}}],
    }).encode("utf-8")
    chat_ok = False
    last_chat_err = None
    for attempt in range(1, 3):
        try:
            req_chat = urllib.request.Request(f"{base_url}/v1/chat/completions", data=chat_payload, headers=headers_auth)
            resp_chat = urllib.request.urlopen(req_chat, timeout=90)
            if resp_chat.getcode() == 200:
                print(f"  [PASS] {'/v1/chat/completions':20} -> HTTP 200 OK")
                chat_ok = True
                break
            else:
                last_chat_err = f"Auth POST /v1/chat/completions expected HTTP 200, got {resp_chat.getcode()}"
        except urllib.error.HTTPError as he:
            last_chat_err = f"Auth POST /v1/chat/completions failed with HTTP {he.code}: {he.reason}"
            if attempt < 2:
                import time as _t
                _t.sleep(2)
        except Exception as e:
            last_chat_err = f"Auth POST /v1/chat/completions raised: {e}"
            if attempt < 2:
                import time as _t
                _t.sleep(2)
    if not chat_ok and last_chat_err:
        failures.append(last_chat_err)

    print("\n======================================================================")
    print("🛡️ FASTAPI UNAUTHENTICATED SECURITY BOUNDARY PROBES (Rule 121 & Rule 139)")
    print("======================================================================")

    # 4. Unauthenticated probes: protected endpoints MUST return HTTP 401
    unauth_protected_endpoints = [
        ("/api/v1/diag", "GET", None),
        ("/v1/budget", "GET", None),
        ("/api/v1/llm", "POST", json.dumps({"prompt": "ping"}).encode("utf-8")),
        ("/v1/chat/completions", "POST", json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode("utf-8")),
    ]

    for ep, method, data in unauth_protected_endpoints:
        url = f"{base_url}{ep}"
        headers_unauth = {"Content-Type": "application/json"}
        try:
            req = urllib.request.Request(url, data=data, headers=headers_unauth, method=method)
            resp = urllib.request.urlopen(req, timeout=15)
            failures.append(f"Security violation: Unauth {method} {ep} returned HTTP {resp.getcode()} instead of 401")
        except urllib.error.HTTPError as he:
            if he.code == 401:
                print(f"  [PASS] Unauth {method:4} {ep:22} -> HTTP 401 Unauthorized (Security Gate Active)")
            else:
                failures.append(f"Unauth {method} {ep} expected 401, got HTTP {he.code}")
        except Exception as e:
            failures.append(f"Unauth {method} {ep} unexpected error: {e}")

    # 5. Public endpoints (models discovery & health check)
    public_endpoints = [
        ("/v1/models", "GET"),
        ("/api/v1/health", "GET"),
    ]
    for ep, method in public_endpoints:
        try:
            req_pub = urllib.request.Request(f"{base_url}{ep}")
            resp_pub = urllib.request.urlopen(req_pub, timeout=15)
            if resp_pub.getcode() == 200:
                body = resp_pub.read().decode("utf-8", errors="replace")
                if ep == "/api/v1/health":
                    h_json = json.loads(body)
                    sha = h_json.get("git_sha", "MISSING")
                    if sha == "MISSING" or not sha:
                        failures.append(f"Public GET {ep} missing git_sha in response payload: {body}")
                    elif sha != expected_sha:
                        failures.append(f"Public GET {ep} git_sha mismatch: expected exact '{expected_sha}', got '{sha}'")
                    else:
                        print(f"  [PASS] Public {method:4} {ep:22} -> HTTP 200 OK | git_sha={sha} (exact match with EXPECTED_GIT_SHA)")
                else:
                    print(f"  [PASS] Public {method:4} {ep:22} -> HTTP 200 OK (Public Discovery Endpoint)")
            else:
                failures.append(f"Public {method} {ep} expected 200, got HTTP {resp_pub.getcode()}")
        except Exception as e:
            failures.append(f"Public {method} {ep} raised: {e}")

    print("======================================================================")
    if failures:
        print(f"❌ PROBE VERIFICATION FAILED ({len(failures)} defects):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("✅ ALL FASTAPI RUNTIME & SECURITY BOUNDARY PROBES PASSED (Exit code 0)")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
