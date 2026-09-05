#!/usr/bin/env python3
"""
Script to update telegram_buttons.py with B5 integration
Removes TIMING RULES and adds B5 IMAGE AUDIT + B6 TRIGGER sections
"""

import re

# Read the original file
with open('/root/video_factory/app/services/telegram_buttons.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the send_gate2_card function
# We'll do a simpler replacement: just replace the paste_block content between the opening and closing parens

# Define the old timing rules section to remove
old_timing_section = '''        f"TIMING RULES (Rule 436 — 45s Spacing):\\n"
        f"- Minimum 45 seconds between image generation requests\\n"
        f"- Per-request timeout: 120 seconds\\n"
        f"- Do NOT submit >1 request concurrently\\n\\n"'''

# Define the new B5+B6 sections to add after QUALITY RULES
new_b5_b6_sections = '''        f"B5 IMAGE AUDIT (Rule 436 — Quality Gate):\\n"
        f"After all images generated, audit each image before proceeding to B6:\\n\\n"
        f"TECHNICAL CHECKS (Auto-validation):\\n"
        f"✓ Resolution: 2560x1440 (16:9 aspect, 2K DCI)\\n"
        f"✓ Black frame detection: Reject if >95% black pixels (luminance <10)\\n"
        f"✓ File integrity: Size >0 bytes, valid PNG format\\n"
        f"✓ Reuse key validation: Matches prompt library (BG/FG type correct)\\n\\n"
        f"VISION AUDIT (Gemini 2.0 Flash-Lite):\\n"
        f"Evaluate each image on 3 dimensions:\\n"
        f"• D1: Prompt Adherence (40%) - Does image match the written prompt?\\n"
        f"• D2: Object Accuracy (35%) - Are objects, people, settings correctly depicted?\\n"
        f"• D3: Visual Logic (25%) - Does the scene make logical sense?\\n\\n"
        f"Scoring: 0.0–10.0 per dimension, weighted average\\n"
        f"Threshold: ≥8.0 for auto-approval\\n"
        f"Actions:\\n"
        f"  - Score <8.0: Mark as 'Review Required' (HG2.5 manual review)\\n"
        f"  - Score ≥8.0: Auto-approve and proceed to B6\\n"
        f"  - Technical check fails: Flag for regeneration\\n\\n"
        f"Audit Output: Save to /var/vf/episodes/{task_id}/b5_audit_report.json\\n\\n"
        f"B6 TRIGGER (Rule 437 — Automated Handoff):\\n"
        f"After B5 audit completes with verdict 'PASS' or 'CONDITIONAL_PASS', trigger VPS render pipeline:\\n\\n"
        f"Command: python3 scripts/continue_after_images.py --episode-id {task_id}\\n\\n"
        f"What This Does:\\n"
        f"• Starts B6 (TTS generation with en-US-DavisNeural)\\n"
        f"• Continues to B7 (Karaoke subtitles with word-level timing)\\n"
        f"• Proceeds to B8 (Remotion render + FFmpeg mux)\\n"
        f"• Completes B9-B10 (Quality probe + YouTube upload)\\n\\n"
        f"Expected Response:\\n"
        f"• Exit code 0: B6-B10 pipeline spawned successfully\\n"
        f"• Log file: /var/vf/logs/{task_id}_b4b10.log\\n"
        f"• Monitor: tail -f /var/vf/logs/{task_id}_b4b10.log\\n\\n"
        f"Failure Handling:\\n"
        f"• If execution fails: Retry once after 30 seconds\\n"
        f"• If still fails: Send HG2.5 Telegram alert with manual trigger command\\n\\n"
        f"Timing: B5 audit ~60-90s (52 images × 1-2s), Total B4→B6 <2 min (vs 10+ min with old cron-based B5)\\n\\n"'''

# Perform the replacement
if old_timing_section in content:
    updated_content = content.replace(old_timing_section, new_b5_b6_sections)
    
    # Write the updated content
    with open('/root/video_factory/app/services/telegram_buttons.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("SUCCESS: telegram_buttons.py updated with B5 integration")
    print("Changes: Removed TIMING RULES, Added B5 IMAGE AUDIT + B6 TRIGGER")
else:
    print("ERROR: TIMING RULES section not found in expected format")
    print("Manual review required")
    exit(1)
