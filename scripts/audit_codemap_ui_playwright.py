#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/audit_codemap_ui_playwright.py — Playwright Audit for Code Map UI (Rule 122 & Boss Item 9).

Performs headless Chromium UI audit against .codemap/pipeline.html across 3 viewports:
- 1920x1080 (Desktop)
- 768x1024 (Tablet)
- 375x812 (Mobile)

Traps console errors and pageerror exceptions, asserting 0 errors.
Saves real screenshots with SHA-256 hashes for Boss verification.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HTML_PATH = ROOT / ".codemap" / "pipeline.html"
SCREENSHOTS_DIR = ROOT / ".codemap" / "screenshots"


def audit_codemap_ui() -> dict:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("Playwright is not installed. Live audit cannot be replayed from cache.") from e

    if not HTML_PATH.exists():
        from tools.codemap.ui.render import generate_pipeline_html
        generate_pipeline_html()

    viewports = [
        ("desktop", 1920, 1080),
        ("tablet", 768, 1024),
        ("mobile", 375, 812),
    ]

    results = {}
    total_console_errors = []
    total_page_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for label, w, h in viewports:
            console_errors = []
            page_errors = []

            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()

            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))

            file_url = HTML_PATH.as_uri()
            page.goto(file_url, wait_until="networkidle")

            # Verify DOM rendered
            stage_cards = page.locator(".stage-card")
            card_count = stage_cards.count()

            # Click first stage card to test interactivity
            if card_count > 0:
                stage_cards.first.click()
                page.wait_for_timeout(300)

            screenshot_path = SCREENSHOTS_DIR / f"codemap_{label}_{w}x{h}.png"
            page.screenshot(path=str(screenshot_path), full_page=False)

            sha256 = hashlib.sha256(screenshot_path.read_bytes()).hexdigest()
            file_size = screenshot_path.stat().st_size

            results[label] = {
                "viewport": f"{w}x{h}",
                "screenshot": str(screenshot_path),
                "sha256": sha256,
                "size_bytes": file_size,
                "card_count": card_count,
                "console_errors": console_errors,
                "page_errors": page_errors,
                "status": "PASS" if not console_errors and not page_errors else "FAIL",
            }
            total_console_errors.extend(console_errors)
            total_page_errors.extend(page_errors)
            context.close()

        browser.close()

    import subprocess
    import time
    git_sha = "unknown"
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass

    summary = {
        "status": "PASS" if not total_console_errors and not total_page_errors else "FAIL",
        "git_sha": git_sha,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_console_errors": len(total_console_errors),
        "total_page_errors": len(total_page_errors),
        "viewports": results,
    }
    print(json.dumps(summary, indent=2))
    if summary["status"] != "PASS":
        sys.exit(1)
    return summary


if __name__ == "__main__":
    audit_codemap_ui()
