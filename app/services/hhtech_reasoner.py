# app/services/hhtech_reasoner.py
"""
HHTech Reasoning Service via GPT-5.6-Sol (Sole Gateway Model).
Standardized Architecture (24/08/2026 - Go-Live 2026):
  - English-First System Prompt for maximum reasoning depth & zero stereotyping.
  - Native Evidence Grounding (Wikipedia Japanese / Korean / English summaries).
  - Google Trends Rising / Breakout Queries Injection for Act 1 Hook Shock.
  - YouTube Safety Labeling & 4-Tier Content Categorization (Decisions 19/08 - 24/08).
  - Vietnamese Output for Human Gate 1 (topic_name_vi, niche_angle_brief, story_direction_5_arcs).

PATTERN 3 UPDATE (02/09/2026):
  - Routed through Model Gateway for automatic cost tracking and budget enforcement
  - 300k VND monthly cap enforced at gateway layer
  - Fallback support to Anthropic Claude if HHTech fails
"""

import os, json, logging, re, urllib.request, urllib.parse
from app.services.skill_loader import get_skill_rules
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

HHTECH_BASE_URL = os.getenv("HHTECH_BASE_URL", "https://hhtechapi.com/v1")
HHTECH_MODEL = os.getenv("HHTECH_MODEL", "gpt-5.6-sol")

