#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canonical Redirect Wrapper for Image Ready Watcher (Rule 125 Single Truth).
The active, hardened implementation is in scripts/watchers/image_ready_watcher.py.
"""
import os
import sys
from pathlib import Path

WATCHER_TARGET = Path(__file__).resolve().parent / "watchers" / "image_ready_watcher.py"

if __name__ == "__main__":
    os.execv(sys.executable, [sys.executable, str(WATCHER_TARGET)] + sys.argv[1:])
