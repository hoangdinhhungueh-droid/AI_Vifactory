"""
B1.5: Competitor Recon & Gap Analysis (DATA COLLECTION ONLY).

Collects raw competitor evidence for a keyword approved at B1 and writes a
`competitor_intel_card.json` that B2 (story_engine_b2.py) consumes.

Four pillars, per VF_PIPELINE_B1.5_COMPETITOR_RECON_SPEC.md:
  1. Metadata & search intent   -> YouTube Data API search.list + videos.list
  2. Transcript & hook pacing   -> youtube-transcript-api, else yt-dlp -x + Faster-Whisper
  3. Audience comment mining    -> commentThreads.list + regex prefilter
  4. Thumbnail visual recon     -> download image to disk for Antigravity vision audit

This module does NOT interpret the evidence. Judgement calls (critical_flaw,
10x angle, hook rewrite) belong to B2 (GPT-5.6-Sol) and to the Antigravity
vision audit at B5. Fields reserved for them are emitted under
`_b2_to_synthesize` so a downstream reader can never mistake an empty slot
for a finding.

Rule 118: every value in the card is fetched, never invented. When a source is
unreachable the card records the failure (e.g. transcript_status="unavailable")
instead of substituting placeholder prose.
"""
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SECRETS_ENV = "/root/secrets/.env"
CACHE_DIR = Path("/var/vf/b15_cache")
EPISODE_DIR = Path("/var/vf/episodes")
YTDLP_BIN = "/root/video_factory/venv/bin/yt-dlp"

# YouTube Data API v3 daily quota and per-call unit costs.
QUOTA_DAILY_UNITS = 10_000
QUOTA_COST = {"search": 100, "videos": 1, "commentThreads": 1}
QUOTA_FALLBACK_RATIO = 0.80

# PHAN IV selection formula.
RECENT_WINDOW_MIN_DAYS = 90
RECENT_WINDOW_MAX_DAYS = 365
RECENT_MIN_COMMENTS = 100
GROUP1_ALLTIME_COUNT = 2
GROUP2_RECENT_COUNT = 5

# PHAN III item 3: comment prefilter.
COMMENT_MIN_LENGTH = 30
COMMENT_MIN_LIKES = 3
QUESTION_KEYWORDS = (
    "why", "how", "missed", "didn't explain", "didnt explain", "did not explain",
    "confused", "confusing", "unclear", "what about", "never explained",
    "still don't understand", "makes no sense",
)
SPAM_PATTERNS = (
    re.compile(r"https?://", re.I),
    re.compile(r"\bwww\.", re.I),
    re.compile(r"\b(subscribe to|check out my|follow me|promo\s?code)\b", re.I),
    re.compile(r"[\U0001F300-\U0001FAFF]{4,}"),
)

# Market prefix -> YouTube locale hints (PHAN III item 4).
MARKET_LOCALE = {
    "en": {"relevanceLanguage": "en", "regionCode": "US", "transcript_langs": ["en"]},
    "jp": {"relevanceLanguage": "ja", "regionCode": "JP", "transcript_langs": ["ja", "en"]},
    "kr": {"relevanceLanguage": "ko", "regionCode": "KR", "transcript_langs": ["ko", "en"]},
}


def load_env() -> None:
    """Populate os.environ from /root/secrets/.env (youtube_upload.py pattern)."""
    if not os.path.exists(SECRETS_ENV):
        return
    with open(SECRETS_ENV) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def market_of(task_id: str) -> str:
    """Read the en-/jp-/kr- or EN_/JP_/KR_ prefix off a task id, defaulting to en."""
    t = task_id.strip()
    # Check underscore first (e.g. KR_EP0001_...)
    if "_" in t:
        p = t.split("_", 1)[0].lower()
        if p in MARKET_LOCALE:
            return p
    # Check hyphen (e.g. kr-samsung-...)
    if "-" in t:
        p = t.split("-", 1)[0].lower()
        if p in MARKET_LOCALE:
            return p
    return "en"


