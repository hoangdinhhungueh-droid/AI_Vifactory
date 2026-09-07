#!/usr/bin/env python3
"""
scripts/health_monitor.py
VF Pipeline Health Monitor Sidecar (PM2-managed watchdog)
Checks every 60s: PM2 liveness, Redis stale locks, disk space,
cron heartbeat, stuck episode states. Auto-heals + Telegram alerts.
Rule 119: no shadow scripts. Rule 121: log evidence before PASS.
"""
import os, sys, time, json, subprocess, shutil, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, '/root/video_factory')

CHECK_INTERVAL_SECONDS = 60
PM2_TARGETS = ['vf-vps-mcp', 'vf-api', 'cf-vps-mcp']
REDIS_LOCK_MAX_AGE_SECONDS = 1800
DISK_WARN_PCT = 80
DISK_CRITICAL_PCT = 90
CRON_MAX_SILENCE_HOURS = 25
EPISODE_STUCK_MINUTES = 120
LOG_PREFIX = '[health_monitor]'


def _load_env():
    for p in ['/root/secrets/.env', '/root/video_factory/.env',
              '/root/video_factory/config/config.env',
              '/root/video_factory/secrets.env.txt']:
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


_load_env()
TELEGRAM_TOKEN = (os.getenv('VF_TG_BOT_TOKEN', '') or
                  os.getenv('TELEGRAM_BOT_TOKEN', '')).strip()
TELEGRAM_CHAT = (os.getenv('VF_TG_CHAT_ID', '') or
                 os.getenv('TELEGRAM_CHAT_ID', '')).strip()


def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        _log(f'[WARN] Telegram not configured -- suppressed')
        return
    payload = json.dumps({
        'chat_id': TELEGRAM_CHAT, 'text': msg,
        'parse_mode': 'HTML', 'disable_web_page_preview': True
    }).encode('utf-8')
    url = 'https://api.telegram.org/bot' + TELEGRAM_TOKEN + '/sendMessage'
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        _log(f'[WARN] Telegram send failed: {e}')


def redis_cmd(*args):
    try:
        r = subprocess.run(['redis-cli'] + list(args),
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception as e:
        _log(f'[WARN] redis-cli error: {e}')
        return ''


def redis_get(k): return redis_cmd('GET', k)
def redis_del(k): return redis_cmd('DEL', k)


def redis_object_idletime(k: str) -> int:
    try:
        return int(redis_cmd('OBJECT', 'IDLETIME', k))
    except Exception:
        return 0


def redis_keys(pat: str) -> list:
    raw = redis_cmd('KEYS', pat)
    return [k for k in raw.splitlines() if k.strip()] if raw else []


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'{ts} {LOG_PREFIX} {msg}', flush=True)


def check_pm2_processes() -> list:
    """CHECK 1 -- PM2 process liveness."""
    alerts = []
    try:
        result = subprocess.run(['pm2', 'jlist'],
                                capture_output=True, text=True, timeout=10)
        processes = json.loads(result.stdout) if result.stdout.strip() else []
        running = {p['name'] for p in processes
                   if p.get('pm2_env', {}).get('status') == 'online'}
        for target in PM2_TARGETS:
            if target not in running:
                _log(f'[ALERT] PM2 process {target!r} DOWN -- restarting')
                rr = subprocess.run(
                    ['pm2', 'restart', target],
                    capture_output=True, text=True, timeout=15)
                action = f'pm2 restart {target} -> exit {rr.returncode}'
                alerts.append((
                    target, action,
                    f'PM2 DOWN: <code>{target}</code>\n{action}'
                ))
    except Exception as e:
        _log(f'[ERROR] PM2 check failed: {e}')
    return alerts


def check_redis_stale_locks() -> list:
    """CHECK 2 -- Redis stale locks (vf:lock:* idle > 30min)."""
    alerts = []
    for key in redis_keys('vf:lock:*'):
        idle = redis_object_idletime(key)
        if idle >= REDIS_LOCK_MAX_AGE_SECONDS:
            _log(f'[ALERT] Stale lock {key} idle {idle}s -- releasing')
            redis_del(key)
            alerts.append((
                key, f'DEL {key}',
                f'Stale lock released: <code>{key}</code> '
                f'(idle {idle // 60}m {idle % 60}s)'
            ))
    return alerts


