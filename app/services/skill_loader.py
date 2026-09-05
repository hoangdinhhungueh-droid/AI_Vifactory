#!/usr/bin/env python3
"""skill_loader.py — Dynamic Notion SoT Multi-Hub Recursive Loader.

Loads editorial, structural, and visual rules dynamically from Notion Single Source of Truth:
- Central Skill AI: ac901989-2400-827e-bda2-8175dabdcf13 (Rules 113–121)
- Content Engine Hub: 9bb01989-2400-82c0-9ed4-01f19c7ee23f (5-Act narrative, pacing, curiosity loops)
- Media Production Hub: 69e01989-2400-82fe-9352-81d562f63a8b (2-Layer composition, visual art direction)

Features:
- Recursive block and child page traversal via ag_notion_bridge
- 3600s in-memory TTL caching per hub
- Persistent local snapshot fallback (/root/video_factory/data/notion_audit/skills_snapshot.json)
- Dedicated getters: get_central_skills(), get_content_engine_rules(), get_media_production_rules(), get_all_skills_bundle()
- Backward-compatible get_skill_rules() alias
"""
import os
import sys
import logging
import time
import json
from pathlib import Path

# Add scripts dir to path for ag_notion_bridge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "scripts"))
import ag_notion_bridge as bridge

logger = logging.getLogger(__name__)

# Canonical Hub IDs
CENTRAL_SKILL_PAGE_ID = "ac901989-2400-827e-bda2-8175dabdcf13"
CONTENT_ENGINE_PAGE_ID = "9bb01989-2400-82c0-9ed4-01f19c7ee23f"
MEDIA_PRODUCTION_PAGE_ID = "69e01989-2400-82fe-9352-81d562f63a8b"
SELF_LEARNING_PAGE_ID = "83cbd0d0-03af-4a60-a765-682a3c5a0a5d"

# Backward compatibility alias
SKILL_AI_PAGE_ID = CENTRAL_SKILL_PAGE_ID

CACHE_TTL_SECONDS = int(os.getenv("SKILL_CACHE_TTL_SECONDS", "3600"))  # 1 hour default
SNAPSHOT_FILE = Path("/root/video_factory/data/notion_audit/skills_snapshot.json")
LEGACY_SNAPSHOT_FILE = Path("/root/video_factory/data/notion_audit/skill_ai.md")

# In-memory multi-hub cache state
_cache = {
    "central": {"data": None, "expiration": 0},
    "content_engine": {"data": None, "expiration": 0},
    "media_production": {"data": None, "expiration": 0},
    "bundle": {"data": None, "expiration": 0},
    "hits": 0,
    "misses": 0
}


def _parse_block_markdown(block: dict) -> str:
    """Parse a single Notion block into clean markdown text."""
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
        return f"  • {text}" if text else ""
    elif btype == "numbered_list_item":
        return f"  1. {text}" if text else ""
    elif btype == "callout":
        return f"> [CALLOUT] {text}" if text else ""
    elif btype == "quote":
        return f"> {text}" if text else ""
    elif btype == "code":
        lang = block.get("code", {}).get("language", "")
        return f"\n```{lang}\n{text}\n```\n" if text else ""
    elif btype == "paragraph":
        return text
    elif btype == "divider":
        return "---"
    return ""


def _fetch_blocks_recursive(block_or_page_id: str, depth: int = 0, max_depth: int = 2, visited: set = None) -> list:
    """Recursively fetch blocks and child pages from Notion."""
    if visited is None:
        visited = set()
    clean_id = block_or_page_id.replace("-", "")
    if clean_id in visited or depth > max_depth:
        return []
    visited.add(clean_id)

    try:
        res = bridge.get_blocks(block_or_page_id, page_size=100)
    except Exception as e:
        logger.warning(f"[skill_loader] Exception fetching blocks for {block_or_page_id}: {e}")
        return []

    if not isinstance(res, dict) or res.get("error"):
        logger.warning(f"[skill_loader] Notion error for {block_or_page_id}: {res.get('message') if isinstance(res, dict) else res}")
        return []

    blocks = res.get("results", [])
    lines = []

    for block in blocks:
        btype = block.get("type")
        if btype == "child_page":
            cp_id = block.get("id")
            title = block.get("child_page", {}).get("title", "Sub-Page")
            lines.append(f"\n### Sub-Page: {title}\n")
            if depth < max_depth and cp_id:
                sub_lines = _fetch_blocks_recursive(cp_id, depth=depth + 1, max_depth=max_depth, visited=visited)
                lines.extend(sub_lines)
        elif btype == "child_database":
            continue
        else:
            txt = _parse_block_markdown(block)
            if txt:
                lines.append(txt)
            if block.get("has_children") and depth < max_depth:
                b_id = block.get("id")
                if b_id:
                    child_lines = _fetch_blocks_recursive(b_id, depth=depth + 1, max_depth=max_depth, visited=visited)
                    lines.extend(child_lines)

    return lines


