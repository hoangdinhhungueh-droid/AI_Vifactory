#!/usr/bin/env python3
"""skill_loader.py — Load Rules 113-121 động từ Notion Skill AI page.

Dynamic loader for Video Factory editorial & structural rules from Notion Single Source of Truth.
Replaces hardcoded system_prompt strings in hhtech_reasoner.py + story_engine_b2.py.

Created: 2026-08-31 (Fix for CRITICAL_HARDCODED_SKILLS_P0)
"""
import os
import sys
import logging
from functools import lru_cache

# Add scripts dir to path for ag_notion_bridge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "scripts"))
import ag_notion_bridge as bridge

logger = logging.getLogger(__name__)

SKILL_AI_PAGE_ID = "ac901989-2400-827e-bda2-8175dabdcf13"
CACHE_TTL_SECONDS = int(os.getenv("SKILL_CACHE_TTL_SECONDS", "3600"))  # 1 hour default


@lru_cache(maxsize=1)
def _fetch_skill_rules() -> str:
    """Fetch and parse Rules 113-121 từ Notion Skill AI page.
    
    Returns:
        str: Formatted rules text ready for system_prompt injection.
             Returns empty string on error (non-blocking fallback).
    """
    try:
        # Fetch page blocks from Notion
        result = bridge.get_blocks(SKILL_AI_PAGE_ID, page_size=100)
        
        if isinstance(result, dict) and result.get("error"):
            logger.warning(f"[skill_loader] Notion API error: {result.get('message', 'unknown')}")
            return ""
        
        blocks = result.get("results", []) if isinstance(result, dict) else []
        if not blocks:
            logger.warning("[skill_loader] No blocks returned from Skill AI page")
            return ""
        
        # Parse blocks → extract rule text
        rules_lines = []
        in_rules_section = False
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "heading_1":
                # Start of major section
                texts = block.get("heading_1", {}).get("rich_text", [])
                header = "".join([t.get("plain_text", "") for t in texts])
                # Check if this is the Rules section (GROUP 113-121 or similar)
                if "GROUP" in header.upper() or "RULE" in header.upper():
                    in_rules_section = True
                    rules_lines.append(f"\n{'=' * 60}")
                    rules_lines.append(f"{header}")
                    rules_lines.append(f"{'=' * 60}\n")
            
            elif block_type == "heading_2":
                # Section header (e.g., "CORE EDITORIAL PRINCIPLES")
                texts = block.get("heading_2", {}).get("rich_text", [])
                header = "".join([t.get("plain_text", "") for t in texts])
                rules_lines.append(f"\n## {header}\n")
                in_rules_section = True
            
            elif block_type == "heading_3":
                # Sub-section
                texts = block.get("heading_3", {}).get("rich_text", [])
                header = "".join([t.get("plain_text", "") for t in texts])
                rules_lines.append(f"\n### {header}\n")
            
            elif block_type == "numbered_list_item" and in_rules_section:
                # Rule item (e.g., "1. OBJECTIVE & UNBIASED ANALYSIS: ...")
                texts = block.get("numbered_list_item", {}).get("rich_text", [])
                rule_text = "".join([t.get("plain_text", "") for t in texts])
                if rule_text.strip():
                    rules_lines.append(rule_text)
            
            elif block_type == "bulleted_list_item" and in_rules_section:
                # Sub-rule or detail point
                texts = block.get("bulleted_list_item", {}).get("rich_text", [])
                bullet_text = "".join([t.get("plain_text", "") for t in texts])
                if bullet_text.strip():
                    # Preserve bullet if it doesn't already have one
                    if not bullet_text.strip().startswith("•"):
                        rules_lines.append(f"  • {bullet_text}")
                    else:
                        rules_lines.append(f"  {bullet_text}")
            
            elif block_type == "paragraph" and in_rules_section:
                # Freeform text within rules
                texts = block.get("paragraph", {}).get("rich_text", [])
                para_text = "".join([t.get("plain_text", "") for t in texts])
                if para_text.strip():
                    rules_lines.append(para_text)
            
            elif block_type == "code":
                # Code blocks (examples in rules)
                code_texts = block.get("code", {}).get("rich_text", [])
                code = "".join([t.get("plain_text", "") for t in code_texts])
                language = block.get("code", {}).get("language", "")
                if code.strip():
                    rules_lines.append(f"\n```{language}")
                    rules_lines.append(code)
                    rules_lines.append("```\n")
        
        result_text = "\n".join(rules_lines)
        
        # Log success
        char_count = len(result_text)
        line_count = len([l for l in rules_lines if l.strip()])
        logger.info(f"[skill_loader] Loaded {char_count} chars, {line_count} lines from Notion Skill AI")
        
        return result_text
    
    except Exception as e:
        # Fallback to empty string on error (log warning but don't crash)
        logger.warning(f"[skill_loader] Failed to fetch Skill AI rules: {e}", exc_info=True)
        return ""


