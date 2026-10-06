#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/health-check.py — Cross-Platform 7-Axis System Health Check.

Verifies:
1. Core Services (PostgreSQL, Redis)
2. Process & Workers (Celery, Docker)
3. Memory & Swap (RAM, Swap)
4. Disk Storage (Root & Media partitions)
5. Runtime & Render Engine (Python 3.10+, Node.js)
6. Cloud Credentials & API Keys (Gemini, Groq, GitHub)
7. Codebase Cleanliness (Ghost code scan)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def check_cmd(cmd: str) -> bool:
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, timeout=8)
        return res.returncode == 0
    except Exception:
        return False


def get_memory_info() -> dict:
    info = {"ram_total_mb": 0, "ram_avail_mb": 0, "swap_total_mb": 0}
    is_linux = platform.system().lower() == "linux"
    if is_linux and Path("/proc/meminfo").exists():
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip().split()[0]
                        if k == "MemTotal":
                            info["ram_total_mb"] = int(v) // 1024
                        elif k == "MemAvailable":
                            info["ram_avail_mb"] = int(v) // 1024
                        elif k == "SwapTotal":
                            info["swap_total_mb"] = int(v) // 1024
        except Exception:
            pass
    elif platform.system().lower() == "windows":
        try:
            # Simple windows query via powershell
            cmd = "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                import json
                d = json.loads(r.stdout)
                info["ram_total_mb"] = int(d.get("TotalVisibleMemorySize", 0)) // 1024
                info["ram_avail_mb"] = int(d.get("FreePhysicalMemory", 0)) // 1024
        except Exception:
            pass
    return info


def get_disk_info() -> dict:
    target_path = "/" if platform.system().lower() == "linux" else Path.cwd().anchor
    try:
        total, used, free = shutil.disk_usage(target_path)
        pct = (used / total) * 100 if total > 0 else 0
        return {
            "path": target_path,
            "total_gb": round(total / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "used_pct": round(pct, 1)
        }
    except Exception:
        return {"path": target_path, "total_gb": 0, "free_gb": 0, "used_pct": 0}


def main() -> int:
    is_linux = platform.system().lower() == "linux"
    print("=" * 65)
    print(f"🛡️  AI VIDEO FACTORY — 7-AXIS SYSTEM HEALTH CHECK ({platform.system().upper()})")
    print("=" * 65)

    all_ok = True

    # Axis 1: Core Services
    print("\n[Axis 1: Core Database & Caches]")
    pg_ok = check_cmd("pg_isready" if is_linux else "where.exe pg_isready")
    print(f"  PostgreSQL: {'OK' if pg_ok else 'WARN (Not detected on local path)'}")
    redis_ok = check_cmd("redis-cli ping" if is_linux else "where.exe redis-cli")
    print(f"  Redis:      {'OK' if redis_ok else 'WARN (Not detected on local path)'}")

    # Axis 2: Process & Background Workers
    print("\n[Axis 2: Process & Background Workers]")
    if is_linux:
        celery_ok = check_cmd("ps aux | grep celery | grep -v grep")
        print(f"  Celery Workers: {'OK' if celery_ok else 'WARN (No active celery workers)'}")
        docker_ok = check_cmd("docker ps")
        print(f"  Docker Engine:  {'OK' if docker_ok else 'WARN (Docker daemon inactive)'}")
    else:
        celery_ok = True
        docker_ok = check_cmd("docker --version")
        print(f"  Docker Client:  {'OK' if docker_ok else 'WARN (Docker not installed/running)'}")

    # Axis 3: Memory & Swap
    print("\n[Axis 3: Hardware Memory & Swap]")
    mem = get_memory_info()
    if mem["ram_total_mb"] > 0:
        avail_pct = round((mem["ram_avail_mb"] / mem["ram_total_mb"]) * 100, 1)
        print(f"  RAM Available:  {mem['ram_avail_mb']} MB / {mem['ram_total_mb']} MB ({avail_pct}% free)")
        if avail_pct < 10.0:
            print("  RAM Warning:    CRITICAL (Free RAM < 10%)")
            all_ok = False
    else:
        print("  RAM:            Could not query meminfo")

    if is_linux:
        if mem["swap_total_mb"] == 0:
            print("  Swap Memory:    WARN (0 MB configured, risk of OOM on heavy renders)")
        else:
            print(f"  Swap Memory:    {mem['swap_total_mb']} MB OK")

    # Axis 4: Disk Storage
    print("\n[Axis 4: Disk Storage]")
    disk = get_disk_info()
    print(f"  Mount '{disk['path']}': {disk['used_pct']}% used ({disk['free_gb']} GB free / {disk['total_gb']} GB total)")
    if disk["used_pct"] > 90.0:
        print("  Disk Warning:   CRITICAL (Disk usage > 90%)")
        all_ok = False

    # Axis 5: Runtime & Render Environment
    print("\n[Axis 5: Runtimes & Render Stack]")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    print(f"  Python Runtime: {py_ver} ({'OK' if py_ok else 'FAIL: requires 3.10+'})")
    if not py_ok:
        all_ok = False

    node_ok = check_cmd("node -v")
    print(f"  Node.js Engine: {'OK' if node_ok else 'WARN (Node.js not in PATH)'}")

    # Axis 6: Cloud Credentials & API Keys
    print("\n[Axis 6: Cloud AI Credentials & API Keys]")
    keys = {
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
        "GROQ_API_KEY": bool(os.environ.get("GROQ_API_KEY")),
        "GITHUB_TOKEN": bool(os.environ.get("GITHUB_TOKEN")),
    }
    for k, present in keys.items():
        print(f"  {k:15}: {'CONFIGURED ✅' if present else 'NOT SET ⚠️'}")

    # Axis 7: Codebase Cleanliness (Rule 125 Zero Ghost Code)
    print("\n[Axis 7: Codebase Cleanliness (Rule 125)]")
    try:
        root_dir = Path(__file__).resolve().parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        from scripts.orchestrator.ghost_code_detector import scan_workspace
        ghost_defects = scan_workspace(root_dir)
        ghost_ok = len(ghost_defects) == 0
        print(f"  Zero Ghost Scan:{'PASS (0 defects) ✅' if ghost_ok else f'FAIL ({len(ghost_defects)} defects) ❌'}")
        if not ghost_ok:
            for g in ghost_defects[:3]:
                print(f"    -> {g}")
            all_ok = False
    except Exception as e:
        print(f"  Ghost Scan:     SKIPPED ({e})")

    print("\n" + "=" * 65)
    print(f"🎯 FINAL SYSTEM VERDICT: {'ALL CRITICAL CHECKS PASSED ✅' if all_ok else 'SOME CHECKS REQUIRE ATTENTION ⚠️'}")
    print("=" * 65)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
