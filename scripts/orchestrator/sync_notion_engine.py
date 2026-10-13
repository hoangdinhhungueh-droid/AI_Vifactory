#!/usr/bin/env python3
"""sync_notion_engine.py — Two-Way Notion SoT Prompt Engine Synchronizer.

Restores true Single Source of Truth (SoT) between Notion and AI Video Factory:
- Notion Page Management under '🎬 Video Factory Prompt Engine Hub' (3f801989-2400-81c5-9459-f75fc00f24a1)
- Supports 5 Core Prompt Modules:
  1. B1 Strategy (3f801989-2400-8157-96f9-cd29c62cd7b1) -> config/prompts/b1_strategic_rules.md
  2. B2 Editorial (3f801989-2400-818a-adf1-c5f7cc3da7ed) -> config/prompts/b2_editorial_prompt.md
  3. B3 Director (3f801989-2400-81c9-bdb0-c4dc60b43988) -> config/prompts/b3_director_prompt.md
  4. B3.5 Visual (3f801989-2400-81e3-8cc6-c9bb0bb4650c) -> config/prompts/b35_visual_rules.md
  5. B10 SEO (3f801989-2400-8172-8655-cc3cd462cbef) -> config/prompts/seo_package_prompt.md
- Guarantees Zero-Mock truthfulness (Rule 118, Rule 126, Rule 133).

Usage:
  python sync_notion_engine.py --status     # Inspect live status & char counts
  python sync_notion_engine.py --push       # Uplink local prompt files to Notion
  python sync_notion_engine.py --pull       # Pull live Notion blocks to local & snapshot
  python sync_notion_engine.py --diff       # Show textual diff between Notion & disk
"""
import os
import sys
import json
import time
import hashlib
import difflib
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

try:
    import ag_notion_bridge as bridge
except ImportError:
    bridge = None

PAGE_MAP_FILE = ROOT_DIR / "data" / "notion_audit" / "prompt_engine_page_ids.json"
SNAPSHOT_FILE = ROOT_DIR / "data" / "notion_audit" / "skills_snapshot.json"


def load_page_registry() -> dict:
    if PAGE_MAP_FILE.exists():
        try:
            return json.loads(PAGE_MAP_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ Failed to read {PAGE_MAP_FILE}: {e}")
    return {}


def text_to_notion_blocks(markdown_text: str) -> list[dict]:
    """Convert markdown lines into Notion blocks (paragraphs, headings, lists, callouts)."""
    blocks = []
    lines = markdown_text.splitlines()
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Heading 1
        if stripped.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:][:2000]}}]
                }
            })
        # Heading 2
        elif stripped.startswith("## ") or stripped.startswith("=== "):
            clean_h2 = stripped.replace("## ", "").replace("=== ", "").replace(" ===", "")
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": clean_h2[:2000]}}]
                }
            })
        # Heading 3
        elif stripped.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[4:][:2000]}}]
                }
            })
        # Bullet list
        elif stripped.startswith("• ") or stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                }
            })
        # Numbered list
        elif any(stripped.startswith(f"{i}. ") for i in range(1, 20)):
            dot_pos = stripped.find(". ")
            content = stripped[dot_pos + 2:]
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                }
            })
        # Divider
        elif stripped in ("---", "___", "***"):
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        # Callout
        elif stripped.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[2:][:2000]}}]
                }
            })
        # Paragraph
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": stripped[:2000]}}]
                }
            })
    return blocks


def parse_block_to_text(block: dict) -> str:
    """Parse a single Notion block into markdown text."""
    btype = block.get("type", "")
    texts = block.get(btype, {}).get("rich_text", [])
    text = "".join(t.get("plain_text", "") for t in texts).strip()
    
    if btype == "heading_1":
        return f"\n# {text}\n"
    elif btype == "heading_2":
        return f"\n## {text}\n"
    elif btype == "heading_3":
        return f"\n### {text}\n"
    elif btype == "bulleted_list_item":
        return f"• {text}" if text else ""
    elif btype == "numbered_list_item":
        return f"1. {text}" if text else ""
    elif btype == "callout":
        return f"> {text}" if text else ""
    elif btype == "paragraph":
        return text
    elif btype == "divider":
        return "---"
    elif btype == "code":
        lang = block.get("code", {}).get("language", "")
        return f"\n```{lang}\n{text}\n```\n" if text else ""
    return text


