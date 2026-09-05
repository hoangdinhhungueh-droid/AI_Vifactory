#!/usr/bin/env python3
"""
B4 Trigger Form - Telegram Delivery
Sends formatted form to user's Telegram using VPS credentials
"""
import requests
import sys
import os

# Read credentials from VPS env (standardized naming)
BOT_TOKEN = os.environ.get('VF_TG_BOT_TOKEN') or (sys.argv[1] if len(sys.argv) > 1 else None)
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID') or (sys.argv[2] if len(sys.argv) > 2 else None)

if not BOT_TOKEN or not CHAT_ID:
    print("❌ Missing credentials")
    print("   Set VF_TG_BOT_TOKEN and TELEGRAM_CHAT_ID in environment")
    print("   Or: python3 telegram_send_b4_form.py <BOT_TOKEN> <CHAT_ID>")
    sys.exit(1)

# B4 Form content - complete trigger documentation
FORM = """
/run:image task:<episode_id>

📍 EPISODE: <episode_id>
📂 SOURCE: VPS /var/vf/episodes/<episode_id>/prompts_forge.json
🎯 ENGINE: Gemini Pro Web (Zero Cost, unlimited)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 IMAGE FORMAT (Rules 435 & 439)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**100% PNG FORMAT MANDATORY**

Layer 1: Background (16:9)
• Resolution: 2560x1440 (2K DCI)
• Format: PNG 24-bit RGB
• Content: Cinematic wide shot, NO close-up people
• Example: constantinople-gateway.png

Layer 2: Foreground (1:1 Transparent)
• Resolution: 2048x2048
• Format: PNG 32-bit RGBA (alpha channel required)
• Process:
  1. Generate on #FF00FF magenta background
  2. Illustrated/Drawn style, full body
  3. Auto chroma-key → transparent PNG
• Example: basil-second_transparent.png

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 WORKFLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Parse prompts_forge.json from VPS
2. Generate via Gemini Pro Web (3-5s spacing)
3. Chroma-key FG → transparent PNG
4. Upload to VPS: /var/vf/episodes/<ep>/images/
5. Sync to Notion Image Asset Library

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 B6 AUTO-TRIGGER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Expected: Notion sync → Cron poller (10min) → Auto-spawn B6

⚠️ KNOWN ISSUE (2026-08-31):
• Poller queries Parent DB, Sync writes Child DB
• Result: B6 never auto-triggers
• Workaround:
  ssh root@claude.vifactory.com
  python3 scripts/sync_images_to_notion.py <ep>
  python3 scripts/continue_after_images.py <ep>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INPUT (Before):
□ Gemini Pro Web authenticated
□ VPS MCP connection active
□ Notion token valid
□ prompts_forge.json exists

OUTPUT (After):
□ All PNGs generated (BG 2560x1440, FG 2048x2048)
□ FG transparency verified (alpha channel)
□ Files uploaded to VPS
□ Notion synced (Status=Approved)
□ B6 trigger verified

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 QUALITY GATES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REJECT if:
❌ JPG/WEBP format → regenerate PNG
❌ Wrong resolution → regenerate to spec
❌ FG not transparent → run chroma-key
❌ Close-up people in BG → request wide shot
❌ Photorealistic characters → request illustrated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Form v2.1 (2026-08-31)
Session: Multi-agent orchestration B3.5→B4 gap
Ref: ORCHESTRATION_FINAL_REPORT.md
"""

# Send via Telegram API
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
response = requests.post(url, json={
    "chat_id": CHAT_ID,
    "text": FORM,
    "parse_mode": "Markdown"
})

if response.ok:
    result = response.json()['result']
    print(f"✓ Sent to Telegram")
    print(f"  Message ID: {result['message_id']}")
    print(f"  Chat: {result['chat']['id']}")
else:
    print(f"✗ Failed: {response.status_code}")
    print(f"  {response.text}")
    sys.exit(1)