def _load_snapshot() -> dict:
    """Load local snapshot file if present."""
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"[skill_loader] Failed reading snapshot {SNAPSHOT_FILE}: {e}")
    return {}


def _save_snapshot(hub_key: str, content: str):
    """Save content to the local snapshot file for offline fallback."""
    try:
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = _load_snapshot()
        data[hub_key] = content
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        SNAPSHOT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.debug(f"[skill_loader] Saved offline snapshot for {hub_key}")
    except Exception as e:
        logger.warning(f"[skill_loader] Failed saving snapshot: {e}")


AUTHENTIC_5_ACT_PACING_RULES = """

## Cấu Trúc Dẫn Truyện "Investigative Docudrama" (Hồ Sơ Điều Tra Bất Đối Xứng - Multi-Layer Puzzle)
• Beat 1 / Act I (The Impossible Contradiction - Nghịch Lý Mở Màn 0-60s):
  - Mở đầu bằng một nghịch lý kinh tế/xã hội bất khả thi: một thực thể đứng trên đỉnh cao hoàng kim, số liệu tuyệt hảo, nhưng một vết nứt ngầm không ai ngờ kích hoạt sự sụp đổ.
  - An Ong Hook Protocol (Rule 444): 60 từ đầu tiên kích nổ ngay con số chấn động hoặc câu hỏi điều tra nhức nhối, mở ngay Core Curiosity Loop cực lớn. CẤM mở đầu kiểu giáo khoa.
• Beat 2 / Act II (The False Narrative & Red Herring - Bẫy Truyền Thông & Sai Lầm Đối Thủ):
  - Phơi bày câu chuyện bề nổi mà truyền thông chính thống hoặc các video đối thủ đã kể.
  - Lật tẩy "Red Herring" (manh mối hỏa mù / giả thuyết sai lầm) mà công chúng từng tin sái cổ, chỉ ra tại sao cách giải thích thông thường là nông cạn và né tránh trách nhiệm.
• Beat 3 / Act III (The Systemic Blindspot & Paper Trail - Manh Mối Rò Rỉ & Vết Nứt Thể Chế):
  - Khai quật hồ sơ điều tra thực tế, báo cáo kiểm toán nội bộ, email rò rỉ, cơ chế pháp lý hoặc kẽ hở tài chính mà đối thủ đã bỏ qua (Fatal Explanatory Vacuum).
  - Phân tích động cơ lợi ích thực sự của các nhân vật cốt cán: Ai là kẻ kiếm lời? Ai biết trước thảm họa nhưng im lặng?
• Beat 4 / Act IV (The Real Culprit & Smoking Gun - Cỗ Máy Lợi Ích & Bằng Chứng Vạch Trần):
  - Vạch trần "Smoking Gun" (khẩu súng còn bốc khói): Bằng chứng không thể chối cãi, điểm gãy cấu trúc không thể cứu vãn.
  - Giải phẫu đòn đánh chí mạng / sự kiện sụp đổ không thể đảo ngược, đưa kịch bản lên đỉnh điểm kịch tính (Climax).
• Beat 5 / Act V (The Uncomfortable Modern Mirror & Living Warning - Bản Án & Lời Cảnh Báo Hiện Tại):
  - Bản án lịch sử và bài học bất hủ. Đóng các curiosity loops mở ở Beat 1 (tỷ lệ đóng >= 75-80%).
  - Chiếu chiếc gương soi vào hiện tại: Cơ chế thao túng tương tự đang âm thầm diễn ra ở đâu hôm nay? Lời cảnh tỉnh sâu sắc để lại dư âm mạnh mẽ cho người xem.

## Narrative Loop & Micro-Cliffhanger Discipline
• Mở curiosity loop trong 60 từ đầu tiên và cài cắm Micro-Cliffhanger mỗi 90-120 giây xuyên suốt kịch bản để níu chân người xem.
• Độ dài chuẩn: 1,800 - 2,200 từ (~12-15 phút dẫn chuyện lôi cuốn, giọng văn phóng sự điều tra trung tính, sắc bén, không sáo rỗng).
• Bắt buộc trích dẫn bằng chứng cụ thể: ngày tháng, số liệu định lượng, tên tài liệu/cơ quan điều tra ít nhất 2 lần mỗi Beat."""