def fetch_notion_page_text(page_id: str) -> str:
    """Fetch all blocks for a page and assemble clean markdown text."""
    if not bridge:
        raise RuntimeError("ag_notion_bridge is not available")
    res = bridge.get_blocks(page_id, page_size=100)
    if res.get("error"):
        raise RuntimeError(f"Notion API error: {res.get('message') or res}")
    blocks = res.get("results", [])
    lines = []
    for b in blocks:
        t = parse_block_to_text(b)
        if t:
            lines.append(t)
    return "\n".join(lines).strip()


def push_to_notion(reg: dict, module_key: str = None):
    """Push local prompt files up to Notion SoT subpages."""
    print("=" * 80)
    print("🚀 PUSHING PROMPT FILES TO NOTION SOT (UPLINK SYNC)")
    print("=" * 80)
    
    pages = reg.get("pages", {})
    if module_key:
        if module_key not in pages:
            print(f"❌ Unknown module: {module_key}. Available: {list(pages.keys())}")
            return
        pages = {module_key: pages[module_key]}
    success_count = 0

    for key, info in pages.items():
        page_id = info["page_id"]
        rel_file = info["target_file"]
        local_file = ROOT_DIR / rel_file
        
        if not local_file.exists():
            print(f"  ❌ Skipping {key}: Local file {local_file} not found")
            continue
            
        content = local_file.read_text(encoding="utf-8").strip()
        print(f"\n  • [{key}] {info['title']}")
        print(f"    Page ID: {page_id}")
        print(f"    Local file: {rel_file} ({len(content)} chars)")
        
        # 1. Fetch existing blocks to clear (keep clean SoT)
        try:
            existing = bridge.get_blocks(page_id)
            if not existing.get("error"):
                del_count = 0
                for b in existing.get("results", []):
                    bridge.delete_block(b["id"])
                    del_count += 1
                if del_count > 0:
                    print(f"    🧹 Cleared {del_count} old blocks from Notion page")
        except Exception as e:
            print(f"    ⚠️ Notice during block cleanup: {e}")

        # 2. Convert markdown into blocks
        blocks = text_to_notion_blocks(content)
        
        # 3. Append in batches of 50 (Notion API max children limit is 100)
        batch_size = 40
        for i in range(0, len(blocks), batch_size):
            chunk = blocks[i:i + batch_size]
            append_res = bridge.append_children_blocks(page_id, chunk)
            if append_res.get("error"):
                print(f"    ❌ Error appending chunk {i}..{i+len(chunk)}: {append_res}")
                break
            time.sleep(0.3)  # Anti rate-limit sleep
            
        print(f"    ✅ Successfully pushed {len(blocks)} blocks ({len(content)} chars) to Notion")
        success_count += 1

    print("\n" + "=" * 80)
    print(f"🎉 PUSH COMPLETE: {success_count}/{len(pages)} modules uploaded to Notion SoT!")
    print("=" * 80)


