#!/usr/bin/env python3
"""scripts/orchestrator/run_pipeline.py — Canonical Forwarding Proxy to orchestrator.run_pipeline (Rule 125).

Allows invocation via either:
- python -m scripts.orchestrator.run_pipeline
- python -m orchestrator.run_pipeline
"""
import sys
from pathlib import Path

# Ensure repo root is at the head of sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from orchestrator.run_pipeline import main

if __name__ == "__main__":
    main()
