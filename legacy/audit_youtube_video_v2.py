import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.legacy_guard import forbid_legacy
forbid_legacy(__name__)

"""
scripts/audit_youtube_video_v2.py — Robust Playwright YouTube Frame Auditor
Captures frames from YouTube video player at designated time intervals to audit VOX motion graphics and visual pacing.
"""
import os
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from playwright.sync_api import sync_playwright

VIDEO_URL = "https://www.youtube.com/watch?v=r9OhRzstvRA"
OUTPUT_DIR = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\40cd75b2-17c1-4fa2-8f8c-54fbbd590ae7\youtube_frames")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Timestamps to audit (seconds)
TARGET_SECONDS = [3, 10, 25, 45, 70, 100, 140, 180, 220, 260, 300]

def audit_youtube():
    print(f"🚀 Launching Playwright to inspect: {VIDEO_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        print("Navigating to YouTube video...")
        page.goto(VIDEO_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Handle cookie consent or dialogs if any
        try:
            reject_btn = page.locator("button[aria-label*='Reject'], button[aria-label*='Từ chối'], button[aria-label*='I agree']")
            if reject_btn.count() > 0:
                reject_btn.first.click()
                time.sleep(1)
        except Exception:
            pass

        # Wait for video element
        video = page.locator("video.html5-main-video")
        video.wait_for(state="attached", timeout=30000)
        print("Video element found.")

        # Hide YouTube UI overlays (controls, title, branding, spinner) for clean frame inspection
        page.evaluate("""
            const hide = (sel) => { const el = document.querySelector(sel); if (el) el.style.display = 'none'; };
            hide('.ytp-chrome-bottom');
            hide('.ytp-chrome-top');
            hide('.ytp-gradient-bottom');
            hide('.ytp-gradient-top');
            hide('.ytp-spinner');
            hide('.ytp-bezel-text-wrapper');
        """)

        # Get actual video duration
        duration = page.evaluate("document.querySelector('video').duration")
        print(f"Actual video duration on YouTube: {duration:.2f} seconds ({duration/60:.2f} minutes)")

        for sec in TARGET_SECONDS:
            if sec > duration:
                continue
            print(f"Seeking to t={sec}s...")
            # Use player.seekTo and briefly play so YouTube fetches the stream
            page.evaluate(f"""
                () => {{
                    const player = document.getElementById('movie_player');
                    if (player && player.seekTo) {{
                        player.seekTo({sec}, true);
                        player.playVideo();
                    }} else {{
                        const v = document.querySelector('video');
                        v.currentTime = {sec};
                        v.play();
                    }}
                }}
            """)
            time.sleep(2.5)  # Wait for buffer & frame render
            page.evaluate("""
                () => {
                    const player = document.getElementById('movie_player');
                    if (player && player.pauseVideo) {
                        player.pauseVideo();
                    } else {
                        document.querySelector('video').pause();
                    }
                    const spinner = document.querySelector('.ytp-spinner');
                    if (spinner) spinner.style.display = 'none';
                }
            """)
            time.sleep(0.5)
            frame_path = OUTPUT_DIR / f"frame_{sec:03d}s.png"
            video.screenshot(path=str(frame_path))
            print(f"Captured: {frame_path.name} ({os.path.getsize(frame_path)} bytes)")

        browser.close()
        print("✅ Frame capture completed successfully.")

if __name__ == "__main__":
    audit_youtube()