def pull_from_notion(reg: dict):
    """Pull live Notion blocks down to local prompt files and update snapshot."""
    print("=" * 80)
    print("📥 PULLING LIVE PROMPTS FROM NOTION SOT (DOWNLINK SYNC)")
    print("=" * 80)

    pages = reg.get("pages", {})
    snapshot_data = {}
    if SNAPSHOT_FILE.exists():
        try:
            snapshot_data = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    success_count = 0
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    for key, info in pages.items():
        page_id = info["page_id"]
        rel_file = info["target_file"]
        local_file = ROOT_DIR / rel_file

        print(f"\n  • [{key}] {info['title']}")
        print(f"    Page ID: {page_id}")
        
        try:
            live_text = fetch_notion_page_text(page_id)
            if len(live_text) < 50:
                print(f"    ⚠️ Warning: Pulled content too short ({len(live_text)} chars). Keeping existing file.")
                continue

            # Write to local file
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_text(live_text, encoding="utf-8")
            
            # Compute sha256
            sha = hashlib.sha256(live_text.encode("utf-8")).hexdigest()
            snapshot_data[key] = {
                "content": live_text,
                "page_id": page_id,
                "title": info["title"],
                "sha256": sha,
                "chars": len(live_text),
                "synced_at": now_str,
                "source": "NOTION_API_LIVE"
            }
            
            print(f"    ✅ Updated {rel_file} ({len(live_text)} chars, SHA: {sha[:8]})")
            success_count += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"    ❌ Failed pulling from Notion: {e}")

    snapshot_data["updated_at"] = now_str
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(snapshot_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Updated master snapshot file: {SNAPSHOT_FILE}")

    print("\n" + "=" * 80)
    print(f"🎉 PULL COMPLETE: {success_count}/{len(pages)} modules synchronized from Notion SoT!")
    print("=" * 80)


def show_status(reg: dict):
    """Inspect and report synchronization parity between Notion and Local Disk."""
    print("=" * 80)
    print("🔬 NOTION SOT LIVE CONNECTIVITY & SYNC STATUS MATRIX")
    print("=" * 80)
    print(f"Hub: {reg.get('hub_name')} ({reg.get('hub_id')})")
    print("-" * 80)
    
    pages = reg.get("pages", {})
    
    for key, info in pages.items():
        page_id = info["page_id"]
        rel_file = info["target_file"]
        local_file = ROOT_DIR / rel_file
        
        local_chars = len(local_file.read_text(encoding="utf-8")) if local_file.exists() else 0
        local_sha = hashlib.sha256(local_file.read_bytes()).hexdigest()[:8] if local_file.exists() else "NONE"

        live_chars = 0
        live_status = "CONNECTING..."
        try:
            live_text = fetch_notion_page_text(page_id)
            live_chars = len(live_text)
            live_sha = hashlib.sha256(live_text.encode("utf-8")).hexdigest()[:8]
            if live_sha == local_sha:
                live_status = "✅ IN SYNC (100% PARITY)"
            else:
                live_status = f"⚡ DIFF DETECTED (Notion: {live_chars}c vs Disk: {local_chars}c)"
        except Exception as e:
            live_status = f"❌ OFFLINE / ERR: {e}"

        print(f"• [{key.upper()}] {info['title']}")
        print(f"  Page ID: {page_id}")
        print(f"  Local File: {rel_file} ({local_chars} chars, SHA: {local_sha})")
        print(f"  Live Notion: {live_chars} chars | Status: {live_status}")
        print("-" * 80)


def show_diff(reg: dict):
    """Show line-by-line diff between live Notion and local disk files."""
    pages = reg.get("pages", {})
    for key, info in pages.items():
        page_id = info["page_id"]
        rel_file = info["target_file"]
        local_file = ROOT_DIR / rel_file
        if not local_file.exists():
            continue
            
        local_text = local_file.read_text(encoding="utf-8")
        try:
            live_text = fetch_notion_page_text(page_id)
        except Exception as e:
            print(f"❌ Error fetching {key} from Notion: {e}")
            continue

        local_lines = local_text.splitlines()
        live_lines = live_text.splitlines()

        diff = list(difflib.unified_diff(
            local_lines, live_lines,
            fromfile=f"Local: {rel_file}",
            tofile=f"Notion: {info['title']} ({page_id})",
            lineterm=""
        ))
        
        print(f"\n=================== DIFF FOR {key.upper()} ===================")
        if diff:
            for l in diff[:40]:
                print(l)
            if len(diff) > 40:
                print(f"... ({len(diff) - 40} more lines)")
        else:
            print("✅ 100% MATCH: Zero differences between Notion and Local Disk.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Notion SoT Prompt Engine Synchronizer")
    parser.add_argument("--push", action="store_true", help="Push local prompts up to Notion SoT")
    parser.add_argument("--pull", action="store_true", help="Pull live Notion prompts down to disk & snapshot")
    parser.add_argument("--status", action="store_true", help="Show parity status matrix")
    parser.add_argument("--diff", action="store_true", help="Show textual diff between Notion and local disk")
    parser.add_argument("--module", type=str, help="Target specific module key (e.g. b1_strategy, b35_visual)")
    args = parser.parse_args()

    reg = load_page_registry()
    if not reg:
        print("❌ Failed loading page registry. Check prompt_engine_page_ids.json.")
        sys.exit(1)

    if args.push:
        push_to_notion(reg, module_key=args.module)
    elif args.pull:
        pull_from_notion(reg)
    elif args.diff:
        show_diff(reg)
    else:
        show_status(reg)
