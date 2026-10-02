#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/capture_exact_tutorial_frames.py
Captures frames from https://www.youtube.com/watch?v=cXQuNBZA0FA
Target: Seconds 32 to 49 (1s per frame) + Intro samples (0s to 30s).
"""
import sys
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

USER_DATA_DIR = r"C:\Users\hunghd2\.gemini\browser_profile"
ARTIFACT_DIR = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\ce87ffad-6e9b-44cd-ac13-980298764af9")
LOCAL_DIR = Path(r"C:\Users\hunghd2\Documents\antigravity\AI Video Factory\docs\exact_tutorial_frames")

LOCAL_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("🚀 Launching Playwright to inspect https://www.youtube.com/watch?v=cXQuNBZA0FA...")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080"
            ],
            viewport={"width": 1920, "height": 1080},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        target_url = "https://www.youtube.com/watch?v=cXQuNBZA0FA"
        print(f"Navigating to {target_url}...")
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)

        # Handle consent
        for btn_text in ["I agree", "Accept all", "Reject all", "Tôi đồng ý", "Chấp nhận tất cả"]:
            try:
                btn = page.query_selector(f"button:has-text('{btn_text}')")
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(1.5)
            except Exception:
                pass

        try:
            page.wait_for_selector("video", timeout=15000)
            print("Video element found!")
        except Exception as e:
            print(f"Failed to find video: {e}")
            browser.close()
            return

        # Skip ads
        for attempt in range(12):
            is_ad = page.evaluate("() => Boolean(document.querySelector('.ad-showing') || document.querySelector('.ytp-ad-player-overlay'))")
            if not is_ad:
                break
            print(f"Ad detected ({attempt+1}), skipping...")
            for sel in [".ytp-skip-ad-button", ".ytp-ad-skip-button-modern", "button:has-text('Skip')", ".ytp-ad-skip-button"]:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        time.sleep(2)
                        break
                except Exception:
                    pass
            time.sleep(2)

        # Hide controls
        page.evaluate("""() => {
            const v = document.querySelector('video');
            if (v) { v.pause(); v.muted = true; }
            const cb = document.querySelector('.ytp-chrome-bottom');
            if (cb) cb.style.display = 'none';
            const ct = document.querySelector('.ytp-chrome-top');
            if (ct) ct.style.display = 'none';
            const grad = document.querySelector('.ytp-gradient-bottom');
            if (grad) grad.style.display = 'none';
        }""")
        video = page.query_selector("video")

        # 1. Capture exact range: Seconds 32 to 49 (1s step)
        print("📸 Capturing SECONDS 32 TO 49 (1s per frame)...")
        for sec in range(32, 50):
            page.evaluate(f"() => {{ const v = document.querySelector('video'); if (v) v.currentTime = {sec}; }}")
            time.sleep(0.8)
            local_path = LOCAL_DIR / f"frame_sec_{sec:02d}.jpg"
            artifact_path = ARTIFACT_DIR / f"exact_sec_{sec:02d}.jpg"
            video.screenshot(path=str(local_path), type="jpeg", quality=90)
            artifact_path.write_bytes(local_path.read_bytes())
            print(f"Captured sec {sec:02d}: {local_path.name}")

        # 2. Also capture intro 0s to 30s every 2s for complete context
        print("📸 Capturing INTRO SAMPLES (0s to 30s, step 2s)...")
        for sec in range(0, 32, 2):
            page.evaluate(f"() => {{ const v = document.querySelector('video'); if (v) v.currentTime = {sec}; }}")
            time.sleep(0.6)
            local_path = LOCAL_DIR / f"intro_sec_{sec:02d}.jpg"
            artifact_path = ARTIFACT_DIR / f"exact_intro_{sec:02d}.jpg"
            video.screenshot(path=str(local_path), type="jpeg", quality=90)
            artifact_path.write_bytes(local_path.read_bytes())
            print(f"Captured intro {sec:02d}s")

        print("🎉 Capture finished successfully!")
        browser.close()

if __name__ == "__main__":
    main()
