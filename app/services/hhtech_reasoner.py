# app/services/hhtech_reasoner.py
"""
HHTech Reasoning Service via GPT-6-Astra (Sole Gateway Model).
Standardized Architecture (24/08/2026 - Go-Live 2026):
  - English-First System Prompt for maximum reasoning depth & zero stereotyping.
  - Native Evidence Grounding (Wikipedia Japanese / Korean / English summaries).
  - Google Trends Rising / Breakout Queries Injection for Act 1 Hook Shock.
  - YouTube Safety Labeling & 4-Tier Content Categorization (Decisions 19/08 - 24/08).
  - Vietnamese Output for Human Gate 1 (topic_name_vi, niche_angle_brief, story_direction_5_arcs).

PATTERN 3 UPDATE (02/09/2026):
  - Routed through Model Gateway for automatic cost tracking and telemetry
  - Fallback support to Anthropic Claude if HHTech fails
"""

import os, json, logging, re, urllib.request, urllib.parse
from app.services.skill_loader import get_skill_rules, get_b1_strategic_rules
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

HHTECH_BASE_URL = os.getenv("HHTECH_BASE_URL", "https://hhtechapi.com/v1")
HHTECH_MODEL = os.getenv("HHTECH_MODEL", "gpt-6-astra")

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
    elif any(t in text for t in ['chip', 'semiconductor', 'asml', 'tsmc', 'huawei', 'nvidia', 'geopolitic', 'supply chain', 'lithography', 'satellite', 'submarine cable', 'rare earth', 'quantum', 'embargo', 'sanction', 'trade war', 'export control', 'ban', 'switch']):
        return (
            "tech_geopolitical_battle",
            "YT-Tech-Geopolitical-Investigation",
            "TECH & GEOPOLITICAL INVESTIGATION: analyze technological chokeholds, semiconductor espionage, state-subsidized dominance, and supply chain warfare with verified industrial and trade records."
        )
    elif any(t in text for t in ['ancient', 'gobekli', 'göbekli', 'younger dryas', 'denisovan', 'megalith', 'clovis', 'prehistoric', 'lost civilization', 'civilization', 'ice age', 'stonehenge', 'sundaland', 'neanderthal', 'australopithecus', 'archaeolog', 'fossil', 'hominid', '잃어버린 문명', '선사시대', '고대 인류', '고대 문명', '縄文', '古代文明', 'ancient humans']):
        return (
            "ancient_prehistory_anthropology",
            "YT-Educational-Anthropology",
            "PREHISTORIC ANTHROPOLOGY & ANCIENT HUMAN SURVIVAL: forensic deep-dive into fossil evidence, archaeological stratigraphy, and evolutionary mechanics; strictly educational and evidence-grounded."
        )
    elif any(t in text for t in ['stoic', 'stoicism', 'marcus aurelius', 'seneca', 'epictetus', 'musashi', 'dokkodo', '독행도', '스토아', '아우렐리우스', 'burnout', 'mental resilience', 'zen detachment', '번아웃', '孤独の力', '宮本武蔵', '折れない心', '人間関係の疲れ', '내면의 평화', '감정 조절']):
        return (
            "indigenous_philosophy_stoicism",
            "YT-Philosophy-Mindset",
            "INDIGENOUS PHILOSOPHY & CONTEMPLATIVE RESILIENCE: dissect ancient mindset protocols applied to modern institutional burnout; calm, reflective, grounded in primary historical texts."
        )
    elif any(t in text for t in ['military logistics', 'geopolitical choke', 'malacca', 'undersea cable', 'starfish prime', 'supply line', 'airlift', 'defense doctrine', 'strategic blunder', '군사 물류', '지정학', '해저 케이블', '兵站', 'チョークポイント', 'chokepoint', 'blockade']):
        return (
            "military_logistics_geopolitics",
            "YT-Military-Tactical-Investigation",
            "MILITARY LOGISTICS & GEOPOLITICAL CHOKEPOINTS: forensic deconstruction of supply line failures, tactical blunders, and strategic infrastructure chokepoints based on declassified records; ZERO glorification of violence."
        )
    elif any(t in text for t in ["refund", "환불", "교환", "반품", "영수증", "바가지", "동탄문구점", "bẫy giá", "giấu giá", "hóa đơn", "không hoàn tiền", "no refund", "cancellation fee", "hidden fee", "hidden cost", "fine print", "consumer trap", "소비자 분쟁", "위약금", "단순 변심", "가격표시제", "bất cân xứng tiêu dùng", "chèn ép người mua", "quy chế hoàn tiền", "overcharge", "unilateral clause", "consumer dispute", "subscription trap"]):
        return (
            "consumer_injustice_institutional_trap",
            "YT-Consumer-Awareness",
            "SOCIAL REALITY & CONSUMER INJUSTICE DOCUDRAMA: dissect everyday retail traps, asymmetric contract fine print, and regulatory loopholes; empathetic focus on victim struggle and institutional confrontation; ZERO defamation, strictly verified public records."
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

def call_gpt6_astra(
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
    timeout: float = 60.0
) -> str:
    """
    Synchronous caller for GPT-6-Astra via Model Gateway with Multi-Tier Fallback:
      - Tier 1: Primary (gpt-6-astra -> fallback claude-opus-5)
      - Tier 2: Resilient Fallback (kimi-k3 -> fallback claude-sonnet-5)
    Automatically tracks model usage telemetry and guards against token overflow.
    """
    from app.services.model_gateway import get_global_gateway
    gateway = get_global_gateway()

    # Budget / token guard: Cap prompt if excessively long (User approved 40k token ceiling ~150k chars)
    if len(prompt) > 150_000:
        logger.warning(f"[hhtech] Prompt length {len(prompt)} exceeds 150k chars (40k tokens), pruning to 120k to avoid token overflow.")
        prompt = prompt[:120_000]

    # Tier 1: Primary Astra 6 with Opus 5 fallback
    try:
        result = gateway.call_llm(
            prompt=prompt,
            model=HHTECH_MODEL,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            fallback="claude-opus-5"
        )
        return result.strip()
    except Exception as e_t1:
        logger.warning(f"[hhtech] Primary Tier 1 failed ({e_t1}), falling back to Tier 2 (kimi-k3 -> claude-sonnet-5)...")

    # Tier 2: Kimi K3 with Sonnet 5 fallback
    try:
        result = gateway.call_llm(
            prompt=prompt,
            model="kimi-k3",
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            fallback="claude-sonnet-5"
        )
        return result.strip()
    except Exception as e_t2:
        logger.error(f"[hhtech] All gateway tiers failed ({e_t2})")
        raise

# Backward-compatibility alias during migration
call_gpt56_sol = call_gpt6_astra

def reason_topic_niche(
    subject: str,
    market: str,
    virality_score: float = 0.85,
    rising_queries: list | None = None,
    top_queries: list | None = None,
    viral_videos: list | None = None,
    news_catalysts: list | None = None
) -> dict:
    """Call GPT-6-Astra via HHTech API with native signals and YouTube Safety Labeling
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
            if isinstance(v, str):
                t = v.strip()
                vc = 0
                pub = ""
            elif isinstance(v, dict):
                t = str(v.get("title", "")).strip()
                vc = v.get("views", 0)
                pub = str(v.get("published_at", ""))[:10]
            else:
                continue
            if t:
                v_lines.append(f'  - "{t}" ({vc:,} views, published: {pub})' if isinstance(vc, int) and vc > 0 else f'  - "{t}"')
        if v_lines:
            viral_videos_text = "\n[YOUTUBE LIVE VIRAL BENCHMARKS & ALGORITHM RECOMMENDATIONS]:\n" + "\n".join(v_lines) + "\n"

    news_catalysts_text = ""
    if news_catalysts:
        n_lines = []
        for n in news_catalysts[:6]:
            t = n.get("title", "").strip()
            d = n.get("description", "").strip()
            p = n.get("published_at", "").strip()
            if t:
                n_lines.append(f'  - [{p}] "{t}" ({d[:120]})')
        if n_lines:
            news_catalysts_text = "\n[LIVE BREAKING NEWS CATALYSTS (PAST 24-48H) — MANDATORY REAL-WORLD ANCHOR (RULE 130)]:\n" + "\n".join(n_lines) + "\n"

    # 3. Universal English-First Strategic System Prompt (Objective & Free of Stereotypes)
    skill_rules = get_b1_strategic_rules()  # Concise B1 strategic rules (prevents prompt contamination)

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
        f"{viral_videos_text}"
        f"{news_catalysts_text}\n"
        "STRATEGIC INSTRUCTIONS (MANDATORY ALGORITHMIC SURGE ANCHOR & BLUE OCEAN DIFFERENTIATION):\n"
        "0.0. CONTEMPORARY EVENT ANCHOR (RULE 130 ENFORCED): If live breaking news catalysts are provided above, your topic and 'niche_angle_brief' MUST directly explain the breaking real-world catalyst event (who, what, when) that caused viewers to search for this term today. CẤM TUYỆT ĐỐI bẻ lái sang bài toán doanh nghiệp/kế toán/lịch sử xa xưa mà bỏ rơi ngòi nổ thời sự 48h qua.\n"
        "0.1. BLUE OCEAN DIFFERENTIATION: Analyze the competitor video titles above. Identify their superficial gaps (e.g. generic highlight, daily news, surface gossip) and formulate 'competitor_differentiation_gap' in Vietnamese detailing the structural mechanism, forensic truth, or institutional lesson that our video delivers which competitors completely missed.\n"
        "0. SURGE ANCHOR (RULE 118 ZERO-MOCK): The topic and 'niche_angle_brief' MUST be directly anchored to either one of the real rising search queries from the data above OR the proven viral mechanics from the million-view YouTube videos above. CẤM TUYỆT ĐỐI tự sáng tác một đề tài xa lạ không có trong dữ liệu tìm kiếm thật.\n"
        "1. 'search_specific_keyword': High-intent search phrase in TARGET MARKET NATIVE LANGUAGE (Japanese for JP, Korean for KR, English for EN), strictly 3 to 5 words maximum (e.g. '<PRIMARY_ENTITY> <CORE_SURGE_QUERY>'). CẤM TUYỆT ĐỐI nhồi nhét chuỗi từ khóa dài quá 5 từ.\n"
        "2. 'breakout_queries': Top 3-5 breakout/rising query strings in the native market language.\n"
        "3. 'task_slug': Concise lowercase-hyphenated English slug (max 25 characters, e.g. <topic>-<angle>).\n"
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
        content = call_gpt6_astra(user_prompt, system_prompt=system_prompt, max_tokens=2500, timeout=50.0)
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

        # Post-process & sanitize search_specific_keyword (anti-keyword stuffing: max 4-5 words)
        raw_kw = str(parsed.get("search_specific_keyword") or "").strip()
        if raw_kw:
            kw_words = raw_kw.split()
            if len(kw_words) > 5:
                parsed["search_specific_keyword"] = " ".join(kw_words[:4])

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

        logger.info(f"[hhtech] GPT-6-Astra reasoning success for {subject} ({m_up}) -> slug: {parsed.get('task_slug')}, safety: {parsed.get('safety_label')}")
        return parsed
    except Exception as e:
        logger.error(f"[hhtech] Exception calling GPT-6-Astra for {subject} ({m_up}): {e}")

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
    """Pre-Selection Video-Viability Skill for GPT-6-Astra (User Rule 05/09/2026).
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
        "MANDATORY SCOPE: 11 HIGH-RPM/HIGH-RETENTION NON-FICTION CONTENT PILLARS:\n"
        "The candidate topic MUST strictly fall into one of these pillars:\n"
        "  1. Business Rise & Fall: Financial engineering, corporate collapse, accounting fraud, executive hubris.\n"
        "  2. Modern History & Systemic Crisis: 20th-21st century turning points, institutional failure, declassified operations.\n"
        "  3. True Crime Non-Graphic: White-collar schemes, forensic timeline, investigative breakthroughs; ZERO graphic gore.\n"
        "  4. Psychology & Behavioral Manipulation: Mass hysteria, cults, psychological manipulation traps, cognitive biases.\n"
        "  5. Tech & Geopolitical Systemic Battles: Semiconductor wars, supply chain chokeholds, submarine telecom cables, tech espionage.\n"
        "  6. Institutional & Regulatory Chokepoints: Policy loopholes, pension/insurance failures, testing/quality falsification cover-ups.\n"
        "  7. Hidden Asymmetric Fortunes & Underground Flows: Underground flows, money laundering, information asymmetry schemes.\n"
        "  8. Ancient Prehistory & Lost Civilizations: Forensic archaeological evidence, evolutionary survival mechanisms, prehistoric anomalies.\n"
        "  9. Indigenous Philosophy & Stoic Mindset: Ancient mindset protocols (Dokkodo, Stoicism) applied to modern institutional burnout and social fatigue.\n"
        "  10. Declassified Military Logistics & Geopolitical Chokepoints: Supply line collapses, strategic maritime straits, undersea infrastructure vulnerabilities.\n"
        "  11. Everyday Consumer Injustice & Institutional Traps: Asymmetric retail traps, unwritten receipt clauses, hidden fees, toothless regulatory guidance, and minor contract exploitation.\n\n"
        "STRICT REJECTION MANDATE (ZERO-SPECULATION & ANTI-DEFAMATION & ANTI-TUTORIAL):\n"
        "- REJECT immediately if the keyword is celebrity gossip, sports game scores/contract negotiations, entertainment awards, or unverified off-field personal/civil conduct allegations without official documented disciplinary action or court ruling.\n"
        "- REJECT if approving it would require AI speculation, inventing stakes, or defaming real individuals.\n"
        "- REJECT if the proposed angle is a dry customer service FAQ, tutorial, or how-to guide ('How to', 'Mẹo', '5 bước', '환불하는법'). The angle MUST formulate a high-stakes dramatic clash: [Everyday Item/Transaction + Shock Figure] vs [Unilateral Fine Print / Institutional Trap].\n\n"
        "SEARCH INTENT FORENSICS & ALGORITHMIC SURGE ANCHOR (RULE 118):\n"
        "- The 'specific_viral_angle' MUST directly explain the REAL REASON why people are searching, as evidenced by the 'rising_queries'.\n"
        "- If rising queries indicate that a subject is trending for a new reason (e.g. a new documentary announcement or seasonal holiday), do NOT recycle an outdated historical angle from years ago.\n"
        "- FORBIDDEN: Hallucinating an unrelated niche angle not supported by real search signals.\n\n"
        "CRITICAL EVALUATION GATES:\n"
        "1. VISUAL FEASIBILITY (Layer 1 BG 16:9 + Layer 2 FG Transparent PNG)\n"
        "2. CAUSAL CONFLICT DEPTH (Systemic mechanism, regulatory loophole, executive hubris, or institutional betrayal)\n"
        "3. RULE 444 HOOK POTENTIAL (5-10s Quantitative Shock figure, dollar amount, or ticking clock)\n"
        "4. AUDIENCE RETENTION APPEAL (High cold-traffic curiosity)\n\n"
        "Output ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "is_video_viable": true|false,\n'
        '  "viability_score": <float 1.0 to 10.0>,\n'
        '  "verdict": "APPROVED"|"REJECTED",\n'
        '  "specific_viral_angle": "<Specific 10x concrete video title/angle explaining the real search surge reason>",\n'
        '  "visual_feasibility_score": <int 1 to 10>,\n'
        '  "conflict_depth_score": <int 1 to 10>,\n'
        '  "rejection_reason": "<string if rejected, else null>"\n'
        "}"
    )

    preset_hint = ""
    if theme == "ancient_prehistory_anthropology":
        preset_hint = "Assigned Strategic Preset: PRESET_ANCIENT_PREHISTORY_US (Archetype: anthropology_educational_explainer, Target RPM: $15-$35).\n"
    elif theme == "indigenous_philosophy_stoicism":
        preset_hint = "Assigned Strategic Preset: PRESET_STOIC_ZEN_JP_KR (Archetype: philosophical_contemplative_docudrama, Target RPM: $5-$12).\n"
    elif theme == "military_logistics_geopolitics":
        preset_hint = "Assigned Strategic Preset: PRESET_MILITARY_GEOPOLITICS_US (Archetype: forensic_military_investigation, Target RPM: $20-$40).\n"
    elif theme == "consumer_injustice_institutional_trap":
        preset_hint = "Assigned Strategic Preset: PRESET_CONSUMER_DOCUDRAMA (Archetype: social_reality_docudrama, Target RPM: $12-$25).\n"

    user_prompt = (
        f"Candidate Keyword: {keyword}\n"
        f"Target Market: {m_up}\n"
        f"Detected Content Theme: {theme}\n"
        f"Platform Safety Label: {safety_label}\n"
        f"{preset_hint}"
        f"{signals_str}\n"
        "Evaluate this keyword now. If approved, formulate a razor-sharp 'specific_viral_angle' (e.g. from 'Enron' -> 'How Enron Staged Fake Trading Floors to Scam $30B')."
    )

    try:
        raw_res = call_gpt6_astra(user_prompt, system_prompt=system_prompt, max_tokens=1000, timeout=75.0)
        clean_json = raw_res.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
            clean_json = re.sub(r"\s*```$", "", clean_json)
        data = json.loads(clean_json)
        return data
    except Exception as e:
        logger.error(f"[hhtech] assess_keyword_video_viability failed: {type(e).__name__}: {e}")
        return {
            "is_video_viable": False,
            "viability_score": 0.0,
            "verdict": "REJECTED_API_ERROR",
            "specific_viral_angle": keyword,
            "visual_feasibility_score": 0,
            "conflict_depth_score": 0,
            "rejection_reason": f"LLM assessment error: {type(e).__name__} ({e})",
            "api_error": True,
            "error_details": str(e)
        }


class HHTechReasoner:
    """Class wrapper around HHTech reasoning functions for test parity & OO callers."""
    def __init__(self):
        self.model = HHTECH_MODEL
        self.base_url = HHTECH_BASE_URL

    def _get_system_rules(self) -> str:
        return get_b1_strategic_rules()

    def assess_viability(self, *args, **kwargs):
        return assess_keyword_video_viability(*args, **kwargs)

    def reason_niche(self, *args, **kwargs):
        return reason_topic_niche(*args, **kwargs)

