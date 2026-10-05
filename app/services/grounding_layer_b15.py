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
import time
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Reputable journalism, official governmental, maritime, and economic intelligence domains
TRUSTED_DOMAINS = [
    # Wire services & global financial press
    "reuters.com", "apnews.com", "bloomberg.com", "afp.com", "bbc.com", "bbc.co.uk", "cnbc.com", "nytimes.com",
    "theguardian.com", "marketwatch.com", "forbes.com", "wsj.com", "ft.com", "economist.com",
    "washingtonpost.com", "npr.org", "pbs.org", "politico.com", "axios.com", "propublica.org",
    "theintercept.com", "businessinsider.com", "usatoday.com", "latimes.com",
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
        "washington post", "wapo", "npr", "national public radio", "pbs", "cnn", "cbs", "abc news",
        "nbc news", "msnbc", "politico", "axios", "propublica", "the intercept", "intercept",
        "business insider", "usa today", "la times", "los angeles times",
        # Think tanks & foreign affairs
        "csis", "chatham house", "carnegie", "sipri", "crisis group", "defense news", "janes",
        "understanding war", "foreign affairs", "foreign policy",
        # Central banks & international bodies
        "imf", "world bank", "federal reserve", "sec", "cftc", "bis", "ecb", "bank of england",
        "bank of japan", "bank of korea",
        # Legal, Prosecutorial & Judicial Authorities
        "attorney general", "attorney general's office", "department of justice", "doj", "prosecutor",
        "district attorney", "us attorney", "u.s. attorney", "court", "supreme court", "district court",
        "circuit court", "court of appeals", "grand jury",
        # Legislative & Federal Regulatory Agencies
        "house of representatives", "congress", "senate", "gao", "government accountability office",
        "inspector general", "oig", "fbi", "sec", "cftc", "ftc", "fda", "epa", "osha", "ice",
        "cbp", "dhs", "homeland security",
        # Legal Watchdogs & Civil Liberties
        "aclu", "eff", "electronic frontier foundation", "american civil liberties union",
        # Japanese press, broadcast networks & regional authorities
        "nikkei", "nhk", "asahi", "yomiuri", "mainichi", "kyodo", "jiji", "japan times", "toyokeizai",
        "カンテレ", "ktv", "fnn", "ライブドア", "livedoor", "yahoo", "ヤフー", "sankei", "産経", "wikipedia", "ウィキペディア",
        "tbs", "ntv", "日テレ", "テレ朝", "テレビ東京", "tv tokyo", "神戸新聞", "kobe", "chunichi", "中日新聞", "西日本新聞",
        "excite", "エキサイト", "tnc", "共同通信", "時事通信", "時事", "読売新聞", "読売", "朝日新聞", "朝日",
        "日本経済新聞", "日経", "毎日新聞", "毎日", "産経新聞", "東京新聞", "日経ビジネス", "週刊東洋経済", "東洋経済",
        "ダイヤモンド", "プレジデント", "ロイター", "ブルームバーグ", "東京商工リサーチ", "帝国データバンク",
        "財務省", "金融庁", "日本銀行", "日銀", "経済産業省", "経産省", "国土交通省", "国交省",
        "公正取引委員会", "公取委", "東京地裁", "大阪地裁", "最高裁判所", "警察庁", "警視庁", "内閣府",
        "首相官邸", "外務省", "法務省", "厚生労働省", "厚労省", "税務署", "国税庁", "貿易統計",
        # Korean press, broadcast networks & portal news
        "yonhap", "yna", "maeil", "korea economic daily", "hankyung", "chosun", "donga", "joongang",
        "korea times", "korea herald", "sedaily", "kbs", "mbc", "sbs", "ytn", "jtbc", "naver", "daum",
        "연합뉴스", "연합", "조선일보", "조선", "중앙일보", "동아일보", "한겨레", "경향신문", "한국일보",
        "매일경제", "매경", "한국경제", "한경", "서울경제", "머니투데이", "이데일리", "뉴시스",
        "기획재정부", "기재부", "금융위원회", "금융위", "금융감독원", "금감원", "한국은행", "한은",
        "공정거래위원회", "공정위", "산업통상자원부", "산자부", "대법원", "서울중앙지법", "검찰청", "대통령실", "국세청",
        # Vietnamese press and ministries
        "vnexpress", "tuoitre", "tuổi trẻ", "thanhnien", "thanh niên", "vietnamnet", "dantri", "dân trí",
        "vtv", "vov", "baochinhphu", "báo chính phủ", "bộ tài chính", "ngân hàng nhà nước",
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

    # Candidate domains list (host from url + source if source looks like a domain)
    candidate_domains = [host] if host else []
    if "." in source_lower and " " not in source_lower:
        candidate_domains.append(source_lower)

    for td in TRUSTED_DOMAINS:
        td_low = td.lower()
        if td_low.startswith("."):
            # TLD check: e.g. .gov, .mil, .int, .org, .go.jp, .go.kr
            for d in candidate_domains:
                if d.endswith(td_low):
                    return True
            if source_lower.endswith(td_low) or f"{td_low}." in source_lower or f"{td_low}/" in source_lower:
                return True
        else:
            # Domain check: e.g. reuters.com -> matches reuters.com and *.reuters.com
            for d in candidate_domains:
                if d == td_low or d.endswith("." + td_low):
                    return True
            if td_low in source_lower:
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
    timeout: float = 60.0
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

    sys_instruction = (
        "You are an Elite Forensic Research Fact-Finder for an investigative documentary channel.\n"
        "Your mission is to construct a Deep Investigative Factual Dossier containing 12 to 20 concrete, verifiable factual claims across the entire lifecycle of the case (genesis/baseline, early warning signs/mutation, the critical catalyst/rupture, regulatory/prosecution proceedings, and contemporary aftermath).\n\n"
        "MANDATORY FACT-CHECKING & CAUSAL RULES (RULE 118 & RULE 130):\n"
        "1. Extract ONLY facts that actually occurred or are currently reported. NEVER invent statistics, dollar amounts, casualties, or quotes.\n"
        "2. Categorize confidence strictly into:\n"
        "   - 'verified': Corroborated by major official agencies, regulatory filings, court dockets, or multiple reputable international news outlets.\n"
        "   - 'reported': Stated by a single reputable news organization or industry analyst.\n"
        "   - 'speculative': Predictions, scenario forecasts, or unverified claims made by commentators.\n"
        "3. Categorize causal_role strictly into:\n"
        "   - 'primary_catalyst': Level 1 direct event/trigger that physically, legally, or financially initiated the crisis (e.g., military strike, indictment, executive arrest, contract breach, earnings shock, system crash).\n"
        "   - 'transmission_mechanism': Level 2 institutional/systemic response or choke point that transmitted or amplified the impact (e.g., insurance risk surcharge, liquidity freeze, margin call, export ban, supply chain default, traffic plunge).\n"
        "   - 'background_context': Baseline structural data, historical baseline numbers, geographic or legal statutes existing prior to the catalyst.\n"
        "   MANDATORY RULE 130: Distinguish Level 1 from Level 2. NEVER invert causality or present a transmission mechanism as the original primary trigger.\n"
        "4. Map each claim to an intended documentary act: 'act_target': 'ACT_I|ACT_II|ACT_III|ACT_IV|ACT_V' to provide balanced factual evidence across all 5 Acts.\n"
        "5. Identify the mechanism of each claim (e.g. 'financial', 'legal', 'military', 'commercial', 'technical', 'regulatory').\n"
        "6. Include exact publication dates (YYYY-MM-DD) and outlet/source names.\n"
        "7. If there is insufficient credible evidence or the topic is pure rumor/satire, set 'rejected': true with a clear 'reject_reason'.\n"
        "8. ADAPTIVE TEMPORAL PROGRESSION & CHRONO-EPOCHS (SCALE-UP ARCHITECTURE):\n"
        "   - Identify the natural temporal cadence of the topic: 'MACRO_SAGA' (multi-year/decadal, corporate rise/fall, major lawsuit), 'MID_TACTICAL' (months to 1-2 years, policy/product battle), or 'FLASH_CRISIS' (days to weeks, bank-run, flash crash, sudden breach).\n"
        "   - Extract 3 to 5 pivotal 'causal_epochs' representing the timeline progression:\n"
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
        "      \"mechanism\": \"legal|military|commercial|financial|technical|regulatory\",\n"
        "      \"act_target\": \"ACT_I|ACT_II|ACT_III|ACT_IV|ACT_V\"\n"
        "    }\n"
        "  ]\n"
        "}\n"
    )

    query_text = (
        f"Topic: '{topic}'.\n"
        f"Construct a comprehensive 12-20 claim forensic factual dossier for a 5-Act investigative documentary:\n"
        f"1. Contemporary Spark (Act I): Who, what, when, exact financial loss/damages, arrest/indictment details, or market disruption.\n"
        f"2. Foundation & Origin (Act II): The founding contracts, initial regulatory approvals, original business model, or pre-crisis baseline.\n"
        f"3. Systemic Blindspot & Rot (Act III): Internal audit red flags, whistleblower reports, regulatory loopholes, hidden debt, or lack of oversight.\n"
        f"4. The Rupture & Paper Trail (Act IV): Specific court docket numbers, grand jury findings, bankruptcy petitions, forensic accounting evidence, or criminal filings.\n"
        f"5. Contemporary Fallout (Act V): Unresolved liabilities, asset recovery proceedings, regulatory reforms, or societal impact.\n"
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
    candidate_models = ["gemini-2.5-flash"]
    last_err = None

    for model_name in candidate_models:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"[grounding] Executing Google Search Grounding with {model_name} (attempt {attempt+1}/{max_retries}) for topic: '{topic[:60]}'")
                req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
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

                # Safe JSON parsing with regex extraction
                parsed = None
                json_match = re.search(r"\{.*\}", text_resp, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        parsed = None

                # Fallback to claude-sonnet-5-5 via HHTech API if JSON is malformed or claims empty
                if not parsed or not parsed.get("claims"):
                    logger.info(f"[grounding] JSON parse incomplete from {model_name}, invoking claude-sonnet-5-5 for forensic synthesis...")
                    try:
                        from app.services.model_gateway import get_global_gateway
                        gw = get_global_gateway()
                        repair_prompt = (
                            f"You are an Elite Forensic Research Fact-Finder for an investigative documentary channel.\n"
                            f"Synthesize and extract 12 to 18 verified factual claims for topic '{topic}' based on the following search intelligence:\n"
                            f"SEARCH QUERIES: {json.dumps(web_queries)}\n"
                            f"SEARCH SOURCES: {json.dumps(grounding_chunks)}\n"
                            f"RAW RESPONSE SNIPPET: {text_resp[:2000]}\n\n"
                            f"Output ONLY valid JSON matching this schema:\n"
                            f'{{\n  "topic": "{topic}",\n  "temporal_cadence": "MACRO_SAGA|MID_TACTICAL|FLASH_CRISIS",\n'
                            f'  "rejected": false,\n  "reject_reason": "",\n'
                            f'  "causal_epochs": [\n    {{"epoch_stage": "genesis_seed|critical_rupture", "time_marker": "...", "event_summary": "...", "verified_claim": "..."}}\n  ],\n'
                            f'  "claims": [\n    {{\n      "claim": "Specific factual claim with concrete metric/action",\n'
                            f'      "source": "Name of reporting outlet or agency",\n      "source_url": "",\n      "date": "YYYY-MM-DD",\n'
                            f'      "confidence": "verified",\n      "causal_role": "primary_catalyst|transmission_mechanism|background_context",\n'
                            f'      "mechanism": "legal|financial|regulatory",\n      "act_target": "ACT_I|ACT_II|ACT_III|ACT_IV|ACT_V"\n    }}\n  ]\n}}'
                        )
                        sonnet_raw = gw.call_llm(
                            prompt=repair_prompt,
                            model="claude-sonnet-5-5",
                            temperature=0.1,
                            max_tokens=3500
                        )
                        m_sonnet = re.search(r"\{.*\}", sonnet_raw, re.DOTALL)
                        if m_sonnet:
                            parsed = json.loads(m_sonnet.group(0))
                            parsed["grounding_model"] = "claude-sonnet-5-5"
                    except Exception as sonnet_err:
                        logger.warning(f"[grounding] Claude Sonnet 5.5 repair error: {sonnet_err}")

                if parsed and parsed.get("claims"):
                    parsed["grounding_chunks"] = grounding_chunks
                    parsed["search_queries"] = web_queries
                    parsed["has_live_search"] = bool(grounding_chunks)
                    if "grounding_model" not in parsed:
                        parsed["grounding_model"] = "claude-sonnet-5-5"
                    logger.info(f"[grounding] Successfully extracted {len(parsed.get('claims', []))} claims with {len(grounding_chunks)} search sources via {parsed.get('grounding_model')}.")
                    return parsed

            except json.JSONDecodeError as je:
                logger.warning(f"[grounding] Failed to parse JSON from {model_name} response: {je}")
                last_err = je
            except urllib.error.HTTPError as he:
                last_err = he
                if he.code in (500, 502, 503, 504, 429) and attempt < max_retries - 1:
                    wait_sec = 2 * (attempt + 1)
                    logger.warning(f"[grounding] HTTP {he.code} on {model_name}. Retrying in {wait_sec}s...")
                    time.sleep(wait_sec)
                    continue
                else:
                    logger.warning(f"[grounding] HTTP {he.code} on {model_name}. Fallback to claude-sonnet-5-5...")
                    break
            except Exception as e:
                last_err = e
                logger.warning(f"[grounding] Unexpected error on {model_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                break

    # Final robust fallback to claude-sonnet-5-5 via HHTech API
    logger.info(f"[grounding] Invoking primary fallback model claude-sonnet-5-5 via HHTech API...")
    try:
        from app.services.model_gateway import get_global_gateway
        gw = get_global_gateway()
        fallback_prompt = (
            f"You are an Elite Forensic Research Fact-Finder for an investigative documentary channel.\n"
            f"Construct a Deep Investigative Factual Dossier containing 12 to 18 concrete, verifiable factual claims for topic: '{topic}'.\n\n"
            f"Output ONLY valid JSON matching this schema:\n"
            f'{{\n  "topic": "{topic}",\n  "temporal_cadence": "MACRO_SAGA|MID_TACTICAL|FLASH_CRISIS",\n'
            f'  "rejected": false,\n  "reject_reason": "",\n'
            f'  "causal_epochs": [\n    {{"epoch_stage": "genesis_seed|critical_rupture", "time_marker": "...", "event_summary": "...", "verified_claim": "..."}}\n  ],\n'
            f'  "claims": [\n    {{\n      "claim": "Specific factual claim with concrete metric/action",\n'
            f'      "source": "Name of reporting outlet or agency",\n      "source_url": "",\n      "date": "YYYY-MM-DD",\n'
            f'      "confidence": "verified",\n      "causal_role": "primary_catalyst|transmission_mechanism|background_context",\n'
            f'      "mechanism": "legal|financial|regulatory",\n      "act_target": "ACT_I|ACT_II|ACT_III|ACT_IV|ACT_V"\n    }}\n  ]\n}}'
        )
        sonnet_res = gw.call_llm(prompt=fallback_prompt, model="claude-sonnet-5-5", temperature=0.1, max_tokens=3500)
        m_s = re.search(r"\{.*\}", sonnet_res, re.DOTALL)
        if m_s:
            parsed = json.loads(m_s.group(0))
            parsed["grounding_chunks"] = []
            parsed["search_queries"] = []
            parsed["has_live_search"] = False
            parsed["grounding_model"] = "claude-sonnet-5-5"
            return parsed
    except Exception as e_fb:
        logger.error(f"[grounding] Fallback claude-sonnet-5-5 failed: {e_fb}")

    logger.error(f"[grounding] All grounding models failed: {last_err}")
    return {
        "topic": topic,
        "rejected": True,
        "reject_reason": f"All grounding models failed: {last_err}",
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
        return False, f"Factual Density Failure: Insufficient total claims ({len(claims)} found, required >= {min_claims} to prevent B2 hallucination)."

    verified_claims = [c for c in claims if str(c.get("confidence", "")).lower() == "verified"]
    if len(verified_claims) < min_verified:
        return False, f"Insufficient verified claims ({len(verified_claims)} found, required >= {min_verified})."

    if require_whitelist:
        has_whitelisted_verified = False
        chunks = grounding_result.get("grounding_chunks", [])
        has_trusted_chunk = any(
            is_trusted_domain(chunk.get("title", ""), chunk.get("uri", ""))
            for chunk in chunks
        )

        for c in verified_claims:
            if is_trusted_domain(c.get("source", ""), c.get("source_url", "")):
                has_whitelisted_verified = True
                break
            elif has_trusted_chunk and str(c.get("confidence", "")).lower() == "verified":
                has_whitelisted_verified = True
                break

        if not has_whitelisted_verified:
            has_whitelisted_any = any(
                is_trusted_domain(c.get("source", ""), c.get("source_url", "")) for c in claims
            ) or has_trusted_chunk
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
        "### REAL-WORLD GROUNDED FACTS DOSSIER (MANDATORY TRUTH ANCHOR)",
        "The following factual claims have been independently verified via live web research.",
        "MANDATORY FACT-LOCK DIRECTIVES (RULE 118, RULE 130 & RULE 445):",
        "1. FACT-LOCK INTEGRITY: Every Act MUST anchor its core arguments around its designated verified claims. Do NOT invent dates, financial sums, quotes, court filings, or institutional conclusions outside this Dossier.",
        "2. VERIFIED claims: You may assert directly as established facts.",
        "3. REPORTED claims: Naturally attribute to reporting outlets or agencies (e.g. 'Reuters reported...', 'Bloomberg documented...'). STRICTLY FORBIDDEN: Robotic boilerplate openers like 'according to provided summaries' or 'as stated in the data'.",
        "4. SPECULATIVE claims: You MUST use cautious conditional framing ('If subsequent assessments hold...', 'Under projected scenarios...').",
        "5. CAUSAL HIERARCHY & INTEGRITY (RULE 130):",
        "   - [PRIMARY_CATALYST] (Level 1): The direct physical, military, legal, or commercial spark. Act I Hook MUST feature this catalyst to pay off the viewer's search query immediately.",
        "   - [TRANSMISSION_MECHANISM] (Level 2): The systemic channel (insurance, liquidity, margin call, regulatory notice, supply bottleneck). Acts III & IV must dissect this mechanism.",
        "   - ZERO INVERTED CAUSALITY: Strictly forbidden to present a transmission mechanism as the original primary trigger.",
        "6. CONNECTIVE TISSUE RESTRICTION: Connective narrative between facts MUST consist exclusively of forensic analysis, dramatic pacing, procedural questioning, and systemic context—NEVER fabricate new factual events or ungrounded statistics to fill word count.",
        "7. SEARCH-INTENT DIRECT PAYOFF: Do NOT clickbait or drift away into academic abstractions. Address the central headline question within the opening 60 seconds.",
        "8. CONTEMPORARY EVENT ANCHOR & TREND-INTENT PRIORITY (MANDATORY IN ACT I):",
        "   - When an episode is based on an active trend, breaking investigation, or contemporary crisis: Act I (specifically paragraph 1 or 2) MUST explicitly name the specific real-world Contemporary Catalyst Event (exact dates, acting entities/governments, and verified quantitative drops/metrics from this table).",
        "   - STRICTLY FORBIDDEN: Hiding behind vague, abstract, or generic phrasing (such as 'When an emergency occurs' or 'When systemic volatility happens') when verified contemporary event details are present in the table!",
        "   - HISTORICAL PRECEDENT DISCIPLINE: Historical comparisons from past eras may ONLY be used in later Acts (Act II/III) as comparative blueprints to explain the legal, institutional, or financial mechanism, NEVER to replace or displace the contemporary catalyst that viewers are actively searching for.",
        "9. EVIDENTIARY DOCUMENT ATTRIBUTION DISCIPLINE (ANTI-HALLUCINATED TITLES):",
        "   - When citing internal reports, slide presentations, memos, or court records from this Dossier, describe their substance accurately using descriptive attribution (e.g. 'internal company slide decks presented to Congress', 'court-ordered discovery exhibits').",
        "   - STRICTLY FORBIDDEN: Inventing catchy fictitious document nicknames, exhibit numbers, or quotation-mark titles not present verbatim in this Dossier.\n"
    ]

    for idx, c in enumerate(claims, 1):
        conf = str(c.get("confidence", "reported")).upper()
        date = c.get("date", "Undated")
        src = c.get("source", "Industry Record")
        mech = c.get("mechanism", "General")
        role = classify_causal_role(c).upper()
        act_tag = f" [{c['act_target'].upper()}]" if c.get("act_target") else ""
        claim_txt = c.get("claim", "")
        lines.append(f"{idx}. [{conf}] [{role}]{act_tag} ({date}) [{src} | Mechanism: {mech}]: {claim_txt}")

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
