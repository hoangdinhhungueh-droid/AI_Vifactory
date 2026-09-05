#!/usr/bin/env python3
"""
Human Gate 2 - Telegram Message Formatter v2
Redesigned format matching user's preferred layout (2026-09-01)
"""


def format_hg2_message_v2(episode_id: str, scene_count: int, bg_count: int, fg_count: int, 
                          prompts_path: str, notion_synced: bool = True, story_score: str = "N/A") -> tuple[str, str]:
    """
    Generate HG2 Telegram message in redesigned format (Markdown)
    
    Args:
        episode_id: e.g. "EN_EP0251"
        scene_count: Total scenes in episode
        bg_count: Number of background prompts
        fg_count: Number of foreground prompts
        prompts_path: Full VPS path to prompts_forge.json
        notion_synced: Whether prompts synced to Notion (default: True)
        story_score: Story gate score (default: "N/A")
    
    Returns:
        tuple[str, str]: (message_text, parse_mode) - ready for Telegram API
    """
    total_prompts = bg_count + fg_count
    sync_status = "đã sync Notion ✅" if notion_synced else "⏳ đang sync..."
    
    # Build the code block for copy-paste
    code_block = f"""/run:image task:{episode_id}

CONTEXT & CONSTRAINTS (Rule 435-437):
Episode: {episode_id}
Prompts: {prompts_path} ({total_prompts} reuse keys: BG+FG)
- layer_type: Background (16:9) or Foreground (1:1 chroma-key #FF00FF)
- Each reuse_key → one Antigravity /run:image request

QUALITY RULES (Rule 435 — 2K Resolution):
ALL images MUST be 2560x1440 (16:9 aspect, 2K DCI).
Append to every prompt: [TECHNICAL: Generate at 2560x1440 resolution (16:9 aspect ratio, 2K DCI). Do not upscale or downscale.]

TIMING RULES (Rule 436 — 45s Spacing):
- Minimum 45 seconds between image generation requests
- Per-request timeout: 120 seconds
- Do NOT submit >1 request concurrently

LAYER SPECIFICATIONS:
- Background (16:9): cinematic, no people in close-up, documentary lighting
- Foreground (1:1 chroma-key): solid #FF00FF magenta background, full body, clean cutout

STORAGE & UPDATE:
1. Save images: /var/vf/episodes/{episode_id}/assets/
2. Update Notion Image Asset Library: Episode ID, Reuse Key (match Prompt Library), Layer Type, Status=Approved

EXECUTION (Rule 120 — Native UI, No Quota):
Use Antigravity's native chat + Image 3 directly. No TDE, no rate limits, no quota cap."""
    
    # Build the main message (Markdown format)
    message = f"""🎨 *[HUMAN GATE 2] PROMPTS SẴN SÀNG — CẦN SINH ẢNH*

🎬 Episode: `{episode_id}`
📋 Scenes: {scene_count} • BG prompts: {bg_count} • FG prompts: {fg_count}
📊 Story gate: {story_score}
🎭 Director Plan + Prompt Library: {sync_status}

📋 Dán nguyên khối dưới đây vào Antigravity chat:

```
{code_block}
```

👉 _Pipeline tự kiểm tra mỗi ~10 phút — khi mọi ảnh BG/FG đã Approved/Pulled by VPS trên Notion, tự chạy tiếp B5 → B10 và gửi card HG3. Nút dưới đây chỉ để ghi nhận, không kích hoạt render._"""
    
    return message, "Markdown"


# CLI entry point for testing format generation
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: python hg2_telegram_format_v2.py <episode_id> <scenes> <bg_count> <fg_count>")
        print("\nExample: python hg2_telegram_format_v2.py EN_EP0251 14 12 14")
        sys.exit(1)
    
    episode_id = sys.argv[1]
    scene_count = int(sys.argv[2])
    bg_count = int(sys.argv[3])
    fg_count = int(sys.argv[4])
    prompts_path = f"/var/vf/episodes/{episode_id}/prompts_forge.json"
    
    message, parse_mode = format_hg2_message_v2(episode_id, scene_count, bg_count, fg_count, prompts_path)
    print("=" * 80)
    print(f"HG2 TELEGRAM MESSAGE FORMAT V2 (parse_mode={parse_mode})")
    print("=" * 80)
    print(message)
    print("=" * 80)
