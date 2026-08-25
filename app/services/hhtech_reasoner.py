# app/services/hhtech_reasoner.py
"""
HHTech Reasoning Service via GPT-5.6-Sol (Sole Gateway Model).
Standardized Architecture (24/08/2026 - Go-Live 2026):
  - English-First System Prompt for maximum reasoning depth & zero stereotyping.
  - Native Evidence Grounding (Wikipedia Japanese / Korean / English summaries).
  - Google Trends Rising / Breakout Queries Injection for Act 1 Hook Shock.
  - YouTube Safety Labeling & 4-Tier Content Categorization (Decisions 19/08 - 24/08).
  - Vietnamese Output for Human Gate 1 (topic_name_vi, niche_angle_brief, story_direction_5_arcs).
"""

import os, json, logging, re, urllib.request, urllib.parse
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
    """Synchronous caller for GPT-5.6-Sol via HHTech API."""
    import httpx
    key = get_hhtech_key()
    if not key:
        raise ValueError("HHTECH_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": HHTECH_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True
    }

    full_content = []
    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", f"{HHTECH_BASE_URL}/chat/completions", json=payload, headers=headers) as response:
            if response.status_code != 200:
                error_body = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HHTech API returned HTTP {response.status_code}: {error_body}")
            for line in response.iter_lines():
                line = line.strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            full_content.append(delta)
                    except Exception:
                        pass
                    
    return "".join(full_content).strip()

def reason_topic_niche(
    subject: str,
    market: str,
    virality_score: float = 0.85,
    rising_queries: list | None = None,
    top_queries: list | None = None
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

    # 3. Universal English-First Strategic System Prompt (Objective & Free of Stereotypes)
    system_prompt = (
        "You are the Lead Creative Director and Strategic Research Analyst for Video Factory (VF Pipeline).\n"
        "Your mission is to perform an objective, deep-dive causal analysis of the trending topic using the provided factual evidence (Native Ground Truth) and breakout search signals.\n\n"
        "CORE EDITORIAL PRINCIPLES (Rule 1, 2, 3, 4, 78: Big Fish Small Pond):\n"
        "1. OBJECTIVE & UNBIASED ANALYSIS: Do NOT force generic cliches or artificial stereotypes. Let the verified historical, financial, legal, or institutional facts dictate the causal mechanism.\n"
        "2. CAUSAL MECHANISMS OVER GENERALITIES: Uncover the real underlying drivers (e.g., regulatory loopholes, structural incentives, accounting practices, market power, or social dynamics) directly from the evidence.\n"
        "3. ACT 1 HOOK SHOCK: If Google Trends Breakout Queries or critical verified facts exist, use them as the primary catalyst/shock hook in the first 60 words of Act 1.\n"
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
        f"{top_text}\n"
        "STRATEGIC INSTRUCTIONS:\n"
        "1. 'search_specific_keyword': Must be in the TARGET MARKET NATIVE LANGUAGE (Japanese for JP, Korean for KR, English for EN), combining core event names, key figures, and breakout search terms.\n"
        "2. 'breakout_queries': Top 3-5 breakout/rising query strings in the native market language.\n"
        "3. 'task_slug': Concise lowercase-hyphenated English slug (max 25 characters, e.g. livedoor-scandal).\n"
        "4. 'topic_name_vi': Sharp, high-retention Vietnamese title for the episode.\n"
        "5. 'niche_angle_brief': 1 concise sentence in Vietnamese explaining the core Big Fish Small Pond mechanism.\n"
        "6. 'story_direction_5_arcs': Structured 5-Act outline in Vietnamese: Hồi 1 (Hook: Breakout query/shock fact in first 60 words) -> Hồi 2 (Origins & Structural Setup) -> Hồi 3 (Core Conflict & Exploitation) -> Hồi 4 (Turning Point & Collapse/Backlash) -> Hồi 5 (Legacy & Modern Lesson).\n\n"
        "Return EXACT JSON matching this schema:\n"
        "{\n"
        '  "topic_name_vi": "<Tên đề tài tiếng Việt sắc bén>",\n'
        '  "search_specific_keyword": "<Từ khóa tìm kiếm chuyên sâu bằng TIẾNG BẢN XỨ (JP/KR/EN)>",\n'
        '  "task_slug": "<english-lowercase-slug>",\n'
        '  "niche_angle_brief": "<1 câu đúc kết góc nhìn ngách Big Fish Small Pond bằng tiếng Việt>",\n'
        '  "story_direction_5_arcs": "Hồi 1 (Hook): ... -> Hồi 2: ... -> Hồi 3: ... -> Hồi 4: ... -> Hồi 5: ...",\n'
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
        "story_direction_5_arcs": "Hồi 1 (Hook): Đón đầu đột biến -> Hồi 2 (Trỗi dậy) -> Hồi 3 (Xung đột/Thao túng) -> Hồi 4 (Sụp đổ/Khủng hoảng) -> Hồi 5 (Bài học & Di sản)",
        "breakout_queries": clean_bqs,
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note
    }