def get_hhtech_key() -> str:
    key = os.getenv("HHTECH_API_KEY")
    if not key:
        try:
            envp = os.path.join("/root", "secrets", ".env")
            if os.path.exists(envp):
                with open(envp, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("HHTECH_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if key:
                                os.environ["HHTECH_API_KEY"] = key
        except Exception:
            pass
    return key or ""

def is_clean_search_query(q: str) -> bool:
    if not q or not isinstance(q, str):
        return False
    q_clean = q.strip()
    if len(q_clean) < 2 or len(q_clean) > 120:
        return False
    if re.search(r'https?://|\b(?:404|500|502|503|504|null|undefined|nan)\b', q_clean, re.I):
        return False
    return True

def extract_clean_breakout_queries(rising_queries: list, max_count: int = 5) -> list[str]:
    if not rising_queries:
        return []
    res = []
    seen = set()
    for item in rising_queries:
        q = ""
        if isinstance(item, dict):
            q = str(item.get("query", "")).strip()
        elif isinstance(item, str):
            q = item.strip()
        if q and is_clean_search_query(q):
            low = q.lower()
            if low not in seen:
                seen.add(low)
                res.append(q)
    return res[:max_count]

def detect_safety_and_theme(subject: str, market: str = "US") -> tuple[str, str, str]:
    """Detect 4-Tier Content Theme, YouTube Safety Label, and Treatment Note from subject keywords."""
    text = (subject or "").lower()
    
    truecrime_terms = ['killer', 'ripper', 'murder', 'serial', 'gacy', 'bundy', 'dahmer', 'rader', 'golden state', '조두순', 'n번방', 'nth room', 'sarin', '오우무', 'aum', '真理教', 'サリン', '신창원', '유영철']
    fraud_terms = ['fraud', 'scam', 'ponzi', 'madoff', 'enron', 'ftx', 'theranos', 'livedoor', 'ライブドア', 'worldcom', 'lehman', '다단계', '보이스피싱', '전세사기', '동양그룹', '東芝不正会計', 'オリンパス']
    gambling_terms = ['gambling', 'casino', 'slot', 'pachinko', 'パチンコ', '도박', '강원랜드', '바다이야기', '사행성']
    societal_terms = ['kodokushi', '孤独死', '過労死', 'ひきこもり', '引きこもり', '고독사', '은둔']
    history_terms = ['war', 'uprising', 'movement', 'occupation', '광주', '민주화', '일제강점기', '한국전쟁', '제주 4.3', '을미사변', 'roman empire', 'byzantine', 'crusade', 'genghis khan', 'mongol', 'ottoman', 'tulip mania']
    
    if any(t in text for t in truecrime_terms):
        return (
            "true_crime_investigative",
            "YT-Sensitive-TrueCrime",
            "CASE-SOLVING DOCUMENTARY ONLY: focus strictly on forensic reasoning, investigative breakthrough, institutional failure, and legal accountability; ZERO graphic gore, ZERO method instruction, ZERO victim exploitation, and ZERO killer glorification."
        )
    elif any(t in text for t in gambling_terms):
        return (
            "psychology_manipulation_fraud",
            "YT-Gambling-Awareness",
            "GAMBLING AWARENESS ONLY: cautionary educational framing dissecting psychological manipulation traps and regulatory loopholes; ZERO promotion or glamorization of illicit gambling."
        )
    elif any(t in text for t in fraud_terms):
        return (
            "business_rise_fall",
            "YT-Fraud-Education",
            "BUSINESS & FRAUD EDUCATION: dissect financial engineering, accounting loopholes, leverage spirals, and executive hubris; strictly educational with verified public records."
        )
    elif any(t in text for t in societal_terms):
        return (
            "psychology_manipulation_fraud",
            "YT-Societal-Crisis-Documentary",
            "SOCIETAL CRISIS DOCUMENTARY: objective socio-economic analysis of demographic shifts and welfare safety net gaps; empathetic, constructive, and systemic."
        )
    elif any(t in text for t in history_terms):
        return (
            "modern_history_untold",
            "YT-History-Factual-Neutral",
            "FACTUAL HISTORY DOCUMENTARY: objective analysis of institutional decay, economic debasement, and systemic power dynamics backed by historical sources."
        )
    
    return (
        "business_rise_fall",
        "YT-Safe-Standard",
        "Standard platform-safe nonfiction documentary treatment focusing on institutional and economic mechanisms."
    )

def _fetch_native_wiki_extract(subject: str, market: str) -> str:
    """Fetch factual native Wikipedia summary for the subject."""
    lang_map = {"JP": "ja", "KR": "ko", "EN": "en", "US": "en", "GB": "en", "AU": "en", "CA": "en", "DE": "de", "NZ": "en"}
    lang = lang_map.get(market.upper(), "en")
    
    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(subject.replace(' ', '_'))}"
        req = urllib.request.Request(url, headers={"User-Agent": "VF-Reasoner/2.0"})
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract", "")
            if extract:
                return extract[:1500]
    except Exception:
        pass
    return ""

def call_gpt56_sol(
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
    timeout: float = 60.0
) -> str:
    """
    Synchronous caller for GPT-5.6-Sol via Model Gateway (Pattern 3).
    
    Automatically tracks costs and enforces 300k VND monthly budget.
    Falls back to Anthropic Claude if HHTech fails (optional).
    
    Args:
        prompt: User prompt text
        system_prompt: Optional system prompt
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        timeout: Request timeout in seconds
    
    Returns:
        Generated text response
    
    Raises:
        CostCapExceededError: If monthly budget would be exceeded
        ModelGatewayError: If API call fails
    """
    from app.services.model_gateway import get_global_gateway
    
    try:
        gateway = get_global_gateway()
        result = gateway.call_llm(
            prompt=prompt,
            model=HHTECH_MODEL,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            fallback=None  # No fallback by default; can enable with "claude-3.5-sonnet"
        )
        return result.strip()
    
    except Exception as e:
        # Log error and re-raise
        logger.error(f"[hhtech] Model gateway call failed: {e}")
        raise

def reason_topic_niche(
    subject: str,
    market: str,
    virality_score: float = 0.85,
    rising_queries: list | None = None,
    top_queries: list | None = None,
    viral_videos: list | None = None
) -> dict:
    """Call GPT-5.6-Sol via HHTech API with native signals and YouTube Safety Labeling
    to analyze topic objectively, refine native search keywords, and output 5-Act outline for Human Gate 1.
    """
    key = get_hhtech_key()
    if not key:
        logger.error("[hhtech] HHTECH_API_KEY is missing!")
        return _fallback_topic(subject, market, virality_score, rising_queries)

    m_up = (market or "EN").strip().upper()
    theme, safety_label, treatment_note = detect_safety_and_theme(subject, m_up)

    # 1. Fetch Native Ground Truth Extract
    native_extract = _fetch_native_wiki_extract(subject, m_up)
    extract_text = ""
    if native_extract:
        extract_text = f"\n[NATIVE MARKET GROUND TRUTH EVIDENCE ({m_up})]:\n{native_extract}\n"

    # 2. Format breakout & top queries text
    breakout_text = ""
    if rising_queries:
        lines = []
        for item in rising_queries[:10]:
            if isinstance(item, dict):
                q = str(item.get("query", "")).strip()
                v = item.get("value", "")
                if is_clean_search_query(q):
                    lines.append(f'  - "{q}" ({v})')
            elif isinstance(item, str) and is_clean_search_query(item):
                lines.append(f'  - "{item}"')
        if lines:
            breakout_text = "\n[GOOGLE TRENDS RISING / BREAKOUT QUERIES (NATIVE LANGUAGE)]:\n" + "\n".join(lines) + "\n"

    top_text = ""
    if top_queries:
        lines = []
        for item in top_queries[:5]:
            if isinstance(item, dict):
                q = str(item.get("query", "")).strip()
                v = item.get("value", "")
                if is_clean_search_query(q):
                    lines.append(f'  - "{q}" (Index: {v})')
            elif isinstance(item, str) and is_clean_search_query(item):
                lines.append(f'  - "{item}"')
        if lines:
            top_text = "\n[TOP SEARCH QUERIES]:\n" + "\n".join(lines) + "\n"

    viral_videos_text = ""
    if viral_videos:
        v_lines = []
        for v in viral_videos[:6]:
            t = str(v.get("title", "")).strip()
            vc = v.get("views", 0)
            pub = str(v.get("published_at", ""))[:10]
            if t:
                v_lines.append(f'  - "{t}" ({vc:,} views, published: {pub})' if isinstance(vc, int) else f'  - "{t}"')
        if v_lines:
            viral_videos_text = "\n[YOUTUBE LIVE VIRAL BENCHMARKS & ALGORITHM RECOMMENDATIONS]:\n" + "\n".join(v_lines) + "\n"

    # 3. Universal English-First Strategic System Prompt (Objective & Free of Stereotypes)
    skill_rules = get_skill_rules()  # Dynamic load from Notion Skill AI

    system_prompt = (
        "You are the Lead Creative Director and Strategic Research Analyst for Video Factory (VF Pipeline).\n"
        "Your mission is to perform an objective, deep-dive causal analysis of the trending topic using the provided factual evidence (Native Ground Truth) and breakout search signals.\n\n"
        f"{skill_rules}\n\n"  # ← DYNAMIC RULES from Notion
        "4. PLATFORM SAFETY MANDATE: Strictly respect the YouTube Safety Treatment Note below:\n"
        f"   [SAFETY RULE: {safety_label}]: {treatment_note}\n"
        "5. SEARCH-SPECIFIC TARGETING: Formulate 'search_specific_keyword' in the TARGET MARKET'S NATIVE LANGUAGE (Japanese for JP, Korean for KR, English for EN) incorporating high-intent core keywords and breakout terms for YouTube search optimization.\n"
        "6. HUMAN GATE 1 COMPLIANCE: Produce 'topic_name_vi', 'niche_angle_brief', and 'story_direction_5_arcs' in natural, professional Vietnamese with full diacritics for human editorial review.\n\n"
        "Output ONLY a valid JSON object matching the requested schema without markdown code fences."
    )

    user_prompt = (
        f"Target Market: {m_up}\n"
        f"Raw Trending Subject: \"{subject}\" (Virality Score: {virality_score})\n"
        f"Assigned Content Theme: {theme}\n"
        f"Assigned Safety Label: {safety_label}\n"
        f"{extract_text}"
        f"{breakout_text}"
        f"{top_text}"
        f"{viral_videos_text}\n"
        "STRATEGIC INSTRUCTIONS (MANDATORY ALGORITHMIC SURGE ANCHOR & BLUE OCEAN DIFFERENTIATION):\n"
        "0.1. BLUE OCEAN DIFFERENTIATION: Analyze the competitor video titles above. Identify their superficial gaps (e.g. generic highlight, daily news, surface gossip) and formulate 'competitor_differentiation_gap' in Vietnamese detailing the structural mechanism, forensic truth, or institutional lesson that our video delivers which competitors completely missed.\n"
        "0. SURGE ANCHOR (RULE 118 ZERO-MOCK): The topic and 'niche_angle_brief' MUST be directly anchored to either one of the real rising search queries (e.g. 그라목손 / Gramoxone, 배추 농약) OR the proven viral mechanics from the million-view YouTube videos above. CẤM TUYỆT ĐỐI tự sáng tác một đề tài xa lạ không có trong dữ liệu tìm kiếm thật.\n"
        "1. 'search_specific_keyword': Must be in the TARGET MARKET NATIVE LANGUAGE (Japanese for JP, Korean for KR, English for EN), combining core event names, key figures, and breakout search terms.\n"
        "2. 'breakout_queries': Top 3-5 breakout/rising query strings in the native market language.\n"
        "3. 'task_slug': Concise lowercase-hyphenated English slug (max 25 characters, e.g. livedoor-scandal).\n"
        "4. 'topic_name_vi': Sharp, high-retention Vietnamese title for the episode.\n"
        "5. 'niche_angle_brief': 1 concise sentence in Vietnamese explaining the core Big Fish Small Pond mechanism.\n"
        "6. 'story_direction_5_arcs': Structured 5-Beat Investigative Docudrama outline in Vietnamese: Beat 1 (Nghịch lý mở màn 0-60s & An Ong Hook) -> Beat 2 (Bẫy truyền thông & Red Herring/Sai lầm đối thủ) -> Beat 3 (Manh mối rò rỉ & Vết nứt thể chế / Fatal Explanatory Vacuum) -> Beat 4 (Cỗ máy lợi ích & Smoking Gun vạch trần / Climax) -> Beat 5 (Gương soi hiện tại & Lời cảnh báo / Living Warning).\n\n"
        "Return EXACT JSON matching this schema:\n"
        "{\n"
        '  "topic_name_vi": "<Tên đề tài tiếng Việt sắc bén>",\n'
        '  "search_specific_keyword": "<Từ khóa tìm kiếm chuyên sâu bằng TIẾNG BẢN XỨ (JP/KR/EN)>",\n'
        '  "task_slug": "<english-lowercase-slug>",\n'
        '  "competitor_differentiation_gap": "<1-2 cau phan tich ro diem mu cua cac video doi thu va goc nhin doc ban khac biet cua video nay>",\n'
        '  "niche_angle_brief": "<1 câu đúc kết góc nhìn ngách Big Fish Small Pond bằng tiếng Việt>",\n'
        '  "story_direction_5_arcs": "Beat 1 (Nghịch lý mở màn 0-60s): ... -> Beat 2 (Bẫy truyền thông/Red Herring): ... -> Beat 3 (Manh mối rò rỉ/Fatal Vacuum): ... -> Beat 4 (Cỗ máy lợi ích/Smoking Gun): ... -> Beat 5 (Gương soi hiện tại/Lời cảnh báo): ...",\n'
        '  "breakout_queries": ["<native breakout query 1>", "<native breakout query 2>"],\n'
        f'  "content_theme": "{theme}",\n'
        f'  "safety_label": "{safety_label}",\n'
        f'  "treatment_note": "{treatment_note}"\n'
        "}"
    )

    try:
        logger.info(f"[hhtech] Calling {HHTECH_MODEL} for topic: {subject} ({m_up}) with safety: {safety_label} & {len(rising_queries or [])} rising queries...")
        content = call_gpt56_sol(user_prompt, system_prompt=system_prompt, max_tokens=2500, timeout=50.0)
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        parsed = json.loads(content)

        # Ensure safety fields are populated
        parsed["content_theme"] = parsed.get("content_theme") or theme
        parsed["safety_label"] = parsed.get("safety_label") or safety_label
        parsed["treatment_note"] = parsed.get("treatment_note") or treatment_note

        # Post-process & sanitize breakout_queries
        bqs = parsed.get("breakout_queries")
        clean_bqs = []
        if isinstance(bqs, list):
            for q in bqs:
                q_str = str(q).strip()
                if is_clean_search_query(q_str) and q_str.lower() not in [x.lower() for x in clean_bqs]:
                    clean_bqs.append(q_str)
        if not clean_bqs and rising_queries:
            clean_bqs = extract_clean_breakout_queries(rising_queries, max_count=5)
        parsed["breakout_queries"] = clean_bqs[:5]

        logger.info(f"[hhtech] GPT-5.6-Sol reasoning success for {subject} ({m_up}) -> slug: {parsed.get('task_slug')}, safety: {parsed.get('safety_label')}")
        return parsed
    except Exception as e:
        logger.error(f"[hhtech] Exception calling GPT-5.6-Sol for {subject} ({m_up}): {e}")

    return _fallback_topic(subject, market, virality_score, rising_queries)


def _fallback_topic(subject: str, market: str, virality_score: float, rising_queries: list | None = None) -> dict:
    clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(subject).lower()).strip('-')[:20] or 'topic'
    search_key = str(subject)
    clean_bqs = extract_clean_breakout_queries(rising_queries or [], max_count=5)
    if clean_bqs:
        search_key = f"{subject} {clean_bqs[0]}"

    theme, safety_label, treatment_note = detect_safety_and_theme(subject, market)

    return {
        "topic_name_vi": f"{subject} ({market})",
        "search_specific_keyword": search_key,
        "task_slug": clean_slug,
        "niche_angle_brief": f"Đào sâu góc nhìn ngách và cơ chế bản chất của {subject} tại thị trường {market} theo Big Fish Small Pond.",
        "story_direction_5_arcs": "Beat 1: Nghịch lý mở màn 0-60s -> Beat 2: Bẫy truyền thông & Red Herring -> Beat 3: Manh mối rò rỉ & Vết nứt thể chế -> Beat 4: Cỗ máy lợi ích & Smoking Gun -> Beat 5: Gương soi hiện tại & Lời cảnh báo",
        "breakout_queries": clean_bqs,
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note
    }



