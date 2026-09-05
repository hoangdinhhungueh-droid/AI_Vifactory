#!/usr/bin/env python3
"""
Human Gate 2 - Telegram Message Formatter
Generates structured notification for image generation trigger
"""


def format_hg2_message(episode_id: str, scene_count: int, bg_count: int, fg_count: int, 
                       prompts_path: str, notion_synced: bool = True, story_score: str = "N/A") -> str:
    """
    Generate HG2 Telegram message in user's preferred format (Markdown)
    
    Args:
        episode_id: e.g. "EN_EP0251"
        scene_count: Total scenes in episode
        bg_count: Number of background prompts
        fg_count: Number of foreground prompts
        prompts_path: Full VPS path to prompts_forge.json
        notion_synced: Whether prompts synced to Notion (default: True)
        story_score: Story gate score (default: "N/A")
    
    Returns:
        str: Formatted Telegram message (Markdown)
    """
    total_prompts = bg_count + fg_count
    sync_status = "đã sync Notion ✅" if notion_synced else "⏳ đang sync..."
    estimated_minutes = (total_prompts * 45) // 60
    
    message = f"""🎨 [HUMAN GATE 2] PROMPTS SẴN SÀNG — CẦN SINH ẢNH

📺 Episode: {episode_id}
📄 Scenes: {scene_count} · BG prompts: {bg_count} · FG prompts: {fg_count}
🎬 Story gate: {story_score}
📚 Director Plan + Prompt Library: {sync_status}

📋 Dán nguyên khối dưới đây vào Antigravity chat:

```
/run:image task:{episode_id}

CONTEXT & CONSTRAINTS (Rule 435-437):
Episode: {episode_id}
Prompts: {prompts_path} ({total_prompts} reuse keys: BG+FG)
  - layer_type: Background (16:9) or Foreground (1:1 chroma-key #FF00FF)
  - Each reuse_key → one Antigravity /run:image request

QUALITY RULES (Rule 435 – 2K Resolution):
ALL images MUST be 2560x1440 (16:9 aspect, 2K DCI).
Append to every prompt: [TECHNICAL: Generate at 2560x1440 resolution (16:9 aspect ratio, 2K DCI). Do not upscale or downscale.]

TIMING RULES (Rule 436 – 45s Spacing):
- Minimum 45 seconds between image generation requests
- Per-request timeout: 120 seconds
- Do NOT submit >1 request concurrently

LAYER SPECIFICATIONS:
- Background (16:9): cinematic, no people in close-up, documentary lighting
- Foreground (1:1 chroma-key): solid #FF00FF magenta background, full body, clean cutout

STORAGE & UPDATE:
1. Save images: /var/vf/episodes/{episode_id}/assets/
2. Update Notion Image Asset Library: Episode ID, Reuse Key (match Prompt Library), Layer Type, Status=Approved

EXECUTION (Rule 120 – Native UI, No Quota):
Use Antigravity's native chat + Image 3 directly. No IDE, no rate limits, no quota cap.
```

⚡️ Action: Copy khối trên → Paste vào Antigravity → Wait {estimated_minutes} phút"""
    
    return message


# CLI entry point for testing format generation
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: python hg2_telegram_format.py <episode_id> <scenes> <bg_count> <fg_count>")
        print("\nExample: python hg2_telegram_format.py EN_EP0251 14 12 14")
        sys.exit(1)
    
    episode_id = sys.argv[1]
    scene_count = int(sys.argv[2])
    bg_count = int(sys.argv[3])
    fg_count = int(sys.argv[4])
    prompts_path = f"/var/vf/episodes/{episode_id}/prompts_forge.json"
    
    message = format_hg2_message(episode_id, scene_count, bg_count, fg_count, prompts_path)
    print("=" * 80)
    print("HG2 TELEGRAM MESSAGE FORMAT")
    print("=" * 80)
    print(message)
    print("=" * 80)