def check_disk_space() -> list:
    """CHECK 3 -- Disk space on /."""
    alerts = []
    try:
        usage = shutil.disk_usage('/')
        pct = int(usage.used / usage.total * 100)
        free_gb = usage.free / (1024 ** 3)
        if pct >= DISK_CRITICAL_PCT:
            _log(f'[ALERT] CRITICAL disk {pct}% -- flushing PM2 logs')
            subprocess.run(['pm2', 'flush'], capture_output=True)
            alerts.append((
                'disk', 'pm2 flush',
                f'CRITICAL Disk {pct}% (free {free_gb:.1f}GB)\n'
                f'PM2 logs flushed. Clean /tmp/vf_* via terminal.'
            ))
        elif pct >= DISK_WARN_PCT:
            alerts.append((
                'disk', 'warn-only',
                f'Disk WARNING {pct}% (free {free_gb:.1f}GB) '
                f'-- approaching critical {DISK_CRITICAL_PCT}%'
            ))
    except Exception as e:
        _log(f'[ERROR] Disk check: {e}')
    return alerts


def check_cron_heartbeat() -> list:
    """CHECK 4 -- Cron heartbeat via vf:cron:last_run Redis key."""
    alerts = []
    try:
        last_run_str = redis_get('vf:cron:last_run')
        if last_run_str:
            try:
                elapsed_h = (time.time() - float(last_run_str)) / 3600
                if elapsed_h > CRON_MAX_SILENCE_HOURS:
                    ts_str = datetime.fromtimestamp(
                        float(last_run_str)).strftime('%Y-%m-%d %H:%M')
                    _log(f'[ALERT] Cron silent {elapsed_h:.1f}h (last: {ts_str})')
                    alerts.append((
                        'cron', 'no-auto-fix',
                        f'Cron silent {elapsed_h:.0f}h '
                        f'(last: {ts_str}) -- manual check required'
                    ))
            except (ValueError, TypeError):
                pass
    except Exception as e:
        _log(f'[ERROR] Cron check: {e}')
    return alerts


def check_episode_states() -> list:
    """CHECK 5 -- Stuck RUNNING episodes (vf:episode:* > 2h)."""
    alerts = []
    for key in redis_keys('vf:episode:*'):
        try:
            raw = redis_get(key)
            if not raw:
                continue
            ep = json.loads(raw)
            if ep.get('status') != 'RUNNING':
                continue
            elapsed_min = (time.time() - ep.get('started_at', 0)) / 60
            if elapsed_min >= EPISODE_STUCK_MINUTES:
                task_id = ep.get('task_id', key)
                _log(f'[ALERT] Episode {task_id} stuck RUNNING {elapsed_min:.0f}min')
                alerts.append((
                    task_id, 'alert-only',
                    f'Stuck episode: <code>{task_id}</code> '
                    f'({elapsed_min:.0f}min) -- manual investigation required'
                ))
        except (json.JSONDecodeError, KeyError):
            pass
    return alerts


def run_health_check() -> bool:
    _log('=== Health check cycle START ===')
    all_alerts = []
    all_alerts.extend(check_pm2_processes())
    all_alerts.extend(check_redis_stale_locks())
    all_alerts.extend(check_disk_space())
    all_alerts.extend(check_cron_heartbeat())
    all_alerts.extend(check_episode_states())
    if all_alerts:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M VN')
        sep = '=' * 22
        body = '\n\n'.join(a[2] for a in all_alerts)
        msg = (f'VF HEALTH MONITOR -- {now_str}\n{sep}\n'
               f'{body}\n{sep}\nTotal anomalies: {len(all_alerts)}')
        _log(f'[REPORT] {len(all_alerts)} anomaly(ies) -- sending Telegram')
        send_telegram(msg)
    else:
        _log('=== All checks PASSED -- system healthy ===')
    return len(all_alerts) > 0


def main():
    _log(f'VF Health Monitor starting -- interval: {CHECK_INTERVAL_SECONDS}s')
    _log(f'PM2 targets: {PM2_TARGETS}')
    _log(f'Telegram token: {"SET" if TELEGRAM_TOKEN else "NOT SET"}')
    while True:
        try:
            run_health_check()
        except Exception as e:
            _log(f'[ERROR] Unhandled exception: {e}')
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