def get_api_key() -> Optional[str]:
    key = os.environ.get("YT_UPLOAD_API_KEY")
    if not key:
        logger.warning("[b15] YT_UPLOAD_API_KEY not set in %s", SECRETS_ENV)
    return key


class QuotaTracker:
    """Counts API units spent today and flags when yt-dlp fallback should engage."""

    def __init__(self, state_path: Path = CACHE_DIR / "quota.json"):
        self.state_path = state_path
        self.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.spent = 0
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.state_path.read_text())
            if data.get("date") == self.date:
                self.spent = int(data.get("spent", 0))
        except (OSError, ValueError, TypeError):
            pass

    def charge(self, endpoint: str) -> None:
        self.spent += QUOTA_COST.get(endpoint, 1)
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"date": self.date, "spent": self.spent}))
        except OSError as e:
            logger.debug("[b15] could not persist quota state: %s", e)

    @property
    def ratio(self) -> float:
        return self.spent / QUOTA_DAILY_UNITS

    def should_fallback(self) -> bool:
        return self.ratio >= QUOTA_FALLBACK_RATIO


def _api_get(endpoint: str, params: Dict, quota: QuotaTracker) -> Optional[Dict]:
    """One YouTube Data API GET. Returns parsed JSON, or None on failure."""
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = json.load(r)
        quota.charge(endpoint)
        return body
    except Exception as e:
        detail = ""
        if hasattr(e, "read"):
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
        logger.error("[b15] %s failed: %s %s", endpoint, e, detail)
        return None


def youtube_search(api_key: str, query: str, market: str, quota: QuotaTracker,
                   max_results: int = 25) -> List[Dict]:
    """Pillar 1: candidate pool, ordered by view count with automatic query relaxation fallback."""
    locale = MARKET_LOCALE[market]
    
    # Try queries: original, then relaxed subsets
    queries_to_try = [query]
    words = query.strip().split()
    if len(words) > 3:
        queries_to_try.append(" ".join(words[:3]))
    if len(words) > 2:
        queries_to_try.append(" ".join(words[:2]))
    if len(words) > 1:
        queries_to_try.append(words[0])
        
    for q_attempt in queries_to_try:
        body = _api_get("search", {
            "part": "snippet",
            "q": q_attempt,
            "type": "video",
            "maxResults": max_results,
            "order": "viewCount",
            "relevanceLanguage": locale["relevanceLanguage"],
            "regionCode": locale["regionCode"],
            "key": api_key,
        }, quota)
        items = body.get("items", []) if body else []
        if items:
            logger.info("[b15.p1] search returned %d candidates for query %r (market=%s)", len(items), q_attempt, market)
            return [{
                "video_id": it["id"]["videoId"],
                "channel": it["snippet"]["channelTitle"],
                "title": it["snippet"]["title"],
                "published_at": it["snippet"]["publishedAt"],
                "thumbnails": it["snippet"].get("thumbnails", {}),
            } for it in items if "videoId" in it.get("id", {})]
            
    logger.info("[b15.p1] search returned 0 candidates for all query variants of %r (market=%s)", query, market)
    return []


