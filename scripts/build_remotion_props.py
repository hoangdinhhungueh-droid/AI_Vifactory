"""
scripts/build_remotion_props.py — Canonical Wrapper (Rule 119)
Redirects legacy calls to app.services.build_remotion_props.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.build_remotion_props import main

if __name__ == "__main__":
    main()
