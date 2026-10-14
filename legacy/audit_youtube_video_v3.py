import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.legacy_guard import forbid_legacy
forbid_legacy(__name__)

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

VIDEO_URL = "https://www.youtube.com/watch?v=r9OhRzstvRA"
OUTPUT_DIR = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\37d95fd9-3951-4a13-a623-d6096e672b22\youtube_clean_frames")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_SECONDS = [3, 15, 35, 60, 95, 130, 160, 200, 240, 280, 310]

def run():
    print(f"[AUDIT] Starting Playwright precise frame capture: {VIDEO_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(VIDEO_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Remove dialogs & controls
        page.evaluate("""
            const btns = document.querySelectorAll("button[aria-label*='Reject'], button[aria-label*='Từ chối'], button[aria-label*='I agree']");
            if (btns.length > 0) btns[0].click();
            
            const sel = ['.ytp-chrome-bottom', '.ytp-chrome-top', '.ytp-gradient-bottom', '.ytp-gradient-top', '.ytp-ce-element', '.ytp-spinner'];
            sel.forEach(s => {
                document.querySelectorAll(s).forEach(el => el.style.display = 'none');
            });
        """)

        video = page.locator("video.html5-main-video")
        video.wait_for(state="attached", timeout=30000)

        for sec in TARGET_SECONDS:
            print(f"Seeking to t={sec}s...")
            # Seek using JavaScript and wait for readyState >= 3 (HAVE_FUTURE_DATA)
            page.evaluate(f"""
                async () => {{
                    const v = document.querySelector('video');
                    v.currentTime = {sec};
                    await new Promise((resolve) => {{
                        const check = () => {{
                            if (Math.abs(v.currentTime - {sec}) < 0.5 && v.readyState >= 2) {{
                                resolve();
                            }} else {{
                                setTimeout(check, 100);
                            }}
                        }};
                        check();
                        setTimeout(resolve, 3500); // 3.5s timeout safeguard
                    }});
                }}
            """)
            time.sleep(1.0) # Paint wait
            frame_path = OUTPUT_DIR / f"frame_{sec:03d}s.png"
            video.screenshot(path=str(frame_path))
            print(f"  -> Captured {frame_path.name}")

        browser.close()
        print("Done capturing clean frames.")

if __name__ == "__main__":
    run()
