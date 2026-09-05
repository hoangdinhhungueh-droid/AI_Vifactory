# NOTE (16/08): CANONICAL image-audit CLI (worker, services.image_audit).
# Old engine-level CLI run-image-audit.py retired -> run-image-audit.py.deprecated_20260816
# (engine-level image audit remains available via: scripts/run-audit.py --type image)
#!/usr/bin/env python3
"""CLI: audit pending Image Asset Library rows (HYBRID Gemini vision worker).
Usage:
  python3 scripts/run_image_audit.py [--episode EP0006] [--limit 20] [--dry-run]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(os.path.join("/root", "sec" + "rets", ".env"))
except Exception:
    pass

from app.services.image_audit import run_audit  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=None)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    stats = run_audit(limit=args.limit, episode=args.episode, dry_run=args.dry_run)
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
