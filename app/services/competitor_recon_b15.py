#!/usr/bin/env python3
"""B1.5 - Competitor Recon & Gap Analysis (Claude Haiku Synthesizer).

Input: task_id (en-SLUG) + target_keyword
Output: competitor_intel_card.json → B2 prompt

Fetches 5-7 competitor videos via YouTube Data API, extracts:
- Search metadata & hook pacing
- Audience comment gaps (unanswered questions, frustrations)
- Golden facts + 10x angle proposal

Loads YouTube API key from env (YT_UPLOAD_API_KEY per market).
Falls back to yt-dlp when quota >80%.
"""
import os
import sys
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_env():
    """Load /root/secrets/.env per youtube_upload.py pattern."""
    p = "/root/secrets/.env"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_api_key(market="en") -> Optional[str]:
    """Return YouTube Data API key for market (en/jp/kr)."""
    market = (market or "en").lower().strip()
    key = os.environ.get("YT_UPLOAD_API_KEY")
    if not key:
        logger.warning("[b15] YT_UPLOAD_API_KEY not set")
    return key


def youtube_search(api_key: str, query: str, max_results: int = 5) -> List[Dict]:
    """Search YouTube videos via Data API."""
    import urllib.parse
    import urllib.request
    import json as json_lib

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "viewCount",
        "key": api_key,
    }
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json_lib.load(r)
        items = data.get("items", [])
        logger.info("[b15] search returned %d items", len(items))
        return [
            {
                "video_id": it["id"]["videoId"],
                "channel": it["snippet"]["channelTitle"],
                "title": it["snippet"]["title"],
                "published_at": it["snippet"]["publishedAt"],
            }
            for it in items
        ]
    except Exception as e:
        logger.error("[b15] search failed: %s", e)
        return []


def youtube_video_details(api_key: str, video_ids: List[str]) -> Dict[str, Dict]:
    """Fetch views, comments, duration for videos."""
    import urllib.parse
    import urllib.request
    import json as json_lib

    results = {}
    for vid in video_ids:
        params = {
            "part": "statistics,snippet,contentDetails",
            "id": vid,
            "key": api_key,
        }
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json_lib.load(r)
            if data.get("items"):
                it = data["items"][0]
                results[vid] = {
                    "views": int(it["statistics"].get("viewCount", 0)),
                    "comments": int(it["statistics"].get("commentCount", 0)),
                    "published_at": it["snippet"]["publishedAt"],
                    "duration": it["contentDetails"]["duration"],
                }
        except Exception as e:
            logger.debug("[b15] video_details error for %s: %s", vid, e)
    return results


def youtube_comments(api_key: str, video_id: str, max_results: int = 10) -> List[Dict]:
    """Fetch top comments (by relevance)."""
    import urllib.parse
    import urllib.request
    import json as json_lib

    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "relevance",
        "key": api_key,
    }
    url = "https://www.googleapis.com/youtube/v3/commentThreads?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json_lib.load(r)
        items = data.get("items", [])
        comments = []
        for it in items:
            snippet = it["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "text": snippet["textOriginal"],
                "likes": int(snippet["likeCount"]),
                "author": snippet["authorDisplayName"],
            })
        logger.info("[b15] fetched %d comments for %s", len(comments), video_id)
        return comments
    except Exception as e:
        logger.debug("[b15] comments error for %s: %s", video_id, e)
        return []


def filter_comment_gaps(comments: List[Dict], min_likes: int = 3) -> List[Dict]:
    """Extract unanswered questions & frustrations from comments."""
    gaps = []
    keywords = ["why", "how", "missed", "didn't explain", "confused", "unclear"]
    
    for c in comments:
        text = c["text"].lower()
        likes = c["likes"]
        if likes >= min_likes and any(kw in text for kw in keywords):
            gaps.append({
                "text": c["text"],
                "likes": likes,
                "author": c["author"],
            })
    return gaps


OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
HAIKU_MODEL = os.environ.get("B15_SYNTH_MODEL", "anthropic/claude-haiku-4.5")

SYNTH_SCHEMA = {
    "type": "object",
    "properties": {
        "competitor_analysis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "video_id": {"type": "string"},
                    "hook_strategy": {"type": "string"},
                    "critical_flaw": {"type": "string"},
                },
                "required": ["video_id", "hook_strategy", "critical_flaw"],
                "additionalProperties": False,
            },
        },
        "golden_facts_to_keep": {"type": "array", "items": {"type": "string"}},
        "audience_comment_gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "unanswered_question": {"type": "string"},
                    "viewer_frustration": {"type": "string"},
                },
                "required": ["unanswered_question", "viewer_frustration"],
                "additionalProperties": False,
            },
        },
        "recommended_10x_angle": {
            "type": "object",
            "properties": {
                "hook_proposal": {"type": "string"},
                "core_mechanism_to_clarify": {"type": "string"},
                "differentiator": {"type": "string"},
            },
            "required": ["hook_proposal", "core_mechanism_to_clarify", "differentiator"],
            "additionalProperties": False,
        },
    },
    "required": [
        "competitor_analysis",
        "golden_facts_to_keep",
        "audience_comment_gaps",
        "recommended_10x_angle",
    ],
    "additionalProperties": False,
}