def assess_keyword_video_viability(
    keyword: str = None,
    market: str = "EN",
    search_signals: dict | None = None,
    term: str = None,
    traffic: str = None,
    rising_queries: list | None = None,
    top_videos: list | None = None,
    **kwargs
) -> dict:
    """Pre-Selection Video-Viability Skill for GPT-5.6-Sol (User Rule 05/09/2026).
    Evaluates raw candidate keywords on whether they can viably sustain an 8-12 min
    high-retention 5-act non-fiction video with 2-layer Remotion illustration.
    """
    keyword = keyword or term or ""
    m_up = (market or "EN").strip().upper()
    theme, safety_label, treatment_note = detect_safety_and_theme(keyword, m_up)
    
    if search_signals is None:
        search_signals = {}
    if traffic and "traffic" not in search_signals:
        search_signals["traffic"] = traffic
    if rising_queries and "rising_queries" not in search_signals:
        search_signals["rising_queries"] = rising_queries
    if top_videos and "top_videos" not in search_signals:
        search_signals["top_videos"] = top_videos

    signals_str = ""
    if search_signals:
        signals_str = f"Search Signals: {json.dumps(search_signals, ensure_ascii=False)}\n"

    system_prompt = (
        "You are the Chief Executive Producer and Video Viability Auditor for Video Factory.\n"
        "Your role is to rigorously evaluate whether a raw trending keyword can be turned into a "
        "compelling, high-retention 8-12 minute non-fiction investigative documentary video.\n\n"
        "CRITICAL EVALUATION CRITERIA (4 PILLARS):\n"
        "1. VISUAL FEASIBILITY (Layer 1 BG 16:9 + Layer 2 FG Transparent PNG):\n"
        "   - Can the story be staged with tangible visual scenes (boardrooms, trading desks, courtrooms, labs, archives, historical streets)?\n"
        "   - REJECT if purely abstract math/financial formula with zero concrete physical scenes or identifiable decision-makers.\n"
        "2. CAUSAL CONFLICT DEPTH (Rule 1-4, 78 Big Fish Small Pond):\n"
        "   - Is there a systemic mechanism, regulatory loophole, executive hubris, or institutional betrayal?\n"
        "   - REJECT if it is merely generic everyday gossip, simple celebrity news, or a routine press release.\n"
        "3. RULE 444 HOOK POTENTIAL (5-10s Quantitative Shock):\n"
        "   - Can we extract a visceral number, paradox, dollar loss, or ticking clock for the first 5 seconds?\n"
        "4. AUDIENCE RETENTION APPEAL:\n"
        "   - Does the topic have viral curiosity for mobile cold-traffic?\n"
        "5. ALGORITHMIC & AUDIENCE SURGE ANCHOR (RULE 118 ZERO-MOCK DATA):\n"
        "   - The 'specific_viral_angle' MUST directly stem from the ACTUAL TOP RISING SEARCH QUERIES or the ACTUAL TOP VIRAL YOUTUBE VIDEO CONCEPTS provided in the Search Signals.\n"
        "   - FORBIDDEN: Hallucinating or inventing an unrelated niche topic that is NOT reflected in the rising queries or viral video signals (e.g. Do NOT turn 'pesticides' into 'animal testing for 90 days' if the community is searching for 'Gramoxone poisoning' or 'cabbage pesticide residue').\n\n"
        "Output ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "is_video_viable": true|false,\n'
        '  "viability_score": <float 1.0 to 10.0>,\n'
        '  "verdict": "APPROVED"|"REJECTED",\n'
        '  "specific_viral_angle": "<Specific 10x concrete video title/angle instead of generic subject>",\n'
        '  "visual_feasibility_score": <int 1 to 10>,\n'
        '  "conflict_depth_score": <int 1 to 10>,\n'
        '  "rejection_reason": "<string if rejected, else null>"\n'
        "}"
    )

    user_prompt = (
        f"Candidate Keyword: {keyword}\n"
        f"Target Market: {m_up}\n"
        f"Detected Content Theme: {theme}\n"
        f"Platform Safety Label: {safety_label}\n"
        f"{signals_str}\n"
        "Evaluate this keyword now. If approved, formulate a razor-sharp 'specific_viral_angle' (e.g. from 'Enron' -> 'How Enron Staged Fake Trading Floors to Scam $30B')."
    )

    try:
        raw_res = call_gpt56_sol(user_prompt, system_prompt=system_prompt, max_tokens=1000, timeout=75.0)
        clean_json = raw_res.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)
        data = json.loads(clean_json)
        return data
    except Exception as e:
        logger.warning(f"[hhtech] assess_keyword_video_viability failed: {e}")
        return {
            "is_video_viable": True,
            "viability_score": 7.0,
            "verdict": "APPROVED_BY_FALLBACK",
            "specific_viral_angle": keyword,
            "visual_feasibility_score": 7,
            "conflict_depth_score": 7,
            "rejection_reason": None
        }