TWO_LAYER_VISUAL_RULES = """

## 2-Layer Visual Composition & Remotion Architecture (Rule 116 & Rule 435)
• Layer 1 (Background 16:9 2K DCI 2560x1440): Wide-angle cinematic documentary environment, unobstructed bottom 20% safe-zone for subtitles, clear center-right negative space for foreground character overlay.
• Layer 2 (Foreground 1:1 2048x2048): Stylized editorial graphic novel digital illustration, full-body head-to-shoes standing portrait, on solid #FF00FF pure magenta chroma key.
• Remotion Safe-Zone Subtitle Container: Sole on-screen subtitle mechanism with millisecond karaoke sync. Redundant FFmpeg burning bypassed."""


def _fallback_for_hub(hub_key: str) -> str:
    """Provide a reliable fallback if Notion API is unavailable."""
    snapshot = _load_snapshot()
    if snapshot.get(hub_key):
        content = snapshot[hub_key]
        if hub_key == "content_engine" and ("5-Act" not in content and "5-act" not in content.lower()):
            content = f"{content}{AUTHENTIC_5_ACT_PACING_RULES}".strip()
        elif hub_key == "media_production" and ("Layer 1" not in content and "2-Layer" not in content):
            content = f"{content}{TWO_LAYER_VISUAL_RULES}".strip()
        logger.info(f"[skill_loader] Using offline snapshot for {hub_key}")
        return content

    if hub_key == "central" and LEGACY_SNAPSHOT_FILE.exists():
        try:
            logger.info(f"[skill_loader] Using legacy markdown snapshot for central skills")
            return LEGACY_SNAPSHOT_FILE.read_text(encoding="utf-8")
        except Exception:
            pass

    # Built-in authoritative fallbacks aligned with Notion SoT
    if hub_key == "content_engine":
        return (
            """# Content Engine Hub (Fallback Snapshot)
## 5 HARD Rules
1. Brand voice before content — Never draft an article or script without first defining tone and audience.
2. Fact-check before publish — Any factual claim (statistics, dates, names) MUST be verified.
3. No AI disclosure bypass — Comply strictly with synthetic media disclosure mandates.
4. No publish without quality gate — Story gate score must meet threshold (score >= 8/10).
5. Platform spec compliance — Length, tags, character limits strictly enforced.
"""
            + AUTHENTIC_5_ACT_PACING_RULES.strip()
        )
    elif hub_key == "media_production":
        return (
            """# Media Production Hub (Fallback Snapshot)
## 5 HARD Rules
1. Aspect ratio lock — 16:9 for documentary master (2560x1440 or 1920x1080).
2. Script before render — Narration copy must exist and pass quality gates before rendering.
3. Offline render only — Render locally on CPU/GPU, probe integrity before upload.
4. No hardcoded configuration — All runtime settings loaded via environment variables.
5. Version every output — Version all artifacts (final_169.mp4, remotion_props.json).
"""
            + TWO_LAYER_VISUAL_RULES.strip()
        )
    return ""


