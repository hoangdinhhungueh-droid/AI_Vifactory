"""
B1.5: Two-Pass Competitor Recon & Deep Forensic Reasoning Engine.

Architecture & Operational Standard (Rule 118: Zero-Mock Data & Rule 123: Real Data):
  - Pass 1: Empirical Evidence Harvesting (YouTube Data API search/videos/comments,
            transcript extraction via captions/Faster-Whisper, thumbnail staging).
  - Pass 2: Forensic Narrative Anatomy via GPT-6-Astra (Lead Forensic Story Analyst).
            Synthesizes 5 strategic pillars:
              1. competitor_act_breakdown: Narrative arcs & story pacing used by rivals.
              2. competitor_secret_sauce: Underlying velocity triggers (hook, pacing, emotion).
              3. audience_core_frustrations: Unanswered questions & outrage from top comments.
              4. fatal_explanatory_vacuum: Critical systemic & institutional blindspots.
              5. our_10x_pivot_angle: Independent 15-min investigative docudrama angle for B2.
  - Pass 3: Contract Assembly, Dual Persistence & Notion SoT Synchronization
            (Persists competitor_intel_card.json for B2 and syncs callouts to Notion DBs).
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

# ==============================================================================
# SECTION 0: CONFIGURATION, QUOTA MANAGEMENT & LOCALE MAPPING
# ==============================================================================

SECRETS_ENV = "/root/secrets/.env"
CACHE_DIR = Path("/var/vf/b15_cache")
EPISODE_DIR = Path("/var/vf/episodes")
YTDLP_BIN = "/root/video_factory/venv/bin/yt-dlp"

# YouTube Data API v3 daily quota and per-call unit costs
QUOTA_DAILY_UNITS = 10_000
QUOTA_COST = {"search": 100, "videos": 1, "commentThreads": 1, "channels": 1}
QUOTA_FALLBACK_RATIO = 0.80

# Two-group competitor selection parameters (TubeRadar Outlier & Narrative Architecture)
RECENT_WINDOW_MIN_DAYS = 90
RECENT_WINDOW_MAX_DAYS = 365
RECENT_MIN_COMMENTS = 100
GROUP1_ALLTIME_COUNT = 2
GROUP2_RECENT_COUNT = 5

# TubeRadar 48H Outlier & Small-Channel Constants
OUTLIER_VS_RATIO_MIN = 3.0
SMALL_CHANNEL_SUB_CEILING = 50_000
GROUP1_OUTLIER_COUNT = 3
GROUP2_ALLTIME_BENCHMARK_COUNT = 2

# Token Overflow & Budget Protection Caps
MAX_PROMPT_CHARS = 10_000  # ~2,500 input tokens ceiling
MAX_TRANSCRIPT_CHARS_PER_VIDEO = 1_200  # Focus on first 180s hook/conflict
MAX_COMMENT_CHARS = 180
MAX_COMMENTS_IN_PROMPT = 15

# Audience comment mining filter standards
COMMENT_MIN_LENGTH = 30
COMMENT_MIN_LIKES = 3
QUESTION_KEYWORDS = (
    "why", "how", "missed", "didn't explain", "didnt explain", "did not explain",
    "confused", "confusing", "unclear", "what about", "never explained",
    "still don't understand", "makes no sense", "tại sao", "chưa giải thích",
    "vô lý", "thế còn", "tiền đi đâu", "lừa đảo", "sao lại", "không hiểu",
    "なぜ", "どうして", "説明がない", "矛盾", "왜", "어떻게", "설명안함",
)
PRAISE_KEYWORDS = (
    "best video", "masterpiece", "eye opening", "eye-opening", "amazing analysis",
    "great explanation", "underrated", "deserves more views", "chất lượng",
    "quá hay", "quá cuốn", "đỉnh cao", "xuất sắc", "cảm ơn tác giả",
    "最高", "わかりやすい", "神動画", "최고", "소름", "명작",
)
CRITIQUE_KEYWORDS = (
    "wrong", "inaccurate", "biased", "propaganda", "fake", "clickbait",
    "lazy", "missed the point", "misleading", "sai rồi", "bịa đặt",
    "chém gió", "hời hợt", "thiếu sót", "sai lệch", "dắt mũi",
    "間違い", "嘘", "偏向", "틀림", "선동", "왜곡",
)
SPAM_PATTERNS = (
    re.compile(r"https?://", re.I),
    re.compile(r"\bwww\.", re.I),
    re.compile(r"\b(subscribe to|check out my|follow me|promo\s?code)\b", re.I),
    re.compile(r"[\U0001F300-\U0001FAFF]{4,}"),
)

# Market prefix -> YouTube locale hints & transcript fallback languages
MARKET_LOCALE = {
    "en": {"relevanceLanguage": "en", "regionCode": "US", "transcript_langs": ["en"]},
    "jp": {"relevanceLanguage": "ja", "regionCode": "JP", "transcript_langs": ["ja", "en"]},
    "kr": {"relevanceLanguage": "ko", "regionCode": "KR", "transcript_langs": ["ko", "en"]},
}

# Strategic comment mining patterns (Thanh Hai YouTube AI 2026 Playbook)
SLOP_PATTERNS = (
    re.compile(r"\b(ai slop|chatgpt script|bot script|sounds like ai|ai generated|lazy writing|generic voiceover|ai hallucination|cliche|fake story)\b", re.I),
    re.compile(r"\b(aiスクリプト|aiっぽい|機械音声|薄っぺらい)\b", re.I),
    re.compile(r"\b(ai 대본|기계음|챗gpt|양산형)\b", re.I),
)

WISHLIST_PATTERNS = (
    re.compile(r"\b(please (?:make|do|cover)|next (?:video|topic) (?:should be|on)|can you (?:make|do|cover)|waiting for|wish you (?:would|could) (?:cover|make)|make one about|would love to see)\b", re.I),
    re.compile(r"\b(次(は|の動画は|のテーマは)|取り上げてほしい|解説してほしい|作ってほしい)\b", re.I),
    re.compile(r"\b(다음(은| 영상은)|다뤄주세요|만들어주세요|해줬으면 좋겠어요)\b", re.I),
)


def load_env() -> None:
    """Populate os.environ from /root/secrets/.env."""
    if not os.path.exists(SECRETS_ENV):
        return
    with open(SECRETS_ENV) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def market_of(task_id: str) -> str:
    """Extract market prefix (en/jp/kr) from task ID, defaulting to 'en'."""
    t = task_id.strip()
    if "_" in t:
        p = t.split("_", 1)[0].lower()
        if p in MARKET_LOCALE:
            return p
    if "-" in t:
        p = t.split("-", 1)[0].lower()
        if p in MARKET_LOCALE:
            return p
    return "en"


def get_api_key() -> Optional[str]:
    """Retrieve YouTube Data API Key from environment."""
    key = os.environ.get("YT_UPLOAD_API_KEY")
    if not key:
        logger.warning("[b15] YT_UPLOAD_API_KEY not set in %s", SECRETS_ENV)
    return key


class QuotaTracker:
    """Tracks daily YouTube Data API units spent and prevents quota exhaustion."""

    def __init__(self, state_path: Path = CACHE_DIR / "quota.json"):
        self.state_path = state_path
        self.date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.spent = 0
        self.exhausted = False
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.state_path.read_text())
            if data.get("date") == self.date:
                self.spent = int(data.get("spent", 0))
                self.exhausted = bool(data.get("exhausted", False))
        except (OSError, ValueError, TypeError):
            pass

    def mark_exhausted(self) -> None:
        self.exhausted = True
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"date": self.date, "spent": self.spent, "exhausted": True}))
            logger.warning("[b15] YouTube Data API daily quota marked EXHAUSTED for date %s", self.date)
        except OSError as e:
            logger.debug("[b15] could not persist quota state: %s", e)

    def charge(self, endpoint: str) -> None:
        self.spent += QUOTA_COST.get(endpoint, 1)
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({"date": self.date, "spent": self.spent, "exhausted": self.exhausted}))
        except OSError as e:
            logger.debug("[b15] could not persist quota state: %s", e)

    @property
    def ratio(self) -> float:
        return self.spent / QUOTA_DAILY_UNITS

    def should_fallback(self) -> bool:
        return self.exhausted or (self.ratio >= QUOTA_FALLBACK_RATIO)


def _api_get(endpoint: str, params: Dict, quota: QuotaTracker) -> Optional[Dict]:
    """Execute authenticated YouTube Data API GET request."""
    if quota.should_fallback():
        logger.debug("[b15] Quota should_fallback active (exhausted=%s, ratio=%.2f). Skipping %s", quota.exhausted, quota.ratio, endpoint)
        return None
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
        if "429" in str(e) or "quotaExceeded" in detail or "RESOURCE_EXHAUSTED" in detail:
            quota.mark_exhausted()
        return None


def parse_relative_time_to_dt(rel_str: str) -> Optional[datetime]:
    """Parse relative time strings like '8 hours ago', '2 days ago', '1 week ago' into UTC datetime."""
    if not rel_str or not isinstance(rel_str, str):
        return None
    s = rel_str.strip().lower()
    now = datetime.now(timezone.utc)
    if "yesterday" in s:
        return now - timedelta(days=1)
    m = re.search(r'(\d+)\s*(second|sec|minute|min|hour|hr|day|week|wk|month|mo|year|yr)', s)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2)
    if unit.startswith("sec"):
        return now - timedelta(seconds=val)
    elif unit.startswith("min"):
        return now - timedelta(minutes=val)
    elif unit.startswith("hour") or unit.startswith("hr"):
        return now - timedelta(hours=val)
    elif unit.startswith("day"):
        return now - timedelta(days=val)
    elif unit.startswith("week") or unit.startswith("wk"):
        return now - timedelta(days=val * 7)
    elif unit.startswith("month") or unit.startswith("mo"):
        return now - timedelta(days=val * 30)
    elif unit.startswith("year") or unit.startswith("yr"):
        return now - timedelta(days=val * 365)
    return None


def scrape_youtube_search_zero_quota(query: str, market: str = "en", max_results: int = 15) -> List[Dict]:
    """Zero-quota public YouTube search harvester using ytInitialData.
    Provides complete resilience against YouTube Data API 429 quota exhaustion (Rule 118 & 123).
    """
    if not query or not str(query).strip():
        return []

    locale = MARKET_LOCALE.get(market.lower(), MARKET_LOCALE.get("en", {}))
    hl = locale.get("relevanceLanguage", "en")
    gl = locale.get("regionCode", "US")

    clean_query = str(query).strip()
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(clean_query)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": f"{hl}-{gl},{hl};q=0.9,en;q=0.8"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        m = re.search(r'var ytInitialData\s*=\s*({.*?});</script>', html)
        if not m:
            m = re.search(r'window\["ytInitialData"\]\s*=\s*({.*?});</script>', html)
        if not m:
            return []

        data = json.loads(m.group(1))
        videos = []
        contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
        for c in contents:
            item_section = c.get("itemSectionRenderer", {}).get("contents", [])
            for item in item_section:
                vr = item.get("videoRenderer")
                if vr:
                    vid = vr.get("videoId")
                    title_runs = vr.get("title", {}).get("runs", [])
                    title = "".join(r.get("text", "") for r in title_runs)
                    view_text = vr.get("viewCountText", {}).get("simpleText", "") or vr.get("shortViewCountText", {}).get("simpleText", "")
                    channel = "".join(r.get("text", "") for r in vr.get("ownerText", {}).get("runs", []))
                    pub_text = vr.get("publishedTimeText", {}).get("simpleText", "")

                    views_int = 0
                    nums = re.findall(r'[\d,\.]+', view_text)
                    if nums:
                        clean_num = nums[0].replace(",", "").replace(".", "")
                        if clean_num.isdigit():
                            views_int = int(clean_num)
                            if "k" in view_text.lower():
                                views_int *= 1000
                            elif "m" in view_text.lower():
                                views_int *= 1000000

                    dt_pub = parse_relative_time_to_dt(pub_text)
                    iso_pub = dt_pub.isoformat() if dt_pub else (pub_text or "")

                    if vid and title:
                        videos.append({
                            "video_id": vid,
                            "channel": channel,
                            "channel_id": "",
                            "title": title,
                            "published_at": iso_pub,
                            "published_at_relative": pub_text,
                            "views": views_int,
                            "thumbnails": vr.get("thumbnail", {}),
                            "url": f"https://www.youtube.com/watch?v={vid}"
                        })
                        if len(videos) >= max_results:
                            break
            if len(videos) >= max_results:
                break

        if videos:
            logger.info("[b15.zero_quota] Scraped %d videos for query %r (market=%s)", len(videos), clean_query, market)
        return videos
    except Exception as e:
        logger.warning("[b15.zero_quota] Scraper failed for %r: %s", clean_query, e)
        return []


# ==============================================================================
# SECTION 1: PASS 1 — EMPIRICAL EVIDENCE HARVESTING (DATA MINING)
# ==============================================================================

def youtube_search(api_key: str, query: str, market: str, quota: QuotaTracker,
                   max_results: int = 25) -> List[Dict]:
    """Harvest candidate videos sorted by viewCount with automatic query relaxation and zero-quota scraper fallback."""
    locale = MARKET_LOCALE.get(market.lower(), MARKET_LOCALE.get("en", {}))
    queries_to_try = [query]
    words = query.strip().split()
    if len(words) > 3:
        queries_to_try.append(" ".join(words[:3]))
    if len(words) > 2:
        queries_to_try.append(" ".join(words[:2]))
    if len(words) > 1:
        queries_to_try.append(words[0])

    if not quota.should_fallback() and api_key:
        for q_attempt in queries_to_try:
            body = _api_get("search", {
                "part": "snippet",
                "q": q_attempt,
                "type": "video",
                "maxResults": max_results,
                "order": "viewCount",
                "relevanceLanguage": locale.get("relevanceLanguage", "en"),
                "regionCode": locale.get("regionCode", "US"),
                "key": api_key,
            }, quota)
            items = body.get("items", []) if body else []
            if items:
                logger.info("[b15.pass1] search returned %d candidates for query %r (market=%s)", len(items), q_attempt, market)
                return [{
                    "video_id": it["id"]["videoId"],
                    "channel": it["snippet"]["channelTitle"],
                    "channel_id": it["snippet"].get("channelId", ""),
                    "title": it["snippet"]["title"],
                    "published_at": it["snippet"]["publishedAt"],
                    "thumbnails": it["snippet"].get("thumbnails", {}),
                } for it in items if "videoId" in it.get("id", {})]

    # Resilient zero-quota fallback when API quota is exhausted, missing, or returns 0
    scraped = scrape_youtube_search_zero_quota(query, market, max_results=max_results)
    if scraped:
        logger.info("[b15.pass1] Resilient zero-quota scraper recovered %d candidates for %r", len(scraped), query)
        return scraped
    if len(queries_to_try) > 1:
        scraped_relaxed = scrape_youtube_search_zero_quota(queries_to_try[1], market, max_results=max_results)
        if scraped_relaxed:
            logger.info("[b15.pass1] Resilient zero-quota scraper recovered %d candidates for relaxed query %r", len(scraped_relaxed), queries_to_try[1])
            return scraped_relaxed

    logger.info("[b15.pass1] search returned 0 candidates for all query variants of %r (market=%s)", query, market)
    return []


def youtube_video_details(api_key: str, video_ids: List[str], quota: QuotaTracker) -> Dict[str, Dict]:
    """Enrich video statistics (views, comments, likes, channel_id, tags, description) in chunks of 50."""
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
                "channel_id": it["snippet"].get("channelId", ""),
                "published_at": it["snippet"]["publishedAt"],
                "duration": it["contentDetails"]["duration"],
                "tags": it["snippet"].get("tags", [])[:20],
                "description_head": (it["snippet"].get("description") or "")[:400],
                "thumbnails": it["snippet"].get("thumbnails", {}),
            }
    logger.info("[b15.pass1] details resolved for %d/%d videos", len(out), len(video_ids))
    return out


def youtube_channel_subscribers(api_key: str, channel_ids: List[str], quota: QuotaTracker) -> Dict[str, int]:
    """
    Query YouTube Data API channels endpoint in chunks of 50 to extract subscriber counts.
    Cost: 1 quota unit per 50 channels (Data-Layer Only Protocol - zero bot risk).
    """
    out: Dict[str, int] = {}
    clean_ids = [cid for cid in channel_ids if cid]
    for chunk_start in range(0, len(clean_ids), 50):
        chunk = clean_ids[chunk_start:chunk_start + 50]
        body = _api_get("channels", {
            "part": "statistics",
            "id": ",".join(chunk),
            "key": api_key,
        }, quota)
        if not body:
            continue
        for it in body.get("items", []):
            stats = it.get("statistics", {})
            hidden = stats.get("hiddenSubscriberCount", False)
            subs = int(stats.get("subscriberCount", 0)) if not hidden else 0
            out[it["id"]] = subs
    logger.info("[b15.pass1] subscriber counts resolved for %d/%d channels", len(out), len(clean_ids))
    return out


def youtube_comments(api_key: str, video_id: str, quota: QuotaTracker,
                     max_results: int = 20) -> List[Dict]:
    """Fetch top audience comments sorted by relevance."""
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
    logger.info("[b15.pass1] fetched %d comments for %s", len(comments), video_id)
    return comments


def is_spam(text: str) -> bool:
    """Filter promo links, URLs, and excessive emoji sequences."""
    return any(p.search(text) for p in SPAM_PATTERNS)


def filter_comment_tri_buckets(comments: List[Dict], min_likes: int = COMMENT_MIN_LIKES) -> Dict[str, List[Dict]]:
    """
    Categorize audience comments into 3 strategic intelligence buckets (TubeRadar Model):
      1. unanswered_questions: High-curiosity gap questions missed or unanswered by competitor.
      2. skepticism_critique: Viewer doubts, counterarguments, and factual/editorial critiques.
      3. praise_resonance: High-resonance emotional triggers and aspects viewers praised.
    """
    buckets: Dict[str, List[Dict]] = {
        "unanswered_questions": [],
        "skepticism_critique": [],
        "praise_resonance": []
    }
    for c in comments:
        text = c["text"].strip() if isinstance(c, dict) else str(c).strip()
        likes = c.get("likes", 0) if isinstance(c, dict) else 0
        if len(text) < COMMENT_MIN_LENGTH or likes < min_likes or is_spam(text):
            continue
        lowered = text.lower()
        item = {
            "text": text,
            "likes": likes,
            "author": c.get("author", "") if isinstance(c, dict) else "",
            "published_at": c.get("published_at") if isinstance(c, dict) else None,
            "video_id": c.get("video_id", "") if isinstance(c, dict) else "",
        }

        # Check Unanswered Question / Gap first
        if any(kw in lowered for kw in QUESTION_KEYWORDS):
            buckets["unanswered_questions"].append(item)
        elif any(kw in lowered for kw in CRITIQUE_KEYWORDS):
            buckets["skepticism_critique"].append(item)
        elif any(kw in lowered for kw in PRAISE_KEYWORDS):
            buckets["praise_resonance"].append(item)

    for k in buckets:
        buckets[k].sort(key=lambda x: x["likes"], reverse=True)
    return buckets


def filter_comment_gaps(comments: List[Dict], min_likes: int = COMMENT_MIN_LIKES) -> List[Dict]:
    """Filter audience comments down to highly-liked, substantive curiosity/doubt questions."""
    tri = filter_comment_tri_buckets(comments, min_likes)
    gaps = tri["unanswered_questions"]
    if not gaps:
        # Fallback: check any comments with question keywords
        for c in comments:
            text = c["text"].strip() if isinstance(c, dict) else str(c).strip()
            likes = c.get("likes", 0) if isinstance(c, dict) else 0
            if len(text) < COMMENT_MIN_LENGTH or likes < min_likes or is_spam(text):
                continue
            lowered = text.lower()
            if any(kw in lowered for kw in QUESTION_KEYWORDS):
                gaps.append({
                    "text": text,
                    "likes": likes,
                    "author": c.get("author", "") if isinstance(c, dict) else "",
                    "published_at": c.get("published_at") if isinstance(c, dict) else None,
                    "video_id": c.get("video_id", "") if isinstance(c, dict) else "",
                })
        gaps.sort(key=lambda g: g["likes"], reverse=True)
    return gaps


def age_days(published_at: str) -> Optional[int]:
    """Calculate age in days since upload."""
    if not published_at or not isinstance(published_at, str):
        return None
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pub = parse_relative_time_to_dt(published_at)
        if pub is None:
            return None
    return max((datetime.now(timezone.utc) - pub.astimezone(timezone.utc)).days, 1)


def velocity(views: int, published_at: str) -> Optional[float]:
    """Calculate daily view velocity (views / days since publish)."""
    days = age_days(published_at)
    return None if days is None else views / days


def calculate_vph(views: int, published_at: str) -> Optional[float]:
    """Calculate Views Per Hour (VPH) since publish for 48H surge detection."""
    if not published_at or not isinstance(published_at, str):
        return None
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        pub = parse_relative_time_to_dt(published_at)
        if pub is None:
            return None
    hours = max((datetime.now(timezone.utc) - pub.astimezone(timezone.utc)).total_seconds() / 3600.0, 1.0)
    return round(views / hours, 2)


def calculate_vs_ratio(views: int, subscribers: int) -> float:
    """Calculate View-to-Subscriber Ratio (R_vs) with floor to avoid division by zero."""
    eff_subs = max(int(subscribers or 0), 100)
    return round(float(views) / float(eff_subs), 2)


def calculate_outlier_score(views: int, subscribers: int, published_at: str) -> float:
    """
    Calculate TubeRadar Outlier Surge Score:
      S_outlier = R_vs * W_tier * log10(VPH + 1.0)
    Gives highest priority to small channels (<50k subs) with extreme View/Sub ratio.
    """
    import math
    subs = int(subscribers or 0)
    if subs <= 10_000:
        w_tier = 2.5
    elif subs <= 50_000:
        w_tier = 1.8
    elif subs <= 200_000:
        w_tier = 1.0
    else:
        w_tier = 0.2

    vs = calculate_vs_ratio(views, subs)
    vph = calculate_vph(views, published_at) or 1.0
    score = vs * w_tier * math.log10(vph + 1.0)
    return round(score, 2)


def select_competitors(candidates: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Select two independent competitor groups (TubeRadar Outlier + Master Narrative Architecture):
      - Group 1 (Outlier Surge): Top 3 videos from small channels (<=50k subs) with R_vs >= 3.0
                                 published within 48h to 180 days (or highest outlier score).
                                 Gracefully falls back to top velocity all-time if no small outliers exist.
      - Group 2 (Macro Benchmark): Top 2 all-time videos with highest velocity / views across any channel size,
                                   or recent window (90-365 days) with >=100 comments.
    """
    scored = []
    for c in candidates:
        v = velocity(c.get("views", 0), c.get("published_at", ""))
        if v is None:
            continue
        vph = calculate_vph(c.get("views", 0), c.get("published_at", "")) or 0.0
        subs = int(c.get("channel_subscribers", 0) or 0)
        vs = calculate_vs_ratio(c.get("views", 0), subs)
        outlier_s = calculate_outlier_score(c.get("views", 0), subs, c.get("published_at", ""))
        c = dict(
            c,
            avg_views_per_day=round(v),
            _velocity=v,
            age_days=age_days(c["published_at"]),
            vph=vph,
            channel_subscribers=subs,
            v_s_ratio=vs,
            outlier_score=outlier_s
        )
        scored.append(c)

    # 1. Check for True Small Channel Outliers (0 < subs <= 50k subs, R_vs >= 3.0, age <= 180 days)
    small_outliers = [
        c for c in scored
        if 0 < c.get("channel_subscribers", 0) <= SMALL_CHANNEL_SUB_CEILING
        and c["v_s_ratio"] >= OUTLIER_VS_RATIO_MIN
        and (c["age_days"] is None or c["age_days"] <= 180)
    ]

    if len(small_outliers) >= 1:
        small_outliers.sort(key=lambda c: (c["outlier_score"], c["vph"]), reverse=True)
        group1 = small_outliers[:GROUP1_OUTLIER_COUNT]
        for c in group1:
            c["selection_group"] = "small_channel_outlier_surge"
        picked = {c["video_id"] for c in group1}

        remaining = [c for c in scored if c["video_id"] not in picked]
        group2 = sorted(remaining, key=lambda c: c["_velocity"], reverse=True)[:GROUP2_ALLTIME_BENCHMARK_COUNT]
        for c in group2:
            c["selection_group"] = "all_time_top_velocity"
    else:
        # Fallback to standard velocity model (preserves 100% backward compatibility)
        group1 = sorted(scored, key=lambda c: c["_velocity"], reverse=True)[:GROUP1_ALLTIME_COUNT]
        for c in group1:
            c["selection_group"] = "all_time_top_velocity"
        picked = {c["video_id"] for c in group1}

        recent = [
            c for c in scored
            if c["video_id"] not in picked
            and RECENT_WINDOW_MIN_DAYS <= c["age_days"] <= RECENT_WINDOW_MAX_DAYS
            and c.get("comments", 0) >= RECENT_MIN_COMMENTS
        ]
        group2 = sorted(recent, key=lambda c: c["_velocity"], reverse=True)[:GROUP2_RECENT_COUNT]
        for c in group2:
            c["selection_group"] = "recent_90_365_days"

    logger.info("[b15.pass1] selected %d in Group 1 (%s) + %d in Group 2 (%s) from %d candidates",
                len(group1), group1[0]["selection_group"] if group1 else "none",
                len(group2), group2[0]["selection_group"] if group2 else "none",
                len(scored))
    return group1, group2



