"""
Grounding Layer Service (B1.5.5) for AI Video Factory (VF Pipeline)
Rule 118: Zero-Mock Data. Fetches real-world factual claims using Google Search Grounding.
Rule 128: Zero Semantic Bias. Generic domain-agnostic fact extraction and confidence tagging.
Rule 125: Single Truth. Clean integration between B1.5 Competitor Recon and B2 Story Engine.
"""

import os
import sys
import json
import re
import logging
import urllib.request
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Reputable journalism, official governmental, maritime, and economic intelligence domains
TRUSTED_DOMAINS = [
    # Wire services & global financial press
    "reuters.com", "apnews.com", "bloomberg.com", "afp.com", "bbc.com", "bbc.co.uk", "cnbc.com", "nytimes.com",
    "theguardian.com", "marketwatch.com", "forbes.com", "wsj.com", "ft.com", "economist.com",
    # Think tanks, security & foreign affairs authorities
    "foreignaffairs.com", "cfr.org", "csis.org", "chathamhouse.org", "carnegieendowment.org",
    "defensenews.com", "janes.com", "understandingwar.org", "sipri.org", "crisisgroup.org",
    # Financial, regulatory & central banking authorities
    "bis.org", "imf.org", "worldbank.org", "federalreserve.gov", "sec.gov", "cftc.gov", "boj.or.jp", "bok.or.kr",
    "bankofengland.co.uk", "ecb.europa.eu",
    # Japanese authoritative news, broadcast networks & economic publications
    "nikkei.com", "nhk.or.jp", "asahi.com", "yomiuri.co.jp", "mainichi.jp", "kyodonews.net", "jiji.com",
    "japantimes.co.jp", "toyokeizai.net", "diamond.jp", "sankei.com", "ktv.jp", "fnn.jp", "news.yahoo.co.jp",
    "yahoo.co.jp", "tbs.co.jp", "ntv.co.jp", "tv-asahi.co.jp", "tv-tokyo.co.jp", "kobe-np.co.jp", "chunichi.co.jp",
    "livedoor.com", "livedoor.jp", "excite.co.jp", "tnc.co.jp", "wikipedia.org",
    # Korean authoritative news, broadcast networks & economic publications
    "yna.co.kr", "mk.co.kr", "hankyung.com", "chosun.com", "donga.com", "joongang.co.kr",
    "koreatimes.co.kr", "koreaherald.com", "sedaily.com", "kbs.co.kr", "imbc.com", "sbs.co.kr", "ytn.co.kr",
    "jtbc.co.kr", "naver.com", "daum.net",
    # Maritime, commodities, energy & trade authorities
    "lloydslist.com", "gcaptain.com", "maritime-executive.com", "tradewindsnews.com",
    "eia.gov", "imo.org", "marad.dot.gov", "spglobal.com", "freightwaves.com",
    "windward.ai", "kpler.com", "vortexa.com", "iea.org", "opec.org", "argusmedia.com", "woodmac.com", "rystadenergy.com",
    # Tech & semiconductor intelligence
    "trendforce.com", "digitimes.com", "counterpointresearch.com", "idc.com", "gartner.com", "semiconductors.org",
    # Official / Institutional TLDs (Global, US, JP, KR, UK, etc.)
    ".gov", ".mil", ".int", ".org", ".go.jp", ".go.kr", ".gov.uk", ".gov.au"
]