def youtube_video_details(api_key: str, video_ids: List[str], quota: QuotaTracker) -> Dict[str, Dict]:
    """Pillar 1: statistics for up to 50 ids per call."""
    out: Dict[str, Dict] = {}
    for chunk_start in range(0, len(video_ids), 50):
        chunk = video_ids[chunk_start:chunk_start + 50]
        body = _api_get("videos", {
            "part": "statistics,snippet,contentDetails",
            "id": ",".join(chunk),
            "key": api_key,
        }, quota)
        if not body:
            continue
        for it in body.get("items", []):
            stats = it.get("statistics", {})
            out[it["id"]] = {
                "views": int(stats.get("viewCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "published_at": it["snippet"]["publishedAt"],
                "duration": it["contentDetails"]["duration"],
                "tags": it["snippet"].get("tags", [])[:20],
                "description_head": (it["snippet"].get("description") or "")[:400],
                "thumbnails": it["snippet"].get("thumbnails", {}),
            }
    logger.info("[b15.p1] details resolved for %d/%d videos", len(out), len(video_ids))
    return out


def youtube_comments(api_key: str, video_id: str, quota: QuotaTracker,
                     max_results: int = 50) -> List[Dict]:
    """Pillar 3: top comments by relevance."""
    body = _api_get("commentThreads", {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "relevance",
        "textFormat": "plainText",
        "key": api_key,
    }, quota)
    if not body:
        return []
    comments = []
    for it in body.get("items", []):
        s = it["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "text": s["textOriginal"],
            "likes": int(s.get("likeCount", 0)),
            "author": s.get("authorDisplayName", ""),
            "published_at": s.get("publishedAt"),
        })
    logger.info("[b15.p3] fetched %d comments for %s", len(comments), video_id)
    return comments


def is_spam(text: str) -> bool:
    return any(p.search(text) for p in SPAM_PATTERNS)


def filter_comment_gaps(comments: List[Dict], min_likes: int = COMMENT_MIN_LIKES) -> List[Dict]:
    """Pillar 3 prefilter: drop short/spam comments, keep liked questions."""
    gaps = []
    for c in comments:
        text = c["text"].strip()
        if len(text) < COMMENT_MIN_LENGTH or c["likes"] < min_likes or is_spam(text):
            continue
        lowered = text.lower()
        if not any(kw in lowered for kw in QUESTION_KEYWORDS):
            continue
        gaps.append({
            "text": text,
            "likes": c["likes"],
            "author": c["author"],
            "published_at": c.get("published_at"),
        })
    gaps.sort(key=lambda g: g["likes"], reverse=True)
    return gaps


def age_days(published_at: str) -> Optional[int]:
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return max((datetime.now(timezone.utc) - pub.astimezone(timezone.utc)).days, 1)


def velocity(views: int, published_at: str) -> Optional[float]:
    days = age_days(published_at)
    return None if days is None else views / days


def select_competitors(candidates: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    PHAN IV. Two independent groups:
      Group 1: top-2 all-time by views/day, for structure and pacing.
      Group 2: top-3..5 published 90-365 days ago with >=100 comments, for current taste.
    """
    scored = []
    for c in candidates:
        v = velocity(c.get("views", 0), c.get("published_at", ""))
        if v is None:
            continue
        c = dict(c, avg_views_per_day=round(v), _velocity=v, age_days=age_days(c["published_at"]))
        scored.append(c)

    group1 = sorted(scored, key=lambda c: c["_velocity"], reverse=True)[:GROUP1_ALLTIME_COUNT]
    picked = {c["video_id"] for c in group1}

    recent = [
        c for c in scored
        if c["video_id"] not in picked
        and RECENT_WINDOW_MIN_DAYS <= c["age_days"] <= RECENT_WINDOW_MAX_DAYS
        and c.get("comments", 0) >= RECENT_MIN_COMMENTS
    ]
    group2 = sorted(recent, key=lambda c: c["_velocity"], reverse=True)[:GROUP2_RECENT_COUNT]

    for c in group1:
        c["selection_group"] = "all_time_top_velocity"
    for c in group2:
        c["selection_group"] = "recent_90_365_days"

    logger.info("[b15.p4] selected %d all-time + %d recent from %d scored candidates",
                len(group1), len(group2), len(scored))
    return group1, group2


def fetch_transcript(video_id: str, langs: List[str], head_seconds: int = 180) -> Dict:
    """
    Pillar 2. Returns {"status", "text", "source"}.

    status is one of:
      captions   - pulled from YouTube caption tracks
      whisper    - yt-dlp audio + Faster-Whisper on the first head_seconds
      unavailable- neither path reachable (cloud-IP block, captions off, etc.)
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        snippets = YouTubeTranscriptApi().fetch(video_id, languages=langs).to_raw_data()
        text = " ".join(s["text"] for s in snippets if s.get("start", 0) < head_seconds)
        if text.strip():
            logger.info("[b15.p2] %s: captions, %d chars", video_id, len(text))
            return {"status": "captions", "text": text, "source": "youtube-transcript-api"}
    except Exception as e:
        logger.info("[b15.p2] %s: captions unavailable (%s), trying audio",
                    video_id, type(e).__name__)

    text = _whisper_transcript(video_id, langs[0], head_seconds)
    if text:
        return {"status": "whisper", "text": text, "source": "yt-dlp+faster-whisper"}

    logger.warning("[b15.p2] %s: no transcript from either path", video_id)
    return {"status": "unavailable", "text": None, "source": None}


def _whisper_transcript(video_id: str, lang: str, head_seconds: int) -> Optional[str]:
    """yt-dlp -x 128kbps then Faster-Whisper over the first head_seconds."""
    if not os.path.exists(YTDLP_BIN):
        logger.debug("[b15.p2] yt-dlp not installed at %s", YTDLP_BIN)
        return None
    with tempfile.TemporaryDirectory(prefix="b15_audio_") as tmp:
        out_tmpl = str(Path(tmp) / "a.%(ext)s")
        proc = subprocess.run(
            [YTDLP_BIN, "--no-update", "--no-playlist", "-x",
             "--audio-format", "mp3", "--audio-quality", "128K",
             "--download-sections", f"*0-{head_seconds}",
             "-o", out_tmpl, f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=180,
        )
        audio = next(Path(tmp).glob("a.*"), None)
        if proc.returncode != 0 or audio is None:
            logger.info("[b15.p2] %s: yt-dlp failed rc=%s (%s)",
                        video_id, proc.returncode, (proc.stderr or "").strip()[-160:])
            return None
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(str(audio), language=lang, beam_size=1)
            text = " ".join(s.text.strip() for s in segments if s.start < head_seconds)
        except Exception as e:
            logger.warning("[b15.p2] %s: Faster-Whisper failed: %s", video_id, e)
            return None
    if text.strip():
        logger.info("[b15.p2] %s: whisper, %d chars", video_id, len(text))
        return text
    return None


def download_thumbnail(video_id: str, thumbnails: Dict, dest_dir: Path) -> Optional[str]:
    """
    Pillar 4. Save the largest available thumbnail for the Antigravity vision
    audit at B5. This module does not analyse the image itself.
    """
    for size in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbnails.get(size) or {}).get("url")
        if not url:
            continue
        dest = dest_dir / f"thumb_{video_id}.jpg"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
            if not data:
                continue
            dest.write_bytes(data)
            logger.info("[b15.p4] %s: thumbnail %s -> %s (%d bytes)",
                        video_id, size, dest.name, len(data))
            return str(dest)
        except Exception as e:
            logger.debug("[b15.p4] %s: %s thumbnail failed: %s", video_id, size, e)
    logger.warning("[b15.p4] %s: no thumbnail downloaded", video_id)
    return None



def extract_high_engagement_comments(comments: List[Dict], max_count: int = 15) -> List[Dict]:
    """Extract top comments with highest likes, filtering spam and low-signal text."""
    cleaned = []
    seen = set()
    for c in comments:
        text = c.get("text", "").strip()
        if len(text) < 15 or is_spam(text):
            continue
        # Avoid duplicate comments across videos/channels
        norm = text.lower()[:60]
        if norm in seen:
            continue
        seen.add(norm)
        cleaned.append({
            "text": text,
            "likes": int(c.get("likes", 0)),
            "author": c.get("author", ""),
            "published_at": c.get("published_at"),
            "video_id": c.get("video_id", ""),
        })
    cleaned.sort(key=lambda x: x["likes"], reverse=True)
    return cleaned[:max_count]


def extract_video_chapters(description: str) -> List[str]:
    """Extract timestamped chapters from video description if present."""
    if not description:
        return []
    chapters = []
    for line in description.splitlines():
        line = line.strip()
        if re.search(r'\b(?:\d{1,2}:)?\d{1,2}:\d{2}\b', line):
            chapters.append(line[:100])
    return chapters[:10]


def analyze_competitor_anatomy(task_id: str, target_keyword: str, market: str,
                               selected: List[Dict], top_comments: List[Dict],
                               niche: str = "General") -> Dict:
    """
    Two-Pass Competitor Recon Reasoning via GPT-5.6-Sol.
    Extracts 5 core pillars:
      1. competitor_act_breakdown: Overview of how top viral videos structured their acts/story.
      2. competitor_secret_sauce: Why competitor videos went viral (hook, visuals, tension, pacing).
      3. audience_core_frustrations: Top 3-5 unanswered questions, skepticism, or outrage from top comments.
      4. fatal_explanatory_vacuum: Fatal blindspots and missing institutional/causal mechanisms left unaddressed.
      5. our_10x_pivot_angle: High-impact independent investigative narrative angle for our 15-min documentary.
    """
    try:
        from app.services.hhtech_reasoner import call_gpt56_sol
        
        bench_summary = []
        for c in selected[:5]:
            ch = c.get("channel", "Unknown")
            ti = c.get("title", "")
            vw = c.get("views", 0)
            vpd = c.get("avg_views_per_day", 0)
            desc = c.get("description_head", "")[:250]
            tr = (c.get("transcript", {}).get("text") or "")[:350]
            bench_summary.append(
                f"- Channel: [{ch}] | Title: \"{ti}\" | Views: {vw:,} ({vpd:,}/day)\n"
                f"  Intro/Transcript: {tr}\n"
                f"  Description: {desc}"
            )
            
        comment_summary = []
        for g in top_comments[:15]:
            txt = g.get("text", "").strip().replace("\n", " ")[:200]
            lks = g.get("likes", 0)
            comment_summary.append(f"- [{lks} likes]: \"{txt}\"")
            
        bench_text = "\n".join(bench_summary) if bench_summary else "No competitor benchmarks available."
        comm_text = "\n".join(comment_summary) if comment_summary else "No comments available."
        
        sys_prompt = (
            "You are the Lead Forensic Story Analyst for Video Factory (Pipeline v3).\n"
            "Your mission is to perform deep competitor anatomy on top-performing YouTube videos and high-engagement audience comments, "
            "identifying what made them viral, where their explanations failed, and how our independent investigative documentary can completely outperform them.\n"
            "Return ONLY a valid JSON object with the exact keys described."
        )
        
        user_prompt = (
            f"Topic / Subject: {target_keyword} (Market: {market.upper()}, Niche: {niche})\n\n"
            f"=== TOP VIRAL COMPETITOR BENCHMARKS ===\n{bench_text}\n\n"
            f"=== TOP HIGH-ENGAGEMENT AUDIENCE COMMENTS (Highest Likes) ===\n{comm_text}\n\n"
            "Perform deep structural and audience sentiment analysis. Provide a JSON response with:\n"
            "{\n"
            '  "competitor_act_breakdown": "Summary of narrative arcs and storyline beats used by competitors (e.g. Act 1 Hook, Act 2 Conflict, Act 3 Climax)",\n'
            '  "competitor_secret_sauce": "What made these videos gain high velocity and views (hook style, pacing, emotional trigger)",\n'
            '  "audience_core_frustrations": [\n'
            '    "Frustration / Unanswered question 1 with context from top comments",\n'
            '    "Frustration / Unanswered question 2",\n'
            '    "Frustration / Unanswered question 3"\n'
            '  ],\n'
            '  "fatal_explanatory_vacuum": "The critical systemic, institutional, financial, or forensic blindspot that competitors completely ignored or glossed over",\n'
            '  "our_10x_pivot_angle": "Our master investigative angle for a 12-15 minute deep-dive that answers audience frustrations and exposes the root causes without mentioning competitor channels"\n'
            "}\n"
            "Output ONLY valid JSON:"
        )
        
        logger.info("[b15.reasoning] Calling GPT-5.6-Sol for Two-Pass Competitor Anatomy...")
        raw_resp = call_gpt56_sol(user_prompt, system_prompt=sys_prompt, max_tokens=1500, timeout=120.0)
        
        m = re.search(r'\{.*\}', raw_resp, re.DOTALL)
        if m:
            anatomy = json.loads(m.group(0))
            logger.info("[b15.reasoning] Successfully extracted competitor narrative anatomy!")
            return anatomy
        else:
            logger.warning("[b15.reasoning] Could not parse JSON from GPT-5.6-Sol response: %s", raw_resp[:200])
    except Exception as e:
        logger.error("[b15.reasoning] Two-Pass competitor reasoning failed: %s", e)
        
    return {
        "competitor_act_breakdown": "Competitors focused on sensational surface events without institutional depth.",
        "competitor_secret_sauce": "Fast-paced hooks and high sensationalism.",
        "audience_core_frustrations": [
            "Why did regulatory oversight fail to detect this early?",
            "Who were the actual beneficiaries behind the scenes?",
            "What systemic changes were made after the scandal?"
        ],
        "fatal_explanatory_vacuum": "Lack of forensic paper trail and regulatory failure mechanisms.",
        "our_10x_pivot_angle": f"Independent investigative documentary uncovering the hidden systemic mechanisms behind {target_keyword}."
    }


def build_intel_card(task_id: str, target_keyword: str, niche: str, market: str,
                     selected: List[Dict], gaps: List[Dict], quota: QuotaTracker,
                     competitor_narrative_anatomy: Optional[Dict] = None) -> Dict:
    """Assemble the card. Collected evidence only; no interpretation."""
    benchmarks = [{
        "video_id": c["video_id"],
        "channel": c["channel"],
        "title": c["title"],
        "published_at": c["published_at"],
        "age_days": c["age_days"],
        "views": c.get("views", 0),
        "likes": c.get("likes", 0),
        "comments": c.get("comments", 0),
        "duration": c.get("duration"),
        "avg_views_per_day": c["avg_views_per_day"],
        "selection_group": c["selection_group"],
        "tags": c.get("tags", []),
        "description_head": c.get("description_head", ""),
        "transcript_status": c["transcript"]["status"],
        "transcript_source": c["transcript"]["source"],
        "transcript_head": c["transcript"]["text"],
        "thumbnail_path": c.get("thumbnail_path"),
    } for c in selected]

    card = {
        "task_id": task_id,
        "target_keyword": target_keyword,
        "niche": niche,
        "market": market,
        "competitor_benchmarks": benchmarks,
        "audience_comment_gaps": [{
            "video_id": g["video_id"],
            "comment_verbatim": g["text"],
            "likes_count": g["likes"],
            "author": g["author"],
            "published_at": g.get("published_at"),
        } for g in gaps],
        "_b2_to_synthesize": [
            "golden_facts_to_keep",
            "competitor_benchmarks[].critical_flaw",
            "competitor_benchmarks[].hook_strategy",
            "audience_comment_gaps[].viewer_frustration",
            "recommended_10x_angle",
        ],
        "collection_meta": {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "quota_units_spent_today": quota.spent,
            "quota_ratio": round(quota.ratio, 4),
            "quota_fallback_active": quota.should_fallback(),
            "transcripts_captured": sum(
                1 for b in benchmarks if b["transcript_status"] != "unavailable"),
            "thumbnails_captured": sum(1 for b in benchmarks if b["thumbnail_path"]),
        },
    }
    if competitor_narrative_anatomy:
        card["competitor_narrative_anatomy"] = competitor_narrative_anatomy
    return card


def sync_card_to_notion(task_id: str, card: dict) -> bool:
    """Sync competitor recon intel summary to Notion DBs (Trend Brain & Story Library)."""
    try:
        import scripts.ag_notion_bridge as bridge
        benchmarks = card.get("competitor_benchmarks", [])
        gaps = card.get("audience_comment_gaps", [])
        anatomy = card.get("competitor_narrative_anatomy") or {}
        
        lines = []
        if anatomy.get("our_10x_pivot_angle"):
            lines.append(f"🎯 10X PIVOT ANGLE:\n{anatomy['our_10x_pivot_angle']}\n")
        if anatomy.get("fatal_explanatory_vacuum"):
            lines.append(f"⚠️ COMPETITOR BLINDSPOT:\n{anatomy['fatal_explanatory_vacuum']}\n")
            
        lines.append(f"Top Competitors ({len(benchmarks)}):")
        for b in benchmarks[:5]:
            ch = b.get("channel", "Unknown")
            ti = b.get("title", "")[:50]
            vw = b.get("views", 0)
            vpd = b.get("avg_views_per_day", 0)
            lines.append(f"• [{ch}] {ti} | {vw:,} views ({vpd:,}/d)")
            
        if anatomy.get("audience_core_frustrations"):
            lines.append(f"\nAudience Core Frustrations:")
            for f_item in anatomy["audience_core_frustrations"][:4]:
                lines.append(f'• {f_item}')
        elif gaps:
            lines.append(f"\nAudience Gaps ({len(gaps)}):")
            for g in gaps[:3]:
                txt = g.get("comment_verbatim", "").strip().replace("\n", " ")[:90]
                lk = g.get("likes_count", 0)
                lines.append(f'• "{txt}" (👍 {lk})')
                
        summary_text = "\n".join(lines)[:1990]
        
        # 1. Update Notion Trend Brain DB
        trend_db_id = "4c101989-2400-8334-8016-01d4f463b09f"
        pages = bridge.query_db(trend_db_id, filter_obj={
            "property": "Task ID",
            "rich_text": {"equals": task_id}
        })
        if pages and pages.get("results"):
            page_id = pages["results"][0]["id"]
            bridge.update_page_properties(page_id, {
                "Competitor Benchmarks": {
                    "rich_text": [{"type": "text", "text": {"content": summary_text}}]
                }
            })
            logger.info("[b15] Synced Competitor Benchmarks to Trend Brain page %s", page_id)
            
        # 2. Update Story Library DB if row exists
        story_db_id = "b0301989-2400-836b-bdb5-8131fea17736"
        s_pages = bridge.query_db(story_db_id, filter_obj={
            "property": "Task ID",
            "rich_text": {"equals": task_id}
        })
        if s_pages and s_pages.get("results"):
            s_page_id = s_pages["results"][0]["id"]
            bridge.update_page_properties(s_page_id, {
                "Competitor Benchmarks": {
                    "rich_text": [{"type": "text", "text": {"content": summary_text}}]
                }
            })
            logger.info("[b15] Synced Competitor Benchmarks to Story Library page %s", s_page_id)
            
            if anatomy:
                try:
                    existing_blocks = bridge.get_blocks(s_page_id)
                    has_callout = False
                    if isinstance(existing_blocks, dict):
                        for blk in existing_blocks.get("results", []):
                            if blk.get("type") == "callout":
                                has_callout = True
                                break
                    if not has_callout:
                        callout_body = (
                            f"🎯 PHÂN TÍCH ĐỐI THỦ & ĐÒN BẨY ĐỘT PHÁ 10X (B1.5 RECON)\n"
                            f"• Đòn bẩy 10x: {anatomy.get('our_10x_pivot_angle', 'N/A')}\n"
                            f"• Điểm mù đối thủ: {anatomy.get('fatal_explanatory_vacuum', 'N/A')}\n"
                            f"• Cốt truyện đối thủ: {anatomy.get('competitor_act_breakdown', 'N/A')}"
                        )[:1950]
                        c_block = [{
                            "object": "block",
                            "type": "callout",
                            "callout": {
                                "rich_text": [{"type": "text", "text": {"content": callout_body}}],
                                "icon": {"type": "emoji", "emoji": "🎯"}
                            }
                        }]
                        bridge.append_children_blocks(s_page_id, c_block)
                        logger.info("[b15] Appended Competitor Callout Block to Story Library page %s", s_page_id)
                except Exception as c_err:
                    logger.debug("[b15] Callout block append error (non-fatal): %s", c_err)
            
        return True
    except Exception as e:
        logger.warning("[b15] Failed to sync competitor intel to Notion: %s", e)
        return False


def run_b15(task_id: str, target_keyword: str, niche: str = "General",
            use_cache: bool = True) -> Optional[Dict]:
    """Orchestrate the four pillars for one task id."""
    load_env()
    market = market_of(task_id)
    logger.info("[b15] task=%s keyword=%r market=%s", task_id, target_keyword, market)

    cache_path = CACHE_DIR / f"{task_id}.json"
    if use_cache and cache_path.exists():
        logger.info("[b15] reusing cached search for %s (1 search.list per task id)", task_id)
        candidates = json.loads(cache_path.read_text())["candidates"]
        quota = QuotaTracker()
    else:
        api_key = get_api_key()
        if not api_key:
            return None
        quota = QuotaTracker()
        if quota.should_fallback():
            logger.warning("[b15] quota at %.0f%% of daily cap - search may fail",
                           quota.ratio * 100)
        candidates = youtube_search(api_key, target_keyword, market, quota)
        if not candidates:
            logger.error("[b15] no candidates for %r", target_keyword)
            return None
        details = youtube_video_details(api_key, [c["video_id"] for c in candidates], quota)
        for c in candidates:
            c.update(details.get(c["video_id"], {}))
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "target_keyword": target_keyword,
                "candidates": candidates,
            }, ensure_ascii=False))
        except OSError as e:
            logger.debug("[b15] cache write failed: %s", e)

    group1, group2 = select_competitors(candidates)
    selected = group1 + group2
    if not selected:
        logger.error("[b15] selection formula matched nothing")
        return None

    api_key = get_api_key() or ""
    asset_dir = EPISODE_DIR / task_id / "competitor_assets"
    langs = MARKET_LOCALE[market]["transcript_langs"]

    all_gaps: List[Dict] = []
    all_raw_comments: List[Dict] = []
    for c in selected:
        c["transcript"] = fetch_transcript(c["video_id"], langs)
        c["thumbnail_path"] = download_thumbnail(c["video_id"], c.get("thumbnails", {}), asset_dir)
        raw_cmts = youtube_comments(api_key, c["video_id"], quota)
        for rc in raw_cmts:
            all_raw_comments.append(dict(rc, video_id=c["video_id"]))
        for g in filter_comment_gaps(raw_cmts):
            all_gaps.append(dict(g, video_id=c["video_id"]))

    all_gaps.sort(key=lambda g: g["likes"], reverse=True)
    top_comments = extract_high_engagement_comments(all_raw_comments, max_count=15)
    
    # Two-Pass Reasoning: Analyze competitor narrative structure and audience sentiment via GPT-5.6-Sol
    anatomy = analyze_competitor_anatomy(task_id, target_keyword, market, selected, top_comments, niche)
    
    card = build_intel_card(task_id, target_keyword, niche, market, selected, all_gaps[:12], quota,
                            competitor_narrative_anatomy=anatomy)

    # Persist competitor_intel_card.json to BOTH episode folders so B2 can load it
    for target_dir in [EPISODE_DIR / task_id, Path("/root/video_factory/episodes") / task_id]:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            out_p = target_dir / "competitor_intel_card.json"
            out_p.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("[b15] Intel card saved to %s", out_p)
        except Exception as e:
            logger.warning("[b15] Failed to save intel card to %s: %s", target_dir, e)

    # Sync to Notion SoT (Trend Brain + Story Library)
    try:
        sync_card_to_notion(task_id, card)
    except Exception as e:
        logger.warning("[b15] sync_card_to_notion failed: %s", e)

    meta = card["collection_meta"]
    logger.info("[b15] card ready: %d competitors, %d gaps, %d transcripts, %d thumbnails, quota %d units",
                len(card["competitor_benchmarks"]), len(card["audience_comment_gaps"]),
                meta["transcripts_captured"], meta["thumbnails_captured"], meta["quota_units_spent_today"])
    return card


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: competitor_recon_b15.py <task_id> <target_keyword> [niche]")
        print("Example: competitor_recon_b15.py en-enron-collapse-ep006 'Enron Scandal Explained' 'Corporate Crime'")
        sys.exit(1)

    task_id, target_keyword = sys.argv[1], sys.argv[2]
    niche = sys.argv[3] if len(sys.argv) > 3 else "General"

    card = run_b15(task_id, target_keyword, niche)
    if not card:
        logger.error("[b15] recon failed for %s", task_id)
        sys.exit(1)

    out_dir = EPISODE_DIR / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "competitor_intel_card.json"
    out_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Intel card saved to {out_path}")
    print(json.dumps(card["collection_meta"], indent=2))


if __name__ == "__main__":
    main()
