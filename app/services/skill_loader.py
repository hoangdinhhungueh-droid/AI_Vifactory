#!/usr/bin/env python3
"""skill_loader.py — Load Rules 113-121 động từ Notion Skill AI page.

Dynamic loader for Video Factory editorial & structural rules from Notion Single Source of Truth.
Replaces hardcoded system_prompt strings in hhtech_reasoner.py + story_engine_b2.py.

Created: 2026-08-31 (Fix for CRITICAL_HARDCODED_SKILLS_P0)
Updated: 2026-08-31 (Added real TTL cache implementation)
"""
import os
import sys
import logging
import time
from functools import wraps

# Add scripts dir to path for ag_notion_bridge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "scripts"))
import ag_notion_bridge as bridge

logger = logging.getLogger(__name__)

SKILL_AI_PAGE_ID = "ac901989-2400-827e-bda2-8175dabdcf13"
CACHE_TTL_SECONDS = int(os.getenv("SKILL_CACHE_TTL_SECONDS", "3600"))  # 1 hour default

# Cache state (module-level for simplicity)
_cache = {
    "data": None,
    "expiration": 0,
    "hits": 0,
    "misses": 0
}


def _fetch_skill_rules_impl() -> str:
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
    """Get cached skill rules with TTL expiration.
    
    Args:
        force_refresh: If True, clear cache and re-fetch from Notion
    
    Returns:
        str: Skill rules text for system_prompt injection.
             Empty string if fetch fails (non-blocking fallback).
    
    Cache behavior:
        - First call: Fetch from Notion, cache for TTL seconds
        - Subsequent calls: Return cached value if not expired
        - After TTL: Automatic refresh from Notion
        - force_refresh: Bypass cache, always fetch fresh
    
    Usage:
        # In hhtech_reasoner.py or story_engine_b2.py:
        from app.services.skill_loader import get_skill_rules
        
        system_prompt = (
            "You are the Lead Creative Director...\n"
            f"{get_skill_rules()}\n\n"  # ← Inject dynamic rules
            "Output ONLY valid JSON...\n"
        )
    """
    global _cache
    
    current_time = time.time()
    
    # Check if cache is valid
    if not force_refresh and _cache["data"] is not None and current_time < _cache["expiration"]:
        # Cache hit
        _cache["hits"] += 1
        logger.debug(f"[skill_loader] Cache hit (expires in {int(_cache['expiration'] - current_time)}s)")
        return _cache["data"]
    
    # Cache miss or expired - fetch fresh data
    _cache["misses"] += 1
    if force_refresh:
        logger.info("[skill_loader] Force refresh requested")
    elif _cache["data"] is None:
        logger.info("[skill_loader] First fetch (cold cache)")
    else:
        logger.info(f"[skill_loader] Cache expired (age: {int(current_time - (_cache['expiration'] - CACHE_TTL_SECONDS))}s)")
    
    # Fetch from Notion
    rules = _fetch_skill_rules_impl()
    
    # Update cache
    _cache["data"] = rules
    _cache["expiration"] = current_time + CACHE_TTL_SECONDS
    
    logger.info(f"[skill_loader] Cache updated (TTL: {CACHE_TTL_SECONDS}s, expires at: {time.strftime('%H:%M:%S', time.localtime(_cache['expiration']))})")
    
    return rules


def get_cache_info() -> dict:
    """Get cache statistics for monitoring.
    
    Returns:
        dict: Cache info with hits, misses, age, ttl, expiration time
    """
    global _cache
    
    current_time = time.time()
    age_seconds = 0
    remaining_seconds = 0
    
    if _cache["data"] is not None:
        cache_created = _cache["expiration"] - CACHE_TTL_SECONDS
        age_seconds = int(current_time - cache_created)
        remaining_seconds = max(0, int(_cache["expiration"] - current_time))
    
    return {
        "hits": _cache["hits"],
        "misses": _cache["misses"],
        "cached": _cache["data"] is not None,
        "age_seconds": age_seconds,
        "remaining_seconds": remaining_seconds,
        "ttl_seconds": CACHE_TTL_SECONDS,
        "expiration_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_cache["expiration"])) if _cache["data"] else None
    }


def clear_cache():
    """Manually clear the cache. Next call to get_skill_rules() will fetch from Notion."""
    global _cache
    _cache["data"] = None
    _cache["expiration"] = 0
    logger.info("[skill_loader] Cache manually cleared")


# CLI test interface
if __name__ == "__main__":
    import json
    
    print("Testing Skill Loader with TTL Cache...")
    print("=" * 60)
    
    # Test 1: Fetch rules (cold cache)
    print("\n[Test 1] Cold cache - fetching from Notion...")
    start = time.time()
    rules = get_skill_rules()
    t1 = time.time() - start
    if rules:
        print(f"✅ SUCCESS: Loaded {len(rules)} characters in {t1:.3f}s")
        print(f"\nFirst 500 chars:\n{rules[:500]}...")
    else:
        print("❌ FAILED: Empty result")
    
    # Test 2: Cache hit (warm cache)
    print("\n[Test 2] Warm cache - should be instant...")
    start = time.time()
    rules2 = get_skill_rules()
    t2 = time.time() - start
    
    if rules == rules2 and t2 < 0.001:  # Cache should be < 1ms
        print(f"✅ CACHE HIT: {t1:.3f}s (cold) vs {t2:.6f}s (warm) - {int(t1/t2)}x faster")
    else:
        print(f"⚠️  UNEXPECTED: {t1:.3f}s (cold) vs {t2:.3f}s (warm)")
    
    # Test 3: Cache info
    print("\n[Test 3] Cache statistics:")
    info = get_cache_info()
    print(json.dumps(info, indent=2))
    
    # Test 4: Wait for partial TTL, verify cache still valid
    print(f"\n[Test 4] Waiting 2 seconds (TTL={CACHE_TTL_SECONDS}s)...")
    time.sleep(2)
    info_after = get_cache_info()
    remaining_before = info["remaining_seconds"]
    remaining_after = info_after["remaining_seconds"]
    
    if remaining_after < remaining_before and remaining_after > 0:
        print(f"✅ TTL WORKING: {remaining_before}s → {remaining_after}s remaining")
    else:
        print(f"⚠️  TTL: {remaining_before}s → {remaining_after}s")
    
    # Test 5: Force refresh
    print("\n[Test 5] Testing force refresh...")
    rules_refreshed = get_skill_rules(force_refresh=True)
    if rules_refreshed:
        print(f"✅ FORCE REFRESH: {len(rules_refreshed)} characters")
        info_refresh = get_cache_info()
        print(f"   Cache reset: {info_refresh['age_seconds']}s old, {info_refresh['remaining_seconds']}s remaining")
    else:
        print("❌ REFRESH FAILED")
    
    # Test 6: Manual clear
    print("\n[Test 6] Testing manual cache clear...")
    clear_cache()
    info_cleared = get_cache_info()
    if not info_cleared["cached"]:
        print(f"✅ CACHE CLEARED: cached={info_cleared['cached']}")
    else:
        print(f"❌ CLEAR FAILED: cached={info_cleared['cached']}")
    
    print("\n" + "=" * 60)
    print("Test complete")