def get_central_skills(force_refresh: bool = False) -> str:
    """Get Rules 113-121 and Core Editorial Principles from Central Skill AI page.
    
    Target: CENTRAL_SKILL_PAGE_ID ('ac901989-2400-827e-bda2-8175dabdcf13')
    """
    global _cache
    now = time.time()
    entry = _cache["central"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    logger.info("[skill_loader] Fetching Central Skills from Notion...")

    try:
        lines = _fetch_blocks_recursive(CENTRAL_SKILL_PAGE_ID, depth=0, max_depth=1)
        content = "\n".join(lines).strip()
        if content:
            # Ensure Rule 120 is explicitly referenced if not already present in raw Notion blocks
            if "Rule 120" not in content:
                rule_120_text = (
                    "\n\n### Rule 120 — Prompt Engineering Isolation & Subtitle Karaoke Sync (23/08/2026)\n"
                    "• Foregrounds strictly generated on #FF00FF pure magenta chroma key background.\n"
                    "• Remotion safe-zone box with word-level karaoke sync; eliminate redundant FFmpeg subtitle burning.\n"
                    "• Complete removal of legacy VPS visual engine; browser-driven generation with 3-5s spacing.\n"
                )
                content += rule_120_text

            entry["data"] = content
            entry["expiration"] = now + CACHE_TTL_SECONDS
            _save_snapshot("central", content)
            logger.info(f"[skill_loader] Loaded {len(content)} chars from Central Skill AI")
            return content
    except Exception as e:
        logger.warning(f"[skill_loader] Exception during central skill fetch: {e}")

    fallback = _fallback_for_hub("central")
    entry["data"] = fallback
    entry["expiration"] = now + 300  # Shorter TTL for fallback
    return fallback


def get_content_engine_rules(force_refresh: bool = False) -> str:
    """Get 5-Act narrative structure, pacing, and loop discipline from Content Engine Hub.
    
    Target: CONTENT_ENGINE_PAGE_ID ('9bb01989-2400-82c0-9ed4-01f19c7ee23f')
    """
    global _cache
    now = time.time()
    entry = _cache["content_engine"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    logger.info("[skill_loader] Fetching Content Engine Hub from Notion...")

    content = ""
    try:
        lines = _fetch_blocks_recursive(CONTENT_ENGINE_PAGE_ID, depth=0, max_depth=1)
        content = "\n".join(lines).strip()
        if content:
            logger.info(f"[skill_loader] Loaded {len(content)} chars from Content Engine Hub")
    except Exception as e:
        logger.warning(f"[skill_loader] Exception during Content Engine fetch: {e}")

    if not content:
        content = _fallback_for_hub("content_engine")

    # ALWAYS ensure authentic 5-Act narrative pacing rules are merged with raw Notion text
    # so B2 Story Engine never loses the 5-Act structure
    if "5-Act" not in content and "5-act" not in content.lower():
        content = f"{content}{AUTHENTIC_5_ACT_PACING_RULES}".strip()
    elif "curiosity loop" not in content.lower() or "first 60 words" not in content.lower():
        content = f"{content}{AUTHENTIC_5_ACT_PACING_RULES}".strip()

    entry["data"] = content
    entry["expiration"] = now + CACHE_TTL_SECONDS
    _save_snapshot("content_engine", content)
    return content


def get_media_production_rules(force_refresh: bool = False) -> str:
    """Get 2-Layer composition, visual art direction, and chroma keying rules from Media Production Hub.
    
    Target: MEDIA_PRODUCTION_PAGE_ID ('69e01989-2400-82fe-9352-81d562f63a8b')
    """
    global _cache
    now = time.time()
    entry = _cache["media_production"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    _cache["misses"] += 1
    logger.info("[skill_loader] Fetching Media Production Hub from Notion...")

    content = ""
    try:
        lines = _fetch_blocks_recursive(MEDIA_PRODUCTION_PAGE_ID, depth=0, max_depth=1)
        content = "\n".join(lines).strip()
        if content:
            logger.info(f"[skill_loader] Loaded {len(content)} chars from Media Production Hub")
    except Exception as e:
        logger.warning(f"[skill_loader] Exception during Media Production fetch: {e}")

    if not content:
        content = _fallback_for_hub("media_production")

    # Ensure 2-Layer composition rules are merged with raw Notion text
    if "Layer 1" not in content and "2-Layer" not in content:
        content = f"{content}{TWO_LAYER_VISUAL_RULES}".strip()

    entry["data"] = content
    entry["expiration"] = now + CACHE_TTL_SECONDS
    _save_snapshot("media_production", content)
    return content


def get_all_skills_bundle(force_refresh: bool = False) -> str:
    """Assembles a unified markdown bundle containing Central Skills, Content Engine, and Media Production rules."""
    global _cache
    now = time.time()
    entry = _cache["bundle"]

    if not force_refresh and entry["data"] is not None and now < entry["expiration"]:
        _cache["hits"] += 1
        return entry["data"]

    central = get_central_skills(force_refresh=force_refresh)
    content_engine = get_content_engine_rules(force_refresh=force_refresh)
    media_production = get_media_production_rules(force_refresh=force_refresh)

    bundle = (
        "# VIDEO FACTORY SINGLE SOURCE OF TRUTH (NOTION SOT SKILL BUNDLE)\n\n"
        "## I. CENTRAL SKILL AI (RULES 113-121)\n"
        f"{central}\n\n"
        "## II. CONTENT ENGINE HUB (5-ACT ARCHITECTURE & NARRATIVE DISCIPLINE)\n"
        f"{content_engine}\n\n"
        "## III. MEDIA PRODUCTION HUB (2-LAYER VISUAL DIRECTION & REMOTION)\n"
        f"{media_production}\n"
    )

    entry["data"] = bundle
    entry["expiration"] = now + CACHE_TTL_SECONDS
    return bundle


def get_skill_rules(force_refresh: bool = False) -> str:
    """Backward-compatible wrapper returning dynamic Central Skills rules."""
    return get_central_skills(force_refresh=force_refresh)


def get_cache_info() -> dict:
    """Get cache statistics for monitoring."""
    global _cache
    now = time.time()

    hubs_info = {}
    for key in ("central", "content_engine", "media_production", "bundle"):
        c = _cache[key]
        has_data = c["data"] is not None
        rem = max(0, int(c["expiration"] - now)) if has_data else 0
        hubs_info[key] = {
            "cached": has_data,
            "char_count": len(c["data"]) if has_data else 0,
            "remaining_seconds": rem
        }

    return {
        "hits": _cache["hits"],
        "misses": _cache["misses"],
        "ttl_seconds": CACHE_TTL_SECONDS,
        "hubs": hubs_info
    }




def get_b11_self_learning_rules(force_refresh: bool = False) -> str:
    """Fetch actionable post-mortem lessons from Notion B11 Self-Learning Loop (83cbd0d0-03af-4a60-a765-682a3c5a0a5d)."""
    global _cache
    now = time.time()
    if not force_refresh and _cache.get("self_learning", {}).get("data") and now < _cache.get("self_learning", {}).get("expiration", 0):
        return _cache["self_learning"]["data"]

    try:
        lines = _fetch_blocks_recursive(SELF_LEARNING_PAGE_ID, depth=0, max_depth=1)
        if not lines:
            return ""
        filtered = [l for l in lines if len(l.strip()) > 15]
        text = chr(10).join(filtered[:25]).strip()
        if text:
            _cache["self_learning"] = {"data": text, "expiration": now + CACHE_TTL_SECONDS}
            return text
    except Exception as e:
        logger.warning(f"[skill_loader] Failed to fetch B11 self-learning rules: {e}")
    return ""


def get_b2_editorial_skills(force_refresh: bool = False) -> str:
    """Return high-density, targeted editorial skill prompts for B2 Story Engine.
    Combines Notion Content Engine Hub narrative rules, Central Brain rules
    (Rule 1-4, 78 Big Fish Small Pond, Rule 118 Truth Anchor, Rule 444 Hook Protocol),
    and B11 Self-Learning post-mortem feedback dynamically.
    """
    ce_rules = get_content_engine_rules(force_refresh=force_refresh)
    b11_lessons = get_b11_self_learning_rules(force_refresh=force_refresh)
    
    b11_section = ""
    if b11_lessons:
        b11_section = (
            "\n\n=== 5. B11 CONTINUOUS SELF-LEARNING LESSONS (LIVE NOTION FEEDBACK) ===\n"
            f"{b11_lessons[:1500]}\n"
        )

    editorial_prompt = (
        "=== B2 EDITORIAL & CINEMATIC NARRATIVE MANDATES ===\n"
        "1. RULE 1, 2, 3, 4, 78 (BIG FISH SMALL POND - CAUSAL MECHANISM):\n"
        "   - Never narrate surface events chronologically like a boring encyclopedia. Dissect the underlying structural mechanism:\n"
        "     the regulatory loophole, the financial incentive structure, or the psychological vulnerability.\n"
        "   - The story is NOT about the person; the story is about the SYSTEMIC MACHINE that made the crisis inevitable.\n"
        "   - Ground all statements in verified historical/economic facts; zero speculative gossip.\n\n"
        "2. RULE 444 (AN ONG HOOK PROTOCOL - COLD TRAFFIC HOOK 5-10 SECONDS):\n"
        "   - The very first sentence of Act I MUST open with a shock quantitative stake, specific economic contradiction, or irreconcilable conflict.\n"
        "   - ZERO generic preamble ('In the quiet town of...', 'Throughout history...', 'In today\'s world...').\n"
        "   - Hook mobile viewers immediately with an inescapable, high-stakes puzzle.\n\n"
        "3. CINEMATIC TENSION & SCENE-LEVEL DRAMA (ANTI-BLAND DIRECTIVE):\n"
        "   - Banish dry passive summary. Anchor every Act in specific human decisions, ticking clocks, and irreversible bets.\n"
        "   - Micro-Cliffhangers: End Act I, Act II, and Act III with an unresolved revelation or friction point that forces the viewer to keep watching.\n"
        "   - Visual Staging: Describe scenes with concrete physical reality (exact boardroom meetings, panicked trading desks, leaked memos, court transcripts) so Remotion visuals can pair seamlessly.\n\n"
        "4. CẤU TRÚC DẪN TRUYỆN INVESTIGATIVE DOCUDRAMA (HỒ SƠ ĐIỀU TRA BẤT ĐỐI XỨNG - MULTI-LAYER PUZZLE):\n"
        "   - Beat 1 / Act I (The Impossible Contradiction): Mở màn nghịch lý phi lý 0-60s, con số chấn động/xung đột bất khả thi, mở Core Curiosity Loop (Rule 444 An Ong Hook).\n"
        "   - Beat 2 / Act II (The False Narrative & Red Herring): Lật tẩy bẫy truyền thông và sai lầm đối thủ, bóc trần manh mối hỏa mù.\n"
        "   - Beat 3 / Act III (The Systemic Blindspot & Paper Trail): Khai quật kẽ hở thể chế, tài liệu/báo cáo rò rỉ (Fatal Explanatory Vacuum) đối thủ bỏ qua.\n"
        "   - Beat 4 / Act IV (The Real Culprit & Smoking Gun): Vạch trần khẩu súng còn bốc khói, cỗ máy lợi ích thật sự, điểm gãy chí mạng (Climax).\n"
        "   - Beat 5 / Act V (The Uncomfortable Modern Mirror & Living Warning): Chiếu chiếc gương soi vào hiện tại, đóng curiosity loops (>=75-80%), lời cảnh báo nhức nhối.\n"
        "   - Micro-Cliffhangers: Cài cắm điểm thắt/tò mò mỗi 90-120 giây xuyên suốt kịch bản để giữ chân người xem.\n"
        "   - Target Word Count: 1,800 - 2,200 từ (~12-15 phút narration) phân bổ đều cho 5 Acts.\n"
        "   - Tone & Style: Phóng sự điều tra độc lập, sắc bén, khách quan, giàu bằng chứng tài liệu/số liệu cụ thể.\n"
        "   - Anti-AI Mandate: ZERO banned cliches (delve, testament, tapestry, crucible, beacon, in conclusion).\n"
        f"{b11_section}\n"
        "=== DETAILED CONTENT ENGINE RULES FROM NOTION SOT ===\n"
        f"{ce_rules[:3500]}"
    )
    return editorial_prompt


def clear_cache():
    """Manually clear all cached rules."""
    global _cache
    for key in ("central", "content_engine", "media_production", "bundle"):
        _cache[key]["data"] = None
        _cache[key]["expiration"] = 0
    logger.info("[skill_loader] All multi-hub caches cleared")


if __name__ == "__main__":
    print("Testing Multi-Hub Skill Loader...")
    print("=" * 60)

    start = time.time()
    c_skills = get_central_skills()
    t1 = time.time() - start
    print(f"✅ Central Skills: {len(c_skills)} chars in {t1:.2f}s")

    start = time.time()
    ce_rules = get_content_engine_rules()
    t2 = time.time() - start
    print(f"✅ Content Engine Rules: {len(ce_rules)} chars in {t2:.2f}s")

    start = time.time()
    mp_rules = get_media_production_rules()
    t3 = time.time() - start
    print(f"✅ Media Production Rules: {len(mp_rules)} chars in {t3:.2f}s")

    start = time.time()
    bundle = get_all_skills_bundle()
    t4 = time.time() - start
    print(f"✅ Full Skills Bundle: {len(bundle)} chars in {t4:.4f}s")

    print("\nCache Info:")
    print(json.dumps(get_cache_info(), indent=2))
