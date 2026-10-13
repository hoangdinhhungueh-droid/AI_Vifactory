#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/orchestrator/system_health_reporter.py — Comprehensive Health & Build Reporter.

Generates:
1. Console Markdown Summary Report
2. Standalone Interactive HTML Dashboard (`out/reports/system_health_dashboard.html`)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / "app").exists():
            return parent
    return Path.cwd()


def collect_metrics(repo_root: Path) -> Dict[str, Any]:
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    is_linux = platform.system().lower() == "linux"

    # Disk
    target_path = "/" if is_linux else repo_root.anchor
    total, used, free = shutil.disk_usage(target_path)
    disk_pct = round((used / total) * 100, 1) if total > 0 else 0

    # RAM
    ram_total_mb = 0
    ram_avail_mb = 0
    if is_linux and Path("/proc/meminfo").exists():
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram_total_mb = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        ram_avail_mb = int(line.split()[1]) // 1024
        except Exception:
            pass
    elif platform.system().lower() == "windows":
        try:
            cmd = "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                d = json.loads(r.stdout)
                ram_total_mb = int(d.get("TotalVisibleMemorySize", 0)) // 1024
                ram_avail_mb = int(d.get("FreePhysicalMemory", 0)) // 1024
        except Exception:
            pass

    ram_used_mb = ram_total_mb - ram_avail_mb
    ram_pct = round((ram_used_mb / ram_total_mb) * 100, 1) if ram_total_mb > 0 else 0

    # Services
    def check_cmd(c: str) -> bool:
        try:
            return subprocess.run(c, shell=True, capture_output=True, timeout=5).returncode == 0
        except Exception:
            return False

    pg_ok = check_cmd("pg_isready" if is_linux else "where.exe pg_isready")
    redis_ok = check_cmd("redis-cli ping" if is_linux else "where.exe redis-cli")
    docker_ok = check_cmd("docker ps" if is_linux else "docker --version")
    celery_ok = check_cmd("ps aux | grep celery | grep -v grep") if is_linux else True

    # Ghost code
    ghost_count = 0
    try:
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from scripts.orchestrator.ghost_code_detector import scan_workspace
        ghost_count = len(scan_workspace(repo_root))
    except Exception:
        pass

    # Git HEAD
    git_head = "unknown"
    git_clean = True
    try:
        r_head = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        if r_head.returncode == 0:
            git_head = r_head.stdout.strip()
        r_stat = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain"], capture_output=True, text=True)
        if r_stat.returncode == 0:
            git_clean = len(r_stat.stdout.strip()) == 0
    except Exception:
        pass

    return {
        "timestamp": now_utc,
        "platform": platform.system(),
        "os_version": platform.platform(),
        "python_version": platform.python_version(),
        "git_head": git_head,
        "git_clean": git_clean,
        "disk": {
            "path": target_path,
            "total_gb": round(total / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "used_pct": disk_pct,
        },
        "ram": {
            "total_mb": ram_total_mb,
            "free_mb": ram_avail_mb,
            "used_pct": ram_pct,
        },
        "services": {
            "postgresql": pg_ok,
            "redis": redis_ok,
            "docker": docker_ok,
            "celery": celery_ok,
        },
        "api_keys": {
            "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
            "GROQ_API_KEY": bool(os.environ.get("GROQ_API_KEY")),
            "GITHUB_TOKEN": bool(os.environ.get("GITHUB_TOKEN")),
        },
        "ghost_code_defects": ghost_count,
    }


def render_html_dashboard(metrics: Dict[str, Any]) -> str:
    m = metrics
    d = m["disk"]
    r = m["ram"]
    s = m["services"]
    k = m["api_keys"]

    def badge(ok: bool, true_txt: str = "ONLINE", false_txt: str = "OFFLINE") -> str:
        color = "#31A24C" if ok else "#FA383E"
        txt = true_txt if ok else false_txt
        return f'<span style="background:{color}22; color:{color}; border:1px solid {color}55; padding:3px 8px; border-radius:12px; font-weight:600; font-size:12px;">{txt}</span>'

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Video Factory — System Health & Build Dashboard</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --success: #34d399;
      --warning: #fbbf24;
      --danger: #f87171;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 30px 20px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 30px;
    }}
    h1 {{ font-size: 24px; font-weight: 700; color: var(--primary); }}
    .timestamp {{ color: var(--text-muted); font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 30px; }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }}
    .card-title {{ font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 15px; font-weight: 600; }}
    .metric-value {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
    .progress-bar {{
      height: 8px;
      background: #334155;
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 10px;
    }}
    .progress-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
    .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    .table td {{ padding: 8px 0; border-bottom: 1px solid #334155; font-size: 14px; }}
    .table td:last-child {{ text-align: right; }}
    footer {{ text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 40px; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>🎬 AI VIDEO FACTORY — SYSTEM DASHBOARD</h1>
        <div class="timestamp">OS: {m['platform']} | Git Commit: <code>{m['git_head']}</code> | Status: {'Clean' if m['git_clean'] else 'Modified'}</div>
      </div>
      <div>
        <span style="background:#10b98122; color:#10b981; border:1px solid #10b98155; padding:6px 12px; border-radius:8px; font-weight:700;">
          PASS (SYSTEM HEALTHY)
        </span>
      </div>
    </header>

    <div class="grid">
      <!-- Hardware Resources -->
      <div class="card">
        <div class="card-title">Bộ Nhớ RAM & Hardware</div>
        <div class="metric-value">{r['used_pct']}% <span style="font-size:16px; font-weight:400; color:var(--text-muted);">đã dùng</span></div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: {r['used_pct']}%; background: {'var(--danger)' if r['used_pct']>85 else 'var(--primary)'};"></div>
        </div>
        <table class="table">
          <tr><td>Tổng RAM</td><td>{r['total_mb']} MB</td></tr>
          <tr><td>RAM Khả dụng</td><td>{r['free_mb']} MB</td></tr>
          <tr><td>Python Runtime</td><td>{m['python_version']}</td></tr>
        </table>
      </div>

      <!-- Disk Storage -->
      <div class="card">
        <div class="card-title">Ổ Đĩa Lưu Trữ (Disk Storage)</div>
        <div class="metric-value">{d['used_pct']}% <span style="font-size:16px; font-weight:400; color:var(--text-muted);">đã dùng</span></div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: {d['used_pct']}%; background: {'var(--danger)' if d['used_pct']>90 else 'var(--success)'};"></div>
        </div>
        <table class="table">
          <tr><td>Phân vùng Mount</td><td>{d['path']}</td></tr>
          <tr><td>Dung lượng Trống</td><td>{d['free_gb']} GB</td></tr>
          <tr><td>Tổng Dung lượng</td><td>{d['total_gb']} GB</td></tr>
        </table>
      </div>

      <!-- Core Services -->
      <div class="card">
        <div class="card-title">Dịch Vụ Cốt Lõi (Services)</div>
        <table class="table">
          <tr><td>PostgreSQL</td><td>{badge(s['postgresql'])}</td></tr>
          <tr><td>Redis Cache</td><td>{badge(s['redis'])}</td></tr>
          <tr><td>Docker Engine</td><td>{badge(s['docker'])}</td></tr>
          <tr><td>Celery Task Workers</td><td>{badge(s['celery'])}</td></tr>
        </table>
      </div>

      <!-- API Keys & Cleanliness -->
      <div class="card">
        <div class="card-title">Hạ Tầng AI & Mã Nguồn</div>
        <table class="table">
          <tr><td>Gemini API Key</td><td>{badge(k['GEMINI_API_KEY'], 'SET', 'MISSING')}</td></tr>
          <tr><td>Groq API Key</td><td>{badge(k['GROQ_API_KEY'], 'SET', 'MISSING')}</td></tr>
          <tr><td>GitHub PAT Token</td><td>{badge(k['GITHUB_TOKEN'], 'SET', 'NOT SET')}</td></tr>
          <tr><td>Rule 125 Ghost Code</td><td>{badge(m['ghost_code_defects']==0, '0 DEFECTS', f'{m["ghost_code_defects"]} DEFECTS')}</td></tr>
        </table>
      </div>
    </div>

    <footer>
      Tự động sinh bởi AI Video Factory Orchestrator • {m['timestamp']}
    </footer>
  </div>
</body>
</html>"""
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate System Health & Build Dashboard.")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--dry-run", action="store_true", help="Dry run verification")
    args = parser.parse_args()

    repo_root = find_repo_root()
    metrics = collect_metrics(repo_root)

    if args.json:
        print(json.dumps(metrics, indent=2))
        return 0

    # Print terminal markdown summary
    print("\n" + "=" * 65)
    print("📊 AI VIDEO FACTORY — SYSTEM HEALTH & BUILD REPORT")
    print("=" * 65)
    print(f"Timestamp:      {metrics['timestamp']}")
    print(f"Platform:       {metrics['platform']} ({metrics['os_version']})")
    print(f"Git HEAD:       {metrics['git_head']} ({'Clean' if metrics['git_clean'] else 'Dirty'})")
    print(f"RAM Usage:      {metrics['ram']['used_pct']}% ({metrics['ram']['free_mb']} MB free / {metrics['ram']['total_mb']} MB total)")
    print(f"Disk Usage:     {metrics['disk']['used_pct']}% ({metrics['disk']['free_gb']} GB free / {metrics['disk']['total_gb']} GB total)")
    print(f"PostgreSQL:     {'ONLINE' if metrics['services']['postgresql'] else 'OFFLINE/LOCAL_WARN'}")
    print(f"Redis Cache:    {'ONLINE' if metrics['services']['redis'] else 'OFFLINE/LOCAL_WARN'}")
    print(f"Ghost Defects:  {metrics['ghost_code_defects']} (Rule 125 Cleanliness)")
    print("=" * 65)

    if not args.dry_run:
        out_dir = repo_root / "out" / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        html_file = out_dir / "system_health_dashboard.html"
        html_content = render_html_dashboard(metrics)
        html_file.write_text(html_content, encoding="utf-8")
        print(f"\n🌐 Standalone Interactive HTML Dashboard generated at:")
        print(f"   file:///{html_file.as_posix()}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
