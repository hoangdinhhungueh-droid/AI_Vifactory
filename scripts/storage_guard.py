"""Storage guard for the credit-capped server + R2 free tier.
Reports disk usage, per-episode footprint, warns near caps, and (optionally)
sweeps intermediate render files while ALWAYS keeping the finals.

Usage:
  python3 scripts/storage_guard.py                  # report + dry-run sweep preview
  python3 scripts/storage_guard.py --apply --days 7 # delete intermediates older than 7d
"""
import os, sys, subprocess, shutil, time
from pathlib import Path

for raw in open("/root/secrets/.env"):
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    if line.lower().startswith("export "):
        line = line[7:]
    k, v = line.split("=", 1)
    k = k.strip(); v = v.strip().strip('"').strip("'")
    if v:
        os.environ[k] = v

APPLY = "--apply" in sys.argv
DAYS = 7
if "--days" in sys.argv:
    DAYS = int(sys.argv[sys.argv.index("--days") + 1])

EP_ROOT = Path("/var/vf/episodes")
INTERMEDIATE = ("tts_out.mp3", "audio_norm.mp3", "final_11.mp4")  # finals 169/916 always kept


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


print("=== DISK ===")
print(sh("df -h /"))
total, used, free = shutil.disk_usage("/")
pct = used / total * 100
print("root: %.1f%% used (%.1fGB / %.1fGB, free %.1fGB)" % (pct, used / 1e9, total / 1e9, free / 1e9))
print("LEVEL:", "OK" if pct < 75 else ("WARN" if pct < 90 else "CRITICAL"))

print("\n=== /var/vf footprint ===")
print(sh("du -sh /var/vf 2>/dev/null"))
print(sh("du -sh /tmp/vf 2>/dev/null"))
eps = sorted([p for p in EP_ROOT.glob("*") if p.is_dir()]) if EP_ROOT.exists() else []
print("episodes:", len(eps))
for ep in eps:
    sz = sum(f.stat().st_size for f in ep.glob("*") if f.is_file())
    print("  %-48s %.1f MB" % (ep.name, sz / 1e6))

now = time.time()
sweep = []
for ep in eps:
    for f in ep.glob("*"):
        if f.is_file() and f.name in INTERMEDIATE:
            age = (now - f.stat().st_mtime) / 86400
            if age > DAYS:
                sweep.append((f, f.stat().st_size, age))
sweep_mb = sum(s for _, s, _ in sweep) / 1e6
print("\n=== SWEEP intermediates > %dd (keeps final_169/final_916/subs/brain/license/payload) ===" % DAYS)
print("candidates: %d files, %.1f MB" % (len(sweep), sweep_mb))
for f, s, a in sweep[:30]:
    print("  %s  %.1fMB  %.0fd" % (f, s / 1e6, a))
if APPLY:
    freed = 0
    for f, s, _ in sweep:
        try:
            f.unlink(); freed += s
        except Exception as e:
            print("skip", f, e)
    print("DELETED %d files, freed %.1f MB" % (len(sweep), freed / 1e6))
else:
    print("(dry-run; add --apply to delete)")

print("\n=== R2 (Cloudflare, free tier = 10 GB storage) ===")
r2names = sorted([k for k in os.environ if k.startswith("R2_")])
print("R2 env vars present:", ", ".join(r2names) or "(none)")
try:
    import boto3
    ak = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("R2_ACCESS_KEY")
    sk = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("R2_SECRET_KEY")
    acct = os.getenv("R2_ACCOUNT_ID")
    bkt = os.getenv("R2_BUCKET") or os.getenv("R2_BUCKET_NAME")
    endpoint = os.getenv("R2_ENDPOINT") or os.getenv("R2_ENDPOINT_URL") or (("https://" + acct + ".r2.cloudflarestorage.com") if acct else None)
    if ak and sk and endpoint and bkt:
        s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=ak,
                          aws_secret_access_key=sk, region_name="auto")
        tot = 0; n = 0
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bkt):
            for o in page.get("Contents", []):
                tot += o["Size"]; n += 1
        print("bucket %s: %d objects, %.2f GB used (%.0f%% of 10GB free tier)" % (
            bkt, n, tot / 1e9, tot / 1e10 * 100))
    else:
        print("R2 creds incomplete -> skipping live check (need access key, secret, endpoint/account, bucket)")
except ImportError:
    print("boto3 not installed -> run: python3 -m pip install boto3 ; then re-run for live R2 usage")
except Exception as e:
    print("R2 check error:", e)