def get_skill_rules(force_refresh: bool = False) -> str:
    """Get cached skill rules, optionally force refresh.
    
    Args:
        force_refresh: If True, clear cache and re-fetch from Notion
    
    Returns:
        str: Skill rules text for system_prompt injection.
             Empty string if fetch fails (non-blocking fallback).
    
    Usage:
        # In hhtech_reasoner.py or story_engine_b2.py:
        from app.services.skill_loader import get_skill_rules
        
        system_prompt = (
            "You are the Lead Creative Director...\n"
            f"{get_skill_rules()}\n\n"  # ← Inject dynamic rules
            "Output ONLY valid JSON...\n"
        )
    """
    if force_refresh:
        _fetch_skill_rules.cache_clear()
        logger.info("[skill_loader] Cache cleared, forcing refresh from Notion")
    
    return _fetch_skill_rules()


def get_cache_info() -> dict:
    """Get LRU cache statistics for monitoring.
    
    Returns:
        dict: Cache info with hits, misses, size, maxsize
    """
    info = _fetch_skill_rules.cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "size": info.currsize,
        "maxsize": info.maxsize,
        "ttl_seconds": CACHE_TTL_SECONDS
    }


# CLI test interface
if __name__ == "__main__":
    import json
    
    print("Testing Skill Loader...")
    print("=" * 60)
    
    # Test 1: Fetch rules
    print("\n[Test 1] Fetching rules from Notion...")
    rules = get_skill_rules()
    if rules:
        print(f"✅ SUCCESS: Loaded {len(rules)} characters")
        print(f"\nFirst 500 chars:\n{rules[:500]}...")
    else:
        print("❌ FAILED: Empty result")
    
    # Test 2: Cache hit
    print("\n[Test 2] Testing cache...")
    import time
    start = time.time()
    rules1 = get_skill_rules()
    t1 = time.time() - start
    
    start = time.time()
    rules2 = get_skill_rules()
    t2 = time.time() - start
    
    if rules1 == rules2 and t2 < t1 / 5:  # Cache should be 5x+ faster
        print(f"✅ CACHE WORKING: {t1:.3f}s (cold) vs {t2:.3f}s (warm)")
    else:
        print(f"⚠️  CACHE: {t1:.3f}s (cold) vs {t2:.3f}s (warm)")
    
    # Test 3: Cache info
    print("\n[Test 3] Cache statistics:")
    info = get_cache_info()
    print(json.dumps(info, indent=2))
    
    # Test 4: Force refresh
    print("\n[Test 4] Testing force refresh...")
    rules_refreshed = get_skill_rules(force_refresh=True)
    if rules_refreshed:
        print(f"✅ REFRESH SUCCESS: {len(rules_refreshed)} characters")
    else:
        print("❌ REFRESH FAILED")
    
    print("\n" + "=" * 60)
    print("Test complete")