def get_gemini_api_key() -> str:
    """Retrieve GEMINI_API_KEY from environment or standard secret paths."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    secret_candidates = [
        "/root/video_factory/.env",
        "/root/secrets/.env",
        os.path.expanduser("~/.env"),
        "./.env"
    ]
    for p in secret_candidates:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                os.environ["GEMINI_API_KEY"] = val
                                return val
            except Exception:
                pass
    return ""


from urllib.parse import urlparse

def is_trusted_domain(source: str, url: str = "") -> bool:
    """Check if the source name or URL contains any of the trusted domains with proper domain boundaries."""
    source_lower = source.lower()
    
    # Authoritative name keywords across geopolitics, economics, maritime, technology, and ministries
    name_keywords = [
        # Wire & global financial press
        "reuters", "associated press", "ap news", "bloomberg", "financial times", "wall street journal",
        "wsj", "economist", "bbc", "cnbc", "new york times", "nytimes", "guardian", "forbes",
        # Think tanks & foreign affairs
        "csis", "chatham house", "carnegie", "sipri", "crisis group", "defense news", "janes",
        "understanding war", "foreign affairs", "foreign policy",
        # Central banks & international bodies
        "imf", "world bank", "federal reserve", "sec", "cftc", "bis", "ecb", "bank of england",
        "bank of japan", "bank of korea",
        # Japanese press, broadcast networks & regional authorities
        "nikkei", "nhk", "asahi", "yomiuri", "mainichi", "kyodo", "jiji", "japan times", "toyokeizai",
        "カンテレ", "ktv", "fnn", "ライブドア", "livedoor", "yahoo", "ヤフー", "sankei", "産経", "wikipedia", "ウィキペディア",
        "tbs", "ntv", "日テレ", "テレ朝", "テレビ東京", "tv tokyo", "神戸新聞", "kobe", "chunichi", "中日新聞", "西日本新聞",
        "excite", "エキサイト", "tnc",
        # Korean press, broadcast networks & portal news
        "yonhap", "yna", "maeil", "korea economic daily", "hankyung", "chosun", "donga", "joongang",
        "korea times", "korea herald", "sedaily", "kbs", "mbc", "sbs", "ytn", "jtbc", "naver", "daum",
        # Maritime & energy & commodities
        "lloyd's list", "lloyds list", "gcaptain", "maritime executive", "tradewinds",
        "eia", "imo", "marad", "s&p global", "sp global", "freightwaves", "windward", "kpler",
        "vortexa", "iea", "opec", "argus", "wood mackenzie", "rystad",
        # Tech & industry research
        "trendforce", "digitimes", "counterpoint", "gartner", "idc", "semiconductor industry",
        # Ministries & governmental agencies
        "ministry of transport", "department of transportation", "department of defense",
        "department of state", "department of energy", "treasury", "pentagon", "white house",
        "coast guard", "maritime administration", "customs", "kantei", "meti", "mof"
    ]
    if any(k in source_lower for k in name_keywords):
        return True

    # Split composite source names into sub-tokens to check each candidate name
    sub_tokens = [tok.strip() for tok in re.split(r"[,;/|\-\(\)]+", source_lower) if tok.strip()]
    for tok in sub_tokens:
        if any(k in tok for k in name_keywords):
            return True

    # Check hostname from URL
    host = ""
    if url:
        try:
            parsed_url = urlparse(url if "://" in url else f"http://{url}")
            host = (parsed_url.hostname or "").lower()
        except Exception:
            host = url.lower()

    if not host and not source_lower:
        return False

    for td in TRUSTED_DOMAINS:
        td_low = td.lower()
        if td_low.startswith("."):
            # TLD check: e.g. .gov, .mil, .int, .org, .go.jp, .go.kr
            if host.endswith(td_low):
                return True
        else:
            # Domain check: e.g. reuters.com -> matches reuters.com and *.reuters.com
            if host == td_low or host.endswith("." + td_low) or td_low in source_lower:
                return True

    return False


def classify_causal_role(claim: Dict[str, Any]) -> str:
    """
    Classifies or extracts the causal role of a factual claim under Rule 130.
    Generic across all 5 topic axes:
      - 'primary_catalyst': Level 1 direct event/trigger (e.g. strike, arrest, indictment, crash, breach, ban).
      - 'transmission_mechanism': Level 2 institutional/systemic response (e.g. insurance surge, margin call, traffic drop, liquidity freeze).
      - 'background_context': Structural baseline, historical baseline, pre-existing statutes or geography.
    """
    role = str(claim.get("causal_role", "")).strip().lower()
    if role in ("primary_catalyst", "transmission_mechanism", "background_context"):
        return role

    # Semantic keyword classification fallback for unannotated or legacy claims
    txt = (str(claim.get("claim", "")) + " " + str(claim.get("mechanism", ""))).lower()
    catalyst_signals = [
        "strike", "struck", "attack", "explod", "invad", "declar", "arrest", "indict",
        "breach", "raid", "order", "clos", "shut", "fired", "killed", "leak", "hack",
        "seiz", "subpoena", "default", "scandal", "fraud", "bribe", "whistleblower"
    ]
    transmission_signals = [
        "premium", "insurance", "advisory", "rate", "transit", "decreas", "plung",
        "drop", "fell", "margin call", "liquidity", "sanction", "ban", "freeze", "divert",
        "rerout", "spread", "yield", "curb", "halt", "loss", "surcharge", "downgrade"
    ]
    if any(s in txt for s in catalyst_signals) and not any(s in txt for s in ["insurance", "premium", "margin call"]):
        return "primary_catalyst"
    if any(s in txt for s in transmission_signals):
        return "transmission_mechanism"
    return "background_context"


def run_grounding_research(
    topic: str,
    search_hint: str = "",
    market: str = "EN",
    timeout: float = 35.0
) -> Dict[str, Any]:
    """
    Executes live Google Search Grounding via Gemini 2.5 Flash REST API.
    Extracts structured factual claims, dates, sources, confidence levels, mechanisms, and causal roles (Rule 130).
    """
    api_key = get_gemini_api_key()
    if not api_key:
        logger.warning("[grounding] No GEMINI_API_KEY configured. Returning fallback ungrounded container.")
        return {
            "topic": topic,
            "rejected": False,
            "reject_reason": "No GEMINI_API_KEY configured",
            "claims": [],
            "grounding_chunks": [],
            "search_queries": [],
            "has_live_search": False
        }

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    sys_instruction = (
        "You are an Elite Forensic Research Fact-Finder for an investigative documentary channel.\n"
        "Your mission is to extract 3 to 6 concrete, verifiable factual claims from real-world news and official records.\n\n"
        "MANDATORY FACT-CHECKING & CAUSAL RULES (RULE 118 & RULE 130):\n"
        "1. Extract ONLY facts that actually occurred or are currently reported. NEVER invent statistics, dollar amounts, casualties, or quotes.\n"
        "2. Categorize confidence strictly into:\n"
        "   - 'verified': Corroborated by major official agencies, regulatory filings, or multiple reputable international news outlets.\n"
        "   - 'reported': Stated by a single reputable news organization or industry analyst.\n"
        "   - 'speculative': Predictions, scenario forecasts, or unverified claims made by commentators.\n"
        "3. Categorize causal_role strictly into:\n"
        "   - 'primary_catalyst': Level 1 direct event/trigger that physically, legally, or financially initiated the crisis (e.g., military strike, indictment, executive arrest, contract breach, earnings shock, system crash).\n"
        "   - 'transmission_mechanism': Level 2 institutional/systemic response or choke point that transmitted or amplified the impact (e.g., insurance risk surcharge, liquidity freeze, margin call, export ban, supply chain default, traffic plunge).\n"
        "   - 'background_context': Baseline structural data, historical baseline numbers, geographic or legal statutes existing prior to the catalyst.\n"
        "   MANDATORY RULE 130: Distinguish Level 1 from Level 2. NEVER invert causality or present a transmission mechanism as the original primary trigger.\n"
        "4. Identify the mechanism of each claim (e.g. 'financial', 'legal', 'military', 'commercial', 'technical', 'regulatory').\n"
        "5. Include exact publication dates (YYYY-MM-DD) and outlet/source names.\n"
        "6. If there is insufficient credible evidence or the topic is pure rumor/satire, set 'rejected': true with a clear 'reject_reason'.\n"
        "7. ADAPTIVE TEMPORAL PROGRESSION & CHRONO-EPOCHS (SCALE-UP ARCHITECTURE):\n"
        "   - Identify the natural temporal cadence of the topic: 'MACRO_SAGA' (multi-year/decadal, corporate rise/fall, major lawsuit), 'MID_TACTICAL' (months to 1-2 years, policy/product battle), or 'FLASH_CRISIS' (days to weeks, bank-run, flash crash, sudden breach).\n"
        "   - Extract 2 to 4 pivotal 'causal_epochs' representing the timeline progression:\n"
        "     * 'genesis_seed': The foundational origin (initial contract, loan, founding premise, baseline deal, or pre-crisis baseline).\n"
        "     * 'incubation_mutation': The hidden distortion or systemic rot (unheeded warnings, hidden leverage, initial disputes, or brewing crisis).\n"
        "     * 'critical_rupture': The fatal breaking point (criminal conviction, regulatory seizure, whistleblower leak, or default).\n"
        "     * 'contemporary_aftermath': The current state (unresolved asset recovery, final award, enforcement, or precedent).\n\n"
        "Output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"topic\": \"...\",\n"
        "  \"temporal_cadence\": \"MACRO_SAGA|MID_TACTICAL|FLASH_CRISIS\",\n"
        "  \"rejected\": false,\n"
        "  \"reject_reason\": \"\",\n"
        "  \"causal_epochs\": [\n"
        "    {\n"
        "      \"epoch_stage\": \"genesis_seed|incubation_mutation|critical_rupture|contemporary_aftermath\",\n"
        "      \"time_marker\": \"Year, date, or relative time (e.g. 2007, 6 months earlier, Hour 0)\",\n"
        "      \"event_summary\": \"What physically, legally, or financially occurred\",\n"
        "      \"verified_claim\": \"Anchor factual statement with concrete metric/actor\"\n"
        "    }\n"
        "  ],\n"
        "  \"claims\": [\n"
        "    {\n"
        "      \"claim\": \"Concise, specific factual claim with concrete metric/action\",\n"
        "      \"source\": \"Name of reporting outlet or agency (e.g. Reuters, Bloomberg, SEC, Nikkei, EIA)\",\n"
        "      \"source_url\": \"Optional URL or domain if available\",\n"
        "      \"date\": \"YYYY-MM-DD\",\n"
        "      \"confidence\": \"verified|reported|speculative\",\n"
        "      \"causal_role\": \"primary_catalyst|transmission_mechanism|background_context\",\n"
        "      \"mechanism\": \"legal|military|commercial|financial|technical|regulatory\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    query_text = (
        f"Topic: '{topic}'.\n"
        f"1. Contemporary Horizon: Identify the immediate breaking event, latest verdict, recent metric, and primary catalyst.\n"
        f"2. Chronological Backtrace: Investigate the chronological pre-history: when did this entity, conflict, contract, deal, or vulnerability begin? "
        f"Identify the origin point, any prior criminal/civil disputes, ignored audits, or pre-crisis baseline.\n"
    )
    if search_hint:
        query_text += f" Search focus: '{search_hint}'."
    if market.upper() == "JP":
        query_text += " Search authoritative Japanese and international news and official records."
    elif market.upper() == "KR":
        query_text += " Search authoritative Korean and international news and official records."
    else:
        query_text += " Search live web news and official records, then return the JSON factual extraction."

    payload = {
        "systemInstruction": {
            "parts": [{"text": sys_instruction}]
        },
        "contents": [{
            "parts": [{
                "text": query_text
            }]
        }],
        "tools": [{
            "googleSearch": {}
        }]
    }

    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    try:
        logger.info(f"[grounding] Executing Google Search Grounding for topic: '{topic[:60]}'")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_data = json.loads(resp.read().decode("utf-8"))

        candidate = raw_data.get("candidates", [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        text_resp = "".join([p.get("text", "") for p in parts]).strip()

        # Extract grounding metadata (queries and source chunks)
        grounding_meta = candidate.get("groundingMetadata", {})
        web_queries = grounding_meta.get("webSearchQueries", [])
        raw_chunks = grounding_meta.get("groundingChunks", [])
        grounding_chunks = []
        for c in raw_chunks:
            web = c.get("web", {})
            if web:
                grounding_chunks.append({
                    "title": web.get("title", ""),
                    "uri": web.get("uri", "")
                })

        # Clean markdown fence if LLM wrapped with ```json
        clean_json = re.sub(r"^```json\s*|\s*```$", "", text_resp, flags=re.MULTILINE).strip()
        parsed = json.loads(clean_json)

        parsed["grounding_chunks"] = grounding_chunks
        parsed["search_queries"] = web_queries
        parsed["has_live_search"] = True
        logger.info(f"[grounding] Successfully extracted {len(parsed.get('claims', []))} claims with {len(grounding_chunks)} search sources.")
        return parsed

    except json.JSONDecodeError as je:
        logger.warning(f"[grounding] Failed to parse JSON from grounding response: {je}")
        return {
            "topic": topic,
            "rejected": True,
            "reject_reason": f"JSON parse error from grounding model: {je}",
            "claims": [],
            "grounding_chunks": [],
            "search_queries": [],
            "has_live_search": False
        }
    except Exception as e:
        logger.error(f"[grounding] Grounding API call failed: {e}")
        return {
            "topic": topic,
            "rejected": True,
            "reject_reason": f"API call error: {e}",
            "claims": [],
            "grounding_chunks": [],
            "search_queries": [],
            "has_live_search": False
        }


def passes_grounding_gate(
    grounding_result: Dict[str, Any],
    min_verified: int = 2,
    require_whitelist: bool = True,
    max_speculative_ratio: float = 0.40,
    min_claims: int = 3,
    min_dated_claims: int = 2,
    require_causal_link: bool = True
) -> Tuple[bool, str]:
    """
    Code-Enforced Gate (Rule 121, Rule 127 & Rule 130).
    Evaluates whether the research result meets factual and causal criteria BEFORE moving to scriptwriting.
    Strict Multi-Layer Quality & Causal Audit Gate:
      1. Not explicitly rejected by model
      2. Minimum total claims (default >= 3)
      3. Minimum verified claims (default >= 2)
      4. Whitelist enforcement: At least 1 verified claim MUST come from an authoritative whitelisted source
      5. Maximum speculative ratio (default <= 40%)
      6. Temporal anchoring: At least 2 claims must have valid date format
      7. Causal Link Verification (Rule 130):
         - At least 1 verified/reported claim must serve as Level 1 Primary Catalyst.
         - At least 1 verified/reported claim must serve as Level 2 Transmission Mechanism.
    """
    if not grounding_result:
        return False, "Empty grounding result."

    if grounding_result.get("rejected", False):
        reason = grounding_result.get("reject_reason") or "Model flagged topic as ungrounded or speculative."
        return False, f"Topic rejected by grounding: {reason}"

    claims = grounding_result.get("claims", [])
    if not claims:
        # Rule 118: Zero-Mock Data. Zero verified claims CANNOT pass the grounding gate.
        reason = grounding_result.get("reject_reason") or "No factual claims could be extracted (API timeout or ungrounded)."
        return False, f"Grounding Gate Blocked: {reason}"

    if len(claims) < min_claims:
        return False, f"Insufficient total claims ({len(claims)} found, required >= {min_claims})."

    verified_claims = [c for c in claims if str(c.get("confidence", "")).lower() == "verified"]
    if len(verified_claims) < min_verified:
        return False, f"Insufficient verified claims ({len(verified_claims)} found, required >= {min_verified})."

    if require_whitelist:
        has_whitelisted_verified = False
        for c in verified_claims:
            if is_trusted_domain(c.get("source", ""), c.get("source_url", "")):
                has_whitelisted_verified = True
                break
        if not has_whitelisted_verified:
            has_whitelisted_any = any(is_trusted_domain(c.get("source", ""), c.get("source_url", "")) for c in claims)
            if not has_whitelisted_any:
                return False, "None of the extracted claims originate from whitelisted authoritative domains."
            return False, "None of the verified claims originate from whitelisted authoritative domains."

    speculative_claims = [c for c in claims if str(c.get("confidence", "")).lower() == "speculative"]
    spec_ratio = len(speculative_claims) / len(claims)
    if spec_ratio > max_speculative_ratio:
        return False, f"Speculative claims ratio too high ({spec_ratio:.1%} > {max_speculative_ratio:.0%})."

    dated_claims = [c for c in claims if re.search(r"\b(19\d\d|20\d\d)(?:-\d{2}-\d{2})?\b", str(c.get("date", "")))]
    if len(dated_claims) < min_dated_claims:
        return False, f"Insufficient temporally anchored claims with valid dates ({len(dated_claims)} found, required >= {min_dated_claims})."

    if require_causal_link:
        catalysts = [
            c for c in claims
            if classify_causal_role(c) == "primary_catalyst"
            and str(c.get("confidence", "")).lower() in ("verified", "reported")
        ]
        if not catalysts:
            return False, "Causal Link Failure (Rule 130): Missing verified or reported primary catalyst claim."

        transmissions = [
            c for c in claims
            if classify_causal_role(c) == "transmission_mechanism"
            and str(c.get("confidence", "")).lower() in ("verified", "reported")
        ]
        if not transmissions:
            return False, "Causal Link Failure (Rule 130): Missing verified or reported transmission mechanism claim."

    return True, f"PASSED ({len(claims)} claims: {len(verified_claims)} verified, {len(dated_claims)} dated, spec_ratio {spec_ratio:.0%}, causal_link: VALID)"


def format_grounded_facts_for_prompt(grounding_result: Dict[str, Any]) -> str:
    """Formats verified claims into a clean Markdown table for injection into B2 Story Engine prompt
    with strict Rule 130 Causal Hierarchy and Search-Intent directives."""
    claims = grounding_result.get("claims", [])
    if not claims:
        return ""

    lines = [
        "### REAL-WORLD GROUNDED FACTS TABLE (MANDATORY TRUTH ANCHOR)",
        "The following factual claims have been independently verified via live web research.",
        "MANDATORY SCRIPTWRITING CONSTRAINTS (RULE 118, RULE 130 & RULE 445):",
        "1. VERIFIED claims: You may assert directly as established facts.",
        "2. REPORTED claims: You MUST use attributive sourcing ('According to reports from [Source]...', 'Records from [Source] indicate...').",
        "3. SPECULATIVE claims: You MUST use cautious conditional framing ('If subsequent assessments hold...', 'Under projected scenarios...').",
        "4. CAUSAL HIERARCHY & INTEGRITY (RULE 130):",
        "   - [PRIMARY_CATALYST] (Level 1): The direct physical, military, legal, or commercial spark. Act I Hook MUST feature this catalyst to pay off the viewer's search query immediately.",
        "   - [TRANSMISSION_MECHANISM] (Level 2): The systemic channel (insurance, liquidity, margin call, regulatory notice, supply bottleneck). Acts III & IV must dissect this mechanism.",
        "   - ZERO INVERTED CAUSALITY: Strictly forbidden to present a transmission mechanism as the original primary trigger.",
        "5. SEARCH-INTENT DIRECT PAYOFF: Do NOT clickbait or drift away into academic abstractions. Address the central headline question within the opening 60 seconds.",
        "6. ZERO-HALLUCINATION: Do NOT invent dates, numerical fees, casualties, or institutional actors outside this table.",
        "7. CONTEMPORARY EVENT ANCHOR & TREND-INTENT PRIORITY (MANDATORY IN ACT I):",
        "   - When an episode is based on an active trend, breaking investigation, or contemporary crisis: Act I (specifically paragraph 1 or 2) MUST explicitly name the specific real-world Contemporary Catalyst Event (exact dates, acting entities/governments, and verified quantitative drops/metrics from this table).",
        "   - STRICTLY FORBIDDEN: Hiding behind vague, abstract, or generic phrasing (such as 'When an emergency occurs' or 'When systemic volatility happens') when verified contemporary event details are present in the table!",
        "   - HISTORICAL PRECEDENT DISCIPLINE: Historical comparisons from past eras may ONLY be used in later Acts (Act II/III) as comparative blueprints to explain the legal, institutional, or financial mechanism, NEVER to replace or displace the contemporary catalyst that viewers are actively searching for.\n"
    ]

    for idx, c in enumerate(claims, 1):
        conf = str(c.get("confidence", "reported")).upper()
        date = c.get("date", "Undated")
        src = c.get("source", "Industry Record")
        mech = c.get("mechanism", "General")
        role = classify_causal_role(c).upper()
        claim_txt = c.get("claim", "")
        lines.append(f"{idx}. [{conf}] [{role}] ({date}) [{src} | Mechanism: {mech}]: {claim_txt}")

    epochs = grounding_result.get("causal_epochs", [])
    cadence = grounding_result.get("temporal_cadence", "ADAPTIVE")
    if epochs:
        lines.append("")
        lines.append(f"### CHRONO-CAUSAL EPOCHS TABLE (TEMPORAL CADENCE: {cadence})")
        lines.append("Use these chronological waypoints to drive narrative progression across the 5 Acts (avoid single-timestamp repetition):")
        for ep in epochs:
            stg = str(ep.get("epoch_stage", "stage")).upper()
            tm = ep.get("time_marker", "Historical Anchor")
            ev = ep.get("event_summary", "")
            cl = ep.get("verified_claim", "")
            anchor_note = f" — Verified Anchor: {cl}" if cl else ""
            lines.append(f"- [{stg}] ({tm}): {ev}{anchor_note}")

    return "\n".join(lines)
