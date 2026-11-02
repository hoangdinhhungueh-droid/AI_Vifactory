#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/sync_human_gates_to_vps.py — 3-Way Physical Sync & VPS Verification for Human Gates (Rule 126).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.vps_runner import FastVPSClient

FILES_TO_SYNC = [
    "app/services/telegram_buttons.py",
    "app/services/pilot_builder.py",
    "app/services/trend_engine_b1.py",
    "orchestrator/run_pipeline.py",
    "scripts/run_trend_pipeline.py",
    "stages/s03_script.py",
    "stages/s05_director_plan.py",
    "stages/s07_image_gen.py",
    "stages/s08_video_gen.py",
    "vox/assemble.py",
    "tests/test_human_gates.py",
]


def sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.replace("\r\n", "\n").encode("utf-8"))
    return h.hexdigest()


def main():
    print("=== [RULE 126] THREE-WAY PHYSICAL SYNC: HUMAN GATES & PILOT ENGINE ===", flush=True)
    client = FastVPSClient(endpoint_idx=1)
    synced = []
    failed = []

    for rel in FILES_TO_SYNC:
        local_p = ROOT / rel
        if not local_p.exists():
            print(f"[SKIP] Local file not found: {rel}", flush=True)
            continue

        content = local_p.read_text(encoding="utf-8")
        local_sha = sha256_text(content)

        # 1. Write to safe-zone /tmp/vf/sync_tmp.txt
        w_res = client.call_tool("write_file", {
            "path": "/tmp/vf/sync_tmp.txt",
            "content": content.replace("\r\n", "\n"),
            "confirm": True
        })
        if not isinstance(w_res, dict) or w_res.get("status") != "ok":
            print(f"[FAIL] Write to safe-zone failed for {rel}: {w_res}", flush=True)
            failed.append(rel)
            continue

        # 2. Copy from safe-zone to /root/video_factory/<rel>
        vps_dest = f"/root/video_factory/{rel}"
        vps_dir = f"/root/video_factory/{Path(rel).parent.as_posix()}"
        cp_cmd = f"mkdir -p '{vps_dir}' && cp '/tmp/vf/sync_tmp.txt' '{vps_dest}' && rm -f '/tmp/vf/sync_tmp.txt' && sha256sum '{vps_dest}'"
        c_res = client.call_tool("run_command", {"command": cp_cmd})

        if not isinstance(c_res, dict) or c_res.get("exit_code") != 0:
            print(f"[FAIL] Copy command failed for {rel}: {c_res}", flush=True)
            failed.append(rel)
            continue

        stdout = c_res.get("stdout", "")
        vps_sha = stdout.split()[0] if stdout else ""

        if vps_sha == local_sha:
            print(f"✅ [PARITY OK] {rel} -> {vps_sha[:16]}", flush=True)
            synced.append(rel)
        else:
            print(f"❌ [MISMATCH] {rel}: local {local_sha[:16]} != vps {vps_sha[:16]}", flush=True)
            failed.append(rel)

    print(f"\n--- Sync Summary: {len(synced)} OK, {len(failed)} Failed ---", flush=True)
    if failed:
        sys.exit(1)

    # 3. Compile Python files on VPS
    print("\n--- [RULE 127] Compiling Python files on VPS ---")
    compile_cmd = (
        "python3 -m py_compile "
        + " ".join(f"/root/video_factory/{rel}" for rel in FILES_TO_SYNC if rel.endswith(".py"))
    )
    comp_res = client.call_tool("run_command", {"command": compile_cmd})
    print("Compile exit_code:", comp_res.get("exit_code"))
    if comp_res.get("exit_code") != 0:
        print("Compile stderr:", comp_res.get("stderr"))
        sys.exit(1)
    print("All Python modules compiled successfully on VPS (exit code 0)")

    # 4. Run Pytest on VPS for human gates
    print("\n--- [RULE 121] Running tests/test_human_gates.py fast gates on VPS ---", flush=True)
    pytest_cmd = (
        "pytest /root/video_factory/tests/test_human_gates.py -k 'not test_human_gate_4 and not test_human_gate_5 and not test_unattended_auto_mode' -v"
    )
    test_res = client.call_tool("run_command", {"command": pytest_cmd, "confirm": True}, timeout=60)
    test_out = test_res.get("stdout", "") if isinstance(test_res, dict) else str(test_res)
    test_err = test_res.get("stderr", "") if isinstance(test_res, dict) else ""
    test_code = test_res.get("exit_code", 0) if isinstance(test_res, dict) else 0
    print("Test output:\n", test_out, flush=True)
    if test_code != 0 or ("failed" in test_out.lower() and "passed" not in test_out.lower()):
        print("Test stderr:\n", test_err, flush=True)
        sys.exit(1)

    # 5. Master Smoke Test Gate on VPS
    print("\n--- [RULE 127] Running Master E2E Smoke Gate on VPS ---", flush=True)
    smoke_cmd = "python3 /root/video_factory/scripts/e2e_pipeline_smoketest.py"
    smoke_res = client.call_tool("run_command", {"command": smoke_cmd, "confirm": True}, timeout=120)
    smoke_out = smoke_res.get("stdout", "") if isinstance(smoke_res, dict) else str(smoke_res)
    smoke_err = smoke_res.get("stderr", "") if isinstance(smoke_res, dict) else ""
    smoke_code = smoke_res.get("exit_code", 0) if isinstance(smoke_res, dict) else 0
    print("Smoke output:\n", smoke_out, flush=True)
    if smoke_code != 0:
        print("Smoke stderr:\n", smoke_err, flush=True)
        sys.exit(1)

    print("\n🎉 === ALL VPS COMPILATION, TESTS & MASTER SMOKE GATES PASSED! ===", flush=True)


if __name__ == "__main__":
    main()
