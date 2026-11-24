#!/usr/bin/env python3
"""scripts/download_vps_asset.py — Multi-endpoint parallel chunked downloader from Hetzner VPS."""

import base64
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.vps_runner import ENDPOINTS, FastVPSClient, get_client


def _make_worker_session(ep_idx: int, verify_tls: bool):
    client = FastVPSClient(endpoint_idx=ep_idx, auto_connect=True)
    ep = client.ep
    sess = requests.Session()
    adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    headers = {
        "Authorization": f"Bearer {ep['token']}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0",
    }
    if ep.get("cf_id"):
        headers["CF-Access-Client-Id"] = ep["cf_id"]
    if ep.get("cf_secret"):
        headers["CF-Access-Client-Secret"] = ep["cf_secret"]
    return {
        "client": client,
        "url": ep["url"],
        "session": sess,
        "headers": headers,
        "session_id": client.session_id,
        "lock": threading.Lock(),
        "verify_tls": verify_tls,
    }


def download_file_chunked(
    vps_path: str,
    local_path: str,
    chunk_size: int = 5997,
    max_workers: int = 16,
) -> bool:
    """Downloads a file from VPS using parallel independent sessions across available endpoints."""
    # MCP run_command truncates stdout at 8000 chars; 5997 raw bytes = 7996 base64 chars.
    eff_chunk = min(max(int(chunk_size), 1024), 5997)
    # Keep multiple of 3 for clean base64 alignment
    eff_chunk = eff_chunk - (eff_chunk % 3)

    client = get_client()
    meta_res = client.run_command(
        f"test -f '{vps_path}' && stat -c %s '{vps_path}' && sha256sum '{vps_path}' | awk '{{print $1}}'"
    )
    lines = [ln.strip() for ln in (meta_res.get("stdout") or "").splitlines() if ln.strip()]
    if len(lines) < 1 or not lines[0].isdigit():
        print(f"[download_vps_asset] Cannot stat remote file {vps_path}: {meta_res}", flush=True)
        return False

    total_size = int(lines[0])
    remote_sha = lines[1] if len(lines) > 1 and len(lines[1]) == 64 else None
    print(
        f"[download_vps_asset] Downloading {vps_path} ({total_size:,} bytes) -> {local_path} "
        f"(chunk={eff_chunk}, workers={max_workers})...",
        flush=True,
    )

    if total_size == 0:
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        Path(local_path).write_bytes(b"")
        return True

    verify_tls = os.getenv("ALLOW_INSECURE_TLS", "").lower() not in ("1", "true", "yes")
    num_eps = max(1, len(ENDPOINTS))
    with ThreadPoolExecutor(max_workers=max_workers) as init_pool:
        worker_pool = list(
            init_pool.map(lambda idx: _make_worker_session(idx % num_eps, verify_tls), range(max_workers))
        )

    chunks = []
    req_id = 1000
    for idx, offset in enumerate(range(0, total_size, eff_chunk)):
        read_len = min(eff_chunk, total_size - offset)
        req_id += 1
        chunks.append((idx, offset, read_len, req_id))

    def fetch_one(item):
        idx, offset, read_len, r_id = item
        w = worker_pool[idx % len(worker_pool)]
        cmd = f"tail -c +{offset + 1} '{vps_path}' | head -c {read_len} | base64 -w 0"
        payload = {
            "jsonrpc": "2.0",
            "id": r_id,
            "method": "tools/call",
            "params": {"name": "run_command", "arguments": {"command": cmd, "confirm": True, "timeout": 30}},
        }
        last_err = None
        for attempt in range(5):
            with w["lock"]:
                headers = dict(w["headers"])
                if w["session_id"]:
                    headers["mcp-session-id"] = w["session_id"]
                try:
                    resp = w["session"].post(
                        w["url"],
                        json=payload,
                        headers=headers,
                        timeout=35,
                        verify=w["verify_tls"],
                    )
                    if resp.status_code in (400, 404, 410):
                        w["session_id"] = w["client"].init_session()
                        continue
                    resp.raise_for_status()
                    for line in resp.text.splitlines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            content = data.get("result", {}).get("content", [])
                            if content:
                                ret = json.loads(content[0].get("text", "{}"))
                                b64_str = (ret.get("stdout") or "").strip()
                                if b64_str:
                                    raw = base64.b64decode(b64_str)
                                    if len(raw) == read_len:
                                        return offset, raw
                                    last_err = ValueError(f"Expected {read_len}B, got {len(raw)}B")
                except Exception as exc:
                    last_err = exc
            time.sleep(0.3 * (attempt + 1))
        raise RuntimeError(f"Failed chunk offset={offset} len={read_len}: {last_err}")

    os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
    tmp_path = f"{local_path}.part"
    write_lock = threading.Lock()
    t0 = time.time()
    completed = 0
    total_chunks = len(chunks)

    with open(tmp_path, "wb") as out_f:
        out_f.truncate(total_size)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(fetch_one, c) for c in chunks]
            for fut in as_completed(futures):
                offset, raw = fut.result()
                with write_lock:
                    out_f.seek(offset)
                    out_f.write(raw)
                completed += 1
                if completed % 250 == 0 or completed == total_chunks:
                    elapsed = max(0.1, time.time() - t0)
                    pct = (completed / total_chunks) * 100.0
                    kbps = (completed * eff_chunk) / 1024.0 / elapsed
                    print(
                        f"   [{pct:5.1f}%] {completed}/{total_chunks} chunks ({kbps:.1f} KB/s)",
                        flush=True,
                    )

    for w in worker_pool:
        try:
            w["session"].close()
            w["client"].close()
        except Exception:
            pass

    if os.path.exists(local_path):
        os.replace(tmp_path, local_path)
    else:
        os.rename(tmp_path, local_path)

    if remote_sha:
        h = hashlib.sha256()
        with open(local_path, "rb") as f:
            while True:
                blk = f.read(65536)
                if not blk:
                    break
                h.update(blk)
        local_sha = h.hexdigest()
        if local_sha != remote_sha:
            print(f"[download_vps_asset] SHA256 mismatch! remote={remote_sha} local={local_sha}", flush=True)
            return False
        print(f"[download_vps_asset] Verified SHA256={local_sha[:16]}... ({os.path.getsize(local_path):,} bytes)", flush=True)

    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/download_vps_asset.py <vps_path> <local_path>")
        sys.exit(1)
    success = download_file_chunked(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