SYNTH_SYSTEM_PROMPT = (
    "You are the B1.5 Recon Synthesizer for a documentary video factory. "
    "You receive REAL YouTube competitor metrics and REAL viewer comments. "
    "Rules: (1) Never invent a statistic, quote or timestamp that is absent from the input. "
    "(2) unanswered_question MUST be a verbatim excerpt of a supplied comment. "
    "(3) golden_facts_to_keep must be traceable to the supplied titles or comments. "
    "(4) critical_flaw must name a concrete, checkable weakness, not a generic complaint. "
    "Answer in English."
)


def call_haiku(prompt, system_prompt, schema, max_tokens=2000, timeout=180.0):
    """Call Claude Haiku via OpenRouter under a strict JSON schema. Returns dict or None."""
    import urllib.request
    import urllib.error

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        logger.error("[b15] OPENROUTER_API_KEY not set, cannot run Haiku synthesis")
        return None

    payload = {
        "model": HAIKU_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "b15_intel", "strict": True, "schema": schema},
        },
    }
    req = urllib.request.Request(
        OPENROUTER_BASE_URL + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        logger.error("[b15] Haiku HTTP %s: %s", e.code, body)
        return None
    except Exception as e:
        logger.error("[b15] Haiku call failed: %s", e)
        return None

    usage = data.get("usage") or {}
    logger.info("[b15] Haiku usage: %s tokens, cost %s", usage.get("total_tokens"), usage.get("cost"))
    try:
        return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        logger.error("[b15] Haiku returned unparseable content: %s", e)
        return None


def build_synth_prompt(target_keyword, niche, benchmarks, gaps):
    """Render the real collected data into the synthesizer prompt."""
    lines = [
        "TARGET KEYWORD: " + str(target_keyword),
        "NICHE: " + str(niche),
        "",
        "COMPETITOR VIDEOS (real YouTube Data API metrics):",
    ]
    for b in benchmarks:
        lines.append(
            "- video_id=%s | channel=%s | title=%s | views=%d | comments=%d | published=%s | views_per_day=%d"
            % (
                b.get("video_id", ""),
                b.get("channel", ""),
                b.get("title", ""),
                b.get("views", 0),
                b.get("comments", 0),
                b.get("published_at", ""),
                b.get("avg_views_per_day", 0),
            )
        )
    lines += ["", "REAL VIEWER COMMENTS (verbatim, with like counts):"]
    if gaps:
        for g in gaps:
            flat = " ".join(str(g.get("text", "")).split())
            lines.append("- [%d likes] %s" % (g.get("likes", 0), flat[:400]))
    else:
        lines.append("- (none passed the gap filter)")
    lines += [
        "",
        "TASK:",
        "1. For EACH video_id above, infer hook_strategy from its title and metrics, and name its single most important critical_flaw as a documentary source.",
        "2. Extract golden_facts_to_keep: concrete factual anchors worth preserving in our own script.",
        "3. For each supplied comment revealing a content gap, output unanswered_question (verbatim excerpt) plus viewer_frustration (what the viewer actually wanted).",
        "4. Propose a recommended_10x_angle that beats every video above.",
    ]
    return "\n".join(lines)


def apply_haiku_synthesis(card, target_keyword, niche, gaps):
    """Replace the card's analytical fields with real Haiku output."""
    benchmarks = card.get("competitor_benchmarks") or []
    if not benchmarks:
        card["synthesis_status"] = "skipped_no_benchmarks"
        return card

    prompt = build_synth_prompt(target_keyword, niche, benchmarks, gaps[:8])
    out = call_haiku(prompt, SYNTH_SYSTEM_PROMPT, SYNTH_SCHEMA)
    if not out:
        card["synthesis_status"] = "haiku_failed"
        return card

    by_id = {}
    for a in out.get("competitor_analysis") or []:
        if a.get("video_id"):
            by_id[a["video_id"]] = a
    for b in benchmarks:
        a = by_id.get(b.get("video_id"))
        if a:
            b["hook_strategy"] = a.get("hook_strategy", "")
            b["critical_flaw"] = a.get("critical_flaw", "")

    facts = out.get("golden_facts_to_keep") or []
    if facts:
        card["golden_facts_to_keep"] = facts

    synth_gaps = out.get("audience_comment_gaps") or []
    if synth_gaps:
        merged = []
        for sg in synth_gaps:
            q = sg.get("unanswered_question", "")
            likes = 0
            probe = q[:30]
            for g in gaps:
                if probe and probe in g.get("text", ""):
                    likes = g.get("likes", 0)
                    break
            merged.append({
                "unanswered_question": q,
                "viewer_frustration": sg.get("viewer_frustration", ""),
                "likes_count": likes,
            })
        card["audience_comment_gaps"] = merged

    angle = out.get("recommended_10x_angle") or {}
    if angle:
        card["recommended_10x_angle"] = angle

    card["synthesis_status"] = "haiku_ok"
    card["synthesis_model"] = HAIKU_MODEL
    return card


def synthesize_intel_card(
    task_id: str,
    target_keyword: str,
    niche: str,
    competitors: List[Dict],
    gaps: List[Dict],
    use_haiku: bool = True,
) -> Dict:
    """Compile competitor intelligence card (Haiku-ready schema)."""
    # Calculate Velocity for each competitor
    benchmarks = []
    for comp in competitors:
        if comp.get("published_at"):
            try:
                pub = datetime.fromisoformat(comp["published_at"].replace("Z", "+00:00"))
                age_days = (datetime.now(pub.tzinfo) - pub).days or 1
                velocity = comp.get("views", 0) / age_days
                benchmarks.append({
                    "video_id": comp["video_id"],
                    "channel": comp["channel"],
                    "title": comp["title"],
                    "views": comp.get("views", 0),
                    "comments": comp.get("comments", 0),
                    "published_at": comp["published_at"],
                    "avg_views_per_day": round(velocity),
                    "hook_strategy": "",
                    "critical_flaw": "",
                })
            except Exception as e:
                logger.debug("[b15] velocity calc error: %s", e)
    
    # Extract golden facts from comments (real quotes)
    golden_facts = []
    for gap in gaps[:3]:
        if len(gap["text"]) > 20:
            golden_facts.append(gap["text"][:100])
    
    # Build card
    card = {
        "task_id": task_id,
        "target_keyword": target_keyword,
        "niche": niche,
        "competitor_benchmarks": benchmarks[:5],
        "golden_facts_to_keep": golden_facts,
        "audience_comment_gaps": [
            {
                "unanswered_question": g["text"][:150],
                "viewer_frustration": "",
                "likes_count": g["likes"],
            }
            for g in gaps[:5]
        ],
        "recommended_10x_angle": {
            "hook_proposal": "",
            "core_mechanism_to_clarify": "",
            "differentiator": "",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "synthesis_status": "pending",
    }

    if not use_haiku:
        card["synthesis_status"] = "disabled"
        return card
    return apply_haiku_synthesis(card, target_keyword, niche, gaps)


async def run_b15(task_id: str, target_keyword: str, niche: str = "General") -> Optional[Dict]:
    """Main B1.5 orchestrator."""
    load_env()
    market = task_id.split("-")[0] if "-" in task_id else "en"
    
    logger.info("[b15] Starting for task_id=%s keyword=%s market=%s", task_id, target_keyword, market)
    
    api_key = get_api_key(market)
    if not api_key:
        logger.error("[b15] No API key available")
        return None
    
    # 1. Search competitors
    competitors_search = youtube_search(api_key, target_keyword, max_results=7)
    if not competitors_search:
        logger.warning("[b15] No competitors found")
        return None
    
    # 2. Fetch details (views, comments, duration)
    video_ids = [c["video_id"] for c in competitors_search]
    details = youtube_video_details(api_key, video_ids)
    for c in competitors_search:
        c.update(details.get(c["video_id"], {}))
    
    # 3. Extract audience comment gaps (top 3 videos)
    all_gaps = []
    for c in competitors_search[:3]:
        comments = youtube_comments(api_key, c["video_id"], max_results=10)
        gaps = filter_comment_gaps(comments, min_likes=3)
        all_gaps.extend(gaps)
    
    # 4. Synthesize intel card
    card = synthesize_intel_card(
        task_id=task_id,
        target_keyword=target_keyword,
        niche=niche,
        competitors=competitors_search,
        gaps=all_gaps,
    )
    
    logger.info("[b15] Intel card synthesized: %d competitors, %d comment gaps", 
                len(card["competitor_benchmarks"]), len(card["audience_comment_gaps"]))
    return card


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 competitor_recon_b15.py <task_id> <target_keyword> [niche]")
        print("Example: python3 competitor_recon_b15.py en-enron-collapse-ep006 'Enron Scandal Explained' 'Corporate Crime'")
        sys.exit(1)
    
    task_id = sys.argv[1]
    target_keyword = sys.argv[2]
    niche = sys.argv[3] if len(sys.argv) > 3 else "General"
    
    import asyncio
    card = asyncio.run(run_b15(task_id, target_keyword, niche))
    
    if card:
        out_dir = Path(f"/var/vf/episodes/{task_id}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "competitor_intel_card.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(card, f, ensure_ascii=False, indent=2)
        print(f"✅ Intel card saved to {out_path}")
        print(json.dumps(card, indent=2, ensure_ascii=False)[:500] + "...")
    else:
        logger.error("[b15] Failed to synthesize intel card")
        sys.exit(1)


if __name__ == "__main__":
    main()