def fetch_transcript(video_id: str, langs: List[str], head_seconds: int = 180) -> Dict:
    """
    Extract competitor spoken transcript:
      - Tries youtube-transcript-api first.
      - Falls back to audio download + Faster-Whisper transcribe.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        snippets = YouTubeTranscriptApi().fetch(video_id, languages=langs).to_raw_data()
        text = " ".join(s["text"] for s in snippets if s.get("start", 0) < head_seconds)
        if text.strip():
            logger.info("[b15.pass1] %s: captions extracted (%d chars)", video_id, len(text))
            return {"status": "captions", "text": text, "source": "youtube-transcript-api"}
    except Exception as e:
        logger.warning("[b15.pass1] %s: captions unavailable (%s), skipping heavy audio download to conserve bandwidth and time",
                       video_id, type(e).__name__)
        return {"status": "unavailable", "text": None, "source": None}



def download_thumbnail(video_id: str, thumbnails: Dict, dest_dir: Path) -> Optional[str]:
    """Download highest resolution thumbnail to disk for downstream visual reference."""
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
            logger.info("[b15.pass1] %s: saved thumbnail (%s, %d bytes)", video_id, size, len(data))
            return str(dest)
        except Exception as e:
            logger.debug("[b15.pass1] %s: %s thumbnail failed: %s", video_id, size, e)
    return None


def extract_high_engagement_comments(comments: List[Dict], max_count: int = 15) -> List[Dict]:
    """Extract top comments with highest engagement (likes), filtering duplicates and noise."""
    cleaned = []
    seen = set()
    for c in comments:
        text = c.get("text", "").strip()
        if len(text) < 15 or is_spam(text):
            continue
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


def extract_comment_mined_signals(comments: List[Dict]) -> Tuple[List[str], List[str]]:
    """
    Mine comments for two critical strategic signals (Thanh Hai YouTube AI 2026 Playbook):
      1. ai_slop_redlines: Community complaints/eye-rolls about AI slop, fake facts, or generic writing.
      2. audience_wishlist_topics: Explicit viewer requests for future content topics.
    """
    ai_slop = []
    wishlist = []
    seen_slop = set()
    seen_wish = set()

    for c in comments:
        text = c.get("text", "").strip() if isinstance(c, dict) else str(c).strip()
        if not text or is_spam(text):
            continue
        text_norm = " ".join(text.split())

        # Check AI slop / skepticism
        for pat in SLOP_PATTERNS:
            if pat.search(text_norm):
                sample = text_norm[:120]
                if sample.lower() not in seen_slop:
                    seen_slop.add(sample.lower())
                    ai_slop.append(sample)
                break

        # Check Audience content wishlist
        for pat in WISHLIST_PATTERNS:
            if pat.search(text_norm):
                sample = text_norm[:120]
                if sample.lower() not in seen_wish:
                    seen_wish.add(sample.lower())
                    wishlist.append(sample)
                break

    return ai_slop[:5], wishlist[:5]



# ==============================================================================
# SECTION 2: PASS 2 — FORENSIC COMPETITOR ANATOMY & 10X SYNTHESIS (MULTI-TIER LLM) ⭐
# ==============================================================================

def call_recon_forensic_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.4,
    timeout: float = 120.0
) -> str:
    """
    Multi-Tier Resilient LLM Caller for Forensic Competitor Analysis (B1.5):
      - Tier 1: Primary (claude-opus-5-5 -> fallback gpt-6-astra)
      - Tier 2: Resilient Fallback (kimi-k3 -> fallback claude-sonnet-5)
      - Budget & Token Guard: CostTracker integration and error containment
    """
    from app.services.model_gateway import get_global_gateway
    gateway = get_global_gateway()

    # Tier 1: Opus 5.5 (with Astra 6 fallback)
    try:
        logger.info("[b15.llm] Invoking Tier 1: claude-opus-5-5 (fallback gpt-6-astra)...")
        return gateway.call_llm(
            prompt=prompt,
            model="claude-opus-5-5",
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            fallback="gpt-6-astra"
        ).strip()
    except Exception as e_tier1:
        logger.warning(f"[b15.llm] Tier 1 failed ({e_tier1}), falling back to Tier 2: kimi-k3 (fallback claude-sonnet-5)...")

    # Tier 2: Kimi K3 (with Sonnet 5 fallback)
    try:
        return gateway.call_llm(
            prompt=prompt,
            model="kimi-k3",
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            fallback="claude-sonnet-5"
        ).strip()
    except Exception as e_tier2:
        logger.error(f"[b15.llm] Tier 2 also failed ({e_tier2}). Attempting last-resort direct hhtech reasoner...")
        from app.services.hhtech_reasoner import call_gpt6_astra
        return call_gpt6_astra(prompt, system_prompt=system_prompt, max_tokens=max_tokens, timeout=timeout)


def prune_forensic_context(
    target_keyword: str,
    market: str,
    niche: str,
    selected: List[Dict],
    top_comments: List[Dict],
    tri_buckets: Optional[Dict[str, List[Dict]]] = None
) -> Tuple[str, str]:
    """
    Budget & Token Overflow Protection:
      - Limits transcript to MAX_TRANSCRIPT_CHARS_PER_VIDEO (1,200 chars focus on hook/conflict).
      - Limits comments to MAX_COMMENTS_IN_PROMPT (15 comments, max 180 chars).
      - Enriches comment context with 3-bucket signals (Praise, Critique, Unanswered).
      - Prunes descriptions if total prompt approaches MAX_PROMPT_CHARS (10,000 chars).
    """
    bench_summary = []
    for c in selected[:5]:
        ch = c.get("channel", "Unknown")
        ti = c.get("title", "")
        vw = c.get("views", 0)
        subs = c.get("channel_subscribers", 0)
        vs = c.get("v_s_ratio", 0.0)
        vph = c.get("vph", 0.0)
        vpd = c.get("avg_views_per_day", 0)
        grp = c.get("selection_group", "competitor")
        desc = (c.get("description_head", "") or "")[:200]
        raw_tr = (c.get("transcript", {}).get("text") or "")
        tr = raw_tr[:MAX_TRANSCRIPT_CHARS_PER_VIDEO]
        bench_summary.append(
            f"- Channel: [{ch}] (Subs: {subs:,} | Group: {grp})\n"
            f"  Title: \"{ti}\" | Views: {vw:,} | VPH: {vph} | V/S Ratio: {vs}x | Views/day: {vpd:,}\n"
            f"  Opening Hook Transcript (0-180s): {tr}\n"
            f"  Description: {desc}"
        )

    comment_summary = []
    if tri_buckets:
        unanswered = tri_buckets.get("unanswered_questions", [])[:7]
        critique = tri_buckets.get("skepticism_critique", [])[:4]
        praise = tri_buckets.get("praise_resonance", [])[:4]
        for u in unanswered:
            txt = u.get("text", "").strip().replace("\n", " ")[:MAX_COMMENT_CHARS]
            comment_summary.append(f"- [UNANSWERED QUESTION | {u.get('likes', 0)} likes]: \"{txt}\"")
        for cr in critique:
            txt = cr.get("text", "").strip().replace("\n", " ")[:MAX_COMMENT_CHARS]
            comment_summary.append(f"- [AUDIENCE CRITIQUE | {cr.get('likes', 0)} likes]: \"{txt}\"")
        for pr in praise:
            txt = pr.get("text", "").strip().replace("\n", " ")[:MAX_COMMENT_CHARS]
            comment_summary.append(f"- [PRAISE/RESONANCE | {pr.get('likes', 0)} likes]: \"{txt}\"")
    else:
        for g in top_comments[:MAX_COMMENTS_IN_PROMPT]:
            txt = g.get("text", "").strip().replace("\n", " ")[:MAX_COMMENT_CHARS]
            lks = g.get("likes", 0)
            comment_summary.append(f"- [{lks} likes]: \"{txt}\"")

    bench_text = "\n".join(bench_summary) if bench_summary else "No competitor benchmarks available."
    comm_text = "\n".join(comment_summary) if comment_summary else "No comments available."

    total_len = len(bench_text) + len(comm_text)
    if total_len > MAX_PROMPT_CHARS:
        excess = total_len - MAX_PROMPT_CHARS
        bench_text = bench_text[:max(len(bench_text) - excess, 2000)]
        logger.info(f"[b15.token_guard] Pruned prompt context to maintain safety ceiling ({len(bench_text) + len(comm_text)} chars)")

    return bench_text, comm_text


def analyze_competitor_anatomy(task_id: str, target_keyword: str, market: str,
                               selected: List[Dict], top_comments: List[Dict],
                               niche: str = "General",
                               tri_buckets: Optional[Dict[str, List[Dict]]] = None) -> Dict:
    """
    Two-Pass Competitor Recon Reasoning via Multi-Tier LLM (Lead Forensic Story Analyst).
    Uses Astra 6 / Opus 5 (fallback Kimi K3 / Sonnet 5) with token overflow protection.
    """
    try:
        bench_text, comm_text = prune_forensic_context(
            target_keyword, market, niche, selected, top_comments, tri_buckets
        )

        sys_prompt = (
            "You are the Lead Forensic Story Analyst for Video Factory (Pipeline v3).\n"
            "Your mission is to perform deep competitor anatomy on top-performing YouTube videos and high-engagement audience comments, "
            "identifying what made them viral, where their explanations failed, and how our independent investigative documentary can completely outperform them.\n"
            "Return ONLY a valid JSON object with the exact keys described."
        )

        user_prompt = (
            f"Topic / Subject: {target_keyword} (Market: {market.upper()}, Niche: {niche})\n\n"
            f"=== TOP VIRAL COMPETITOR BENCHMARKS (OUTLIERS & ALL-TIME) ===\n{bench_text}\n\n"
            f"=== TOP HIGH-ENGAGEMENT AUDIENCE COMMENTS (TRI-BUCKET INTELLIGENCE) ===\n{comm_text}\n\n"
            "Perform deep structural and audience sentiment analysis. Pay special attention to UNANSWERED QUESTIONS to pinpoint the fatal explanatory vacuum.\n"
            "Provide a JSON response with:\n"
            "{\n"
            '  "competitor_act_breakdown": "Summary of narrative arcs and storyline beats used by competitors (e.g. Act 1 Hook, Act 2 Conflict, Act 3 Climax)",\n'
            '  "competitor_secret_sauce": "What made these videos gain high velocity and views (hook style, pacing, emotional trigger)",\n'
            '  "audience_core_frustrations": [\n'
            '    "Frustration / Unanswered question 1 with context from top comments",\n'
            '    "Frustration / Unanswered question 2",\n'
            '    "Frustration / Unanswered question 3"\n'
            '  ],\n'
            '  "fatal_explanatory_vacuum": "The critical systemic, institutional, financial, or forensic blindspot that competitors completely ignored or glossed over",\n'
            '  "our_10x_pivot_angle": "Our master investigative angle for a 12-15 minute deep-dive that answers audience frustrations and exposes the root causes without mentioning competitor channels",\n'
            '  "transposition_opportunities": {\n'
            '    "proven_structural_vehicle": "The underlying psychological format/hook structure that made rivals succeed (e.g. Unit Economics of Operating an Elite Facility, True Cost of Luxury Illusion)",\n'
            '    "recommended_target_niches": [\n'
            '      "Target sub-niche or historical setting 1 where this exact format can be transplanted",\n'
            '      "Target sub-niche 2"\n'
            '    ]\n'
            '  },\n'
            '  "ai_slop_redlines": [\n'
            '    "Specific generic phrases, bot-like cliches, or superficial errors called out by audience or despised in this niche"\n'
            '  ],\n'
            '  "audience_wishlist_topics": [\n'
            '    "Specific future video topic or investigation explicitly requested by viewers in comments"\n'
            '  ]\n'
            "}\n"
            "Output ONLY valid JSON:"
        )

        logger.info("[b15.reasoning] Invoking Multi-Tier Forensic LLM for Two-Pass Competitor Anatomy...")
        raw_resp = call_recon_forensic_llm(user_prompt, system_prompt=sys_prompt, max_tokens=2000, timeout=120.0)

        m = re.search(r'\{.*\}', raw_resp, re.DOTALL)
        if m:
            anatomy = json.loads(m.group(0))
            logger.info("[b15.reasoning] Successfully extracted 5-pillar competitor narrative anatomy!")
            return anatomy
        else:
            logger.warning("[b15.reasoning] Could not parse JSON from LLM response: %s", raw_resp[:200])
    except Exception as e:
        logger.error("[b15.reasoning] Two-Pass competitor reasoning failed: %s", e)

    # Safe deterministic fallback adhering to investigative docudrama standards
    return {
        "competitor_act_breakdown": "Competitors focused on sensational surface events without institutional depth.",
        "competitor_secret_sauce": "Fast-paced hooks and high sensationalism.",
        "audience_core_frustrations": [
            "Why did regulatory oversight fail to detect this early?",
            "Who were the actual beneficiaries behind the scenes?",
            "What systemic changes were made after the scandal?"
        ],
        "fatal_explanatory_vacuum": "Lack of forensic paper trail and regulatory failure mechanisms.",
        "our_10x_pivot_angle": f"Independent investigative documentary uncovering the hidden systemic mechanisms behind {target_keyword}.",
        "transposition_opportunities": {
            "proven_structural_vehicle": "Forensic systemic breakdown of institutional vulnerabilities",
            "recommended_target_niches": [
                f"Historical parallels to {target_keyword} in industrial history",
                f"Modern digital equivalent of {target_keyword}"
            ]
        },
        "ai_slop_redlines": [
            "Avoid generic AI opening phrases like 'in today's video' or 'have you ever wondered'",
            "Avoid vague moralizing conclusions without specific policy or legal outcomes"
        ],
        "audience_wishlist_topics": []
    }


# ==============================================================================
# SECTION 3: PASS 3 — ASSEMBLY, ARTIFACT PERSISTENCE & NOTION SOT SYNC
# ==============================================================================

def build_intel_card(task_id: str, target_keyword: str, niche: str, market: str,
                     selected: List[Dict], gaps: List[Dict], quota: QuotaTracker,
                     competitor_narrative_anatomy: Optional[Dict] = None,
                     raw_comments: Optional[List[Dict]] = None) -> Dict:
    """Assemble final competitor_intel_card.json adhering strictly to B1.5 -> B2 contract."""
    benchmarks = [{
        "video_id": c.get("video_id", ""),
        "channel": c.get("channel", ""),
        "channel_id": c.get("channel_id", ""),
        "subscriber_count": c.get("channel_subscribers", 0),
        "title": c.get("title", ""),
        "published_at": c.get("published_at", ""),
        "age_days": c.get("age_days", 1),
        "views": c.get("views", 0),
        "likes": c.get("likes", 0),
        "comments": c.get("comments", 0),
        "duration": c.get("duration"),
        "avg_views_per_day": c.get("avg_views_per_day", c.get("views", 0)),
        "vph": c.get("vph", 0.0),
        "v_s_ratio": c.get("v_s_ratio", 0.0),
        "outlier_score": c.get("outlier_score", 0.0),
        "selection_group": c.get("selection_group", "competitor_benchmark"),
        "tags": c.get("tags", []),
        "description_head": c.get("description_head", ""),
        "transcript_status": (c.get("transcript") or {}).get("status", "unavailable"),
        "transcript_source": (c.get("transcript") or {}).get("source"),
        "transcript_head": (c.get("transcript") or {}).get("text"),
        "thumbnail_path": c.get("thumbnail_path"),
    } for c in selected]

    mined_slop, mined_wishlist = extract_comment_mined_signals(raw_comments or gaps)
    anatomy = competitor_narrative_anatomy or {}

    combined_slop = list(dict.fromkeys((anatomy.get("ai_slop_redlines") or []) + mined_slop))
    combined_wishlist = list(dict.fromkeys((anatomy.get("audience_wishlist_topics") or []) + mined_wishlist))
    transposition = anatomy.get("transposition_opportunities", {})
    traffic_bridges = [
        {
            "video_id": b.get("video_id"),
            "title": b.get("title"),
            "channel": b.get("channel"),
            "url": f"https://www.youtube.com/watch?v={b.get('video_id')}" if b.get("video_id") else "",
            "seed_tags": (b.get("tags") or [])[:5],
            "vph": b.get("vph", 0.0)
        }
        for b in benchmarks[:3] if b.get("video_id")
    ]

    card = {
        "task_id": task_id,
        "target_keyword": target_keyword,
        "niche": niche,
        "market": market,
        "traffic_bridges": traffic_bridges,
        "competitor_benchmarks": benchmarks,
        "audience_comment_gaps": [{
            "video_id": g.get("video_id", ""),
            "comment_verbatim": g.get("text", ""),
            "likes_count": g.get("likes", 0),
            "author": g.get("author", "Anonymous"),
            "published_at": g.get("published_at"),
        } for g in gaps],
        "transposition_opportunities": transposition,
        "ai_slop_redlines": combined_slop,
        "audience_wishlist_topics": combined_wishlist,
        "_b2_to_synthesize": [
            "golden_facts_to_keep",
            "competitor_benchmarks[].critical_flaw",
            "competitor_benchmarks[].hook_strategy",
            "audience_comment_gaps[].viewer_frustration",
            "recommended_10x_angle",
            "transposition_opportunities",
            "ai_slop_redlines",
        ],
        "collection_meta": {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "quota_units_spent_today": quota.spent,
            "quota_ratio": round(quota.ratio, 4),
            "quota_fallback_active": quota.should_fallback(),
            "transcripts_captured": sum(
                1 for b in benchmarks if b["transcript_status"] != "unavailable"),
            "thumbnails_captured": sum(1 for b in benchmarks if b["thumbnail_path"]),
            "mined_slop_count": len(combined_slop),
            "mined_wishlist_count": len(combined_wishlist),
        },
    }
    if competitor_narrative_anatomy:
        card["competitor_narrative_anatomy"] = competitor_narrative_anatomy
    return card


def sync_card_to_notion(task_id: str, card: dict) -> bool:
    """Synchronize competitor recon intel and 10x pivot angle to Notion DBs."""
    try:
        import scripts.ag_notion_bridge as bridge
        benchmarks = card.get("competitor_benchmarks", [])
        gaps = card.get("audience_comment_gaps", [])
        anatomy = card.get("competitor_narrative_anatomy") or {}

        lines = []
        if anatomy.get("our_10x_pivot_angle"):
            lines.append(f"🎯 10X PIVOT ANGLE:\n{anatomy['our_10x_pivot_angle']}\n")
        if card.get("transposition_opportunities", {}).get("proven_structural_vehicle"):
            v_name = card["transposition_opportunities"]["proven_structural_vehicle"]
            lines.append(f"⚡ FORMAT WIN VEHICLE:\n{v_name}\n")
        if anatomy.get("fatal_explanatory_vacuum"):
            lines.append(f"⚠️ COMPETITOR BLINDSPOT:\n{anatomy['fatal_explanatory_vacuum']}\n")
        if card.get("ai_slop_redlines"):
            lines.append(f"🚫 AI-SLOP REDLINES:")
            for slop in card["ai_slop_redlines"][:2]:
                lines.append(f"• {slop}")
            lines.append("")

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
                lines.append(f'• \"{txt}\" (👍 {lk})')

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
            logger.info("[b15.sync] Synced Competitor Benchmarks to Trend Brain page %s", page_id)

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
            logger.info("[b15.sync] Synced Competitor Benchmarks to Story Library page %s", s_page_id)

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
                        logger.info("[b15.sync] Appended Competitor Callout Block to Story Library page %s", s_page_id)
                except Exception as c_err:
                    logger.debug("[b15.sync] Callout block append error (non-fatal): %s", c_err)

        return True
    except Exception as e:
        logger.warning("[b15.sync] Failed to sync competitor intel to Notion: %s", e)
        return False


def run_b15(task_id: str, target_keyword: str, niche: str = "General",
            use_cache: bool = True, market: Optional[str] = None,
            anchor_video_id: Optional[str] = None) -> Optional[Dict]:
    """
    Main Orchestrator for B1.5 Two-Pass Competitor Recon:
      Pass 1: Collect candidates, details, transcripts, comments, and thumbnails.
      Pass 2: Reason competitor anatomy and 10x pivot angle via GPT-6-Astra.
      Pass 3: Build card, persist to disk, and sync to Notion SoT.
    """
    load_env()
    market = (market or market_of(task_id)).lower()
    logger.info("[b15] Initiating recon for task=%s keyword=%r market=%s anchor=%s", task_id, target_keyword, market, anchor_video_id)

    # 1. Candidate search with cache support
    cache_path = CACHE_DIR / f"{task_id}.json"
    if use_cache and cache_path.exists():
        logger.info("[b15] Reusing cached search for %s", task_id)
        candidates = json.loads(cache_path.read_text())["candidates"]
        quota = QuotaTracker()
    else:
        api_key = get_api_key() or ""
        quota = QuotaTracker()
        if quota.should_fallback():
            logger.warning("[b15] Quota at %.0f%% of daily cap - zero-quota scraper fallback active", quota.ratio * 100)
        candidates = youtube_search(api_key, target_keyword, market, quota)

        if not candidates:
            logger.warning("[b15] No candidates found for keyword %r (quota exhausted or zero matches). Activating resilient fallback recon card.", target_keyword)
            anatomy = analyze_competitor_anatomy(task_id, target_keyword, market, [], [], niche)
            card = build_intel_card(task_id, target_keyword, niche, market, [], [], quota,
                                    competitor_narrative_anatomy=anatomy, raw_comments=[])
            for target_dir in [EPISODE_DIR / task_id, Path("/root/video_factory/episodes") / task_id]:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    out_p = target_dir / "competitor_intel_card.json"
                    out_p.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
                    logger.info("[b15] Resilient fallback intel card saved to %s", out_p)
                except Exception as e:
                    logger.warning("[b15] Failed to save resilient intel card to %s: %s", target_dir, e)
            try:
                sync_card_to_notion(task_id, card)
            except Exception as e:
                logger.warning("[b15] sync_card_to_notion failed: %s", e)
            return card

        if not quota.should_fallback() and api_key:
            details = youtube_video_details(api_key, [c["video_id"] for c in candidates], quota)
            for c in candidates:
                c.update(details.get(c["video_id"], {}))

        # Batch channel subscriber lookup (1 API unit per 50 channels - Data-Layer Only Protocol)
        c_ids = list({c.get("channel_id") for c in candidates if c.get("channel_id")})
        sub_map = youtube_channel_subscribers(api_key, c_ids, quota) if c_ids and not quota.exhausted else {}
        for c in candidates:
            c["channel_subscribers"] = sub_map.get(c.get("channel_id", ""), 0)

        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "target_keyword": target_keyword,
                "candidates": candidates,
            }, ensure_ascii=False))
        except OSError as e:
            logger.debug("[b15] Cache write failed: %s", e)

    # 1.5 Inject V7 anchor competitor video if provided
    if anchor_video_id:
        if not any(c.get("video_id") == anchor_video_id for c in candidates):
            candidates.insert(0, {"video_id": anchor_video_id, "title": target_keyword, "source": "v7_anchor"})
            logger.info("[b15] Prepended V7 anchor competitor video: %s", anchor_video_id)

    # 2. Select top all-time outliers and recent engagement benchmarks
    group1, group2 = select_competitors(candidates)
    selected = group1 + group2
    if not selected and candidates:
        logger.warning("[b15] Competitor selection formula matched 0 videos, falling back to top candidates directly.")
        selected = candidates[:3]
        for c in selected:
            c.setdefault("selection_group", "top_search_fallback")
            c.setdefault("age_days", age_days(c.get("published_at", "")) or 1)
            c.setdefault("avg_views_per_day", c.get("views", 0) / max(c.get("age_days", 1), 1))
            c.setdefault("vph", calculate_vph(c.get("views", 0), c.get("published_at", "")) or 0.0)
            c.setdefault("channel_subscribers", c.get("channel_subscribers", 0))
            c.setdefault("v_s_ratio", 0.0)
            c.setdefault("outlier_score", 0.0)
            c.setdefault("transcript", {"status": "unavailable", "text": None, "source": None})
            c.setdefault("thumbnail_path", None)
    if not selected:
        anatomy = analyze_competitor_anatomy(task_id, target_keyword, market, [], [], niche)
        card = build_intel_card(task_id, target_keyword, niche, market, [], [], quota,
                                competitor_narrative_anatomy=anatomy, raw_comments=[])
        for target_dir in [EPISODE_DIR / task_id, Path("/root/video_factory/episodes") / task_id]:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                out_p = target_dir / "competitor_intel_card.json"
                out_p.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning("[b15] Failed to save intel card to %s: %s", target_dir, e)
        return card

    api_key = get_api_key() or ""
    asset_dir = EPISODE_DIR / task_id / "competitor_assets"
    langs = MARKET_LOCALE[market]["transcript_langs"]

    # 3. Harvest transcripts, comments, and thumbnails (Pass 1)
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

    # 4. Deep Forensic Anatomy via Multi-Tier LLM (Pass 2) ⭐
    tri_buckets = filter_comment_tri_buckets(all_raw_comments)
    anatomy = analyze_competitor_anatomy(task_id, target_keyword, market, selected, top_comments, niche, tri_buckets=tri_buckets)

    # 5. Assemble Intel Card (Pass 3)
    card = build_intel_card(task_id, target_keyword, niche, market, selected, all_gaps[:12], quota,
                            competitor_narrative_anatomy=anatomy, raw_comments=all_raw_comments)

    # 6. Persist card to both episode root dirs
    for target_dir in [EPISODE_DIR / task_id, Path("/root/video_factory/episodes") / task_id]:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            out_p = target_dir / "competitor_intel_card.json"
            out_p.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("[b15] Intel card saved to %s", out_p)
        except Exception as e:
            logger.warning("[b15] Failed to save intel card to %s: %s", target_dir, e)

    # 7. Sync summary to Notion SoT
    try:
        sync_card_to_notion(task_id, card)
    except Exception as e:
        logger.warning("[b15] sync_card_to_notion failed: %s", e)

    meta = card["collection_meta"]
    logger.info("[b15] Recon completed successfully: %d competitors, %d gaps, %d transcripts, %d thumbnails, quota %d units",
                len(card["competitor_benchmarks"]), len(card["audience_comment_gaps"]),
                meta["transcripts_captured"], meta["thumbnails_captured"], meta["quota_units_spent_today"])
    return card


def main() -> None:
    """CLI entrypoint for standalone testing and pipeline invocation."""
    if len(sys.argv) < 3:
        print("Usage: competitor_recon_b15.py <task_id> <target_keyword> [niche]")
        print("Example: competitor_recon_b15.py en-enron-collapse-ep006 'Enron Scandal Explained' 'Corporate Crime'")
        sys.exit(1)

    task_id, target_keyword = sys.argv[1], sys.argv[2]
    niche = sys.argv[3] if len(sys.argv) > 3 else "General"

    card = run_b15(task_id, target_keyword, niche)
    if not card:
        logger.error("[b15] Recon failed for %s", task_id)
        sys.exit(1)

    out_dir = EPISODE_DIR / task_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "competitor_intel_card.json"
    out_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Intel card saved to {out_path}")
    print(json.dumps(card["collection_meta"], indent=2))


if __name__ == "__main__":
    main()