#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/unified_vox_director.py
Unified VOX Spatial Physics Director Engine (B3 & B3.5 Combined)
Merges Scene Breakdown, Veo 3.1 3D Tactile Physics (Dynamic Hero clips distributed across Google accounts),
and Tactile Stop-Motion Collage Remotion Directives (12fps stepped jitter, paper drop shadow).
Compliant with:
- Rule 120 (Word-level Audio Sync with Whisper)
- Rule 122 (Pixel-Level Visual Audit Gate & Zero-Mock Score)
- Rule 128 (Zero Semantic Bias in Contracts - 100% Generic across JP, KR, VN, EN)
- Rule 132 (Decoupled Engine)
- Rule 445 (5-Beat Docudrama Storyboard Structure)
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception as ex:
    logger.debug("Stdout encoding reconfigure skipped: %s", ex)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.prompt_forge import _sanitize_background_prompt, _sanitize_foreground_prompt
from app.services.sfx_registry import get_canonical_sfx_list, is_valid_sfx, resolve_semantic_foley

FLOW_ACCOUNTS = ["acc_01", "acc_02", "acc_03", "acc_04", "acc_05", "acc_06", "acc_07"]

# ============================================================================
# DYNAMIC VISUAL ROSTER GENERATOR (RULE 128 - ZERO SEMANTIC BIAS)
# ============================================================================

_TAXONOMY_CACHE: Dict[str, Dict[str, Any]] = {}

def _reset_taxonomy_cache() -> None:
    """Helper for testing and dynamic reloading of visual taxonomy."""
    global _TAXONOMY_CACHE
    _TAXONOMY_CACHE.clear()

def clear_taxonomy_cache() -> None:
    """Public helper for clearing taxonomy cache (Rule 128 & 132)."""
    _reset_taxonomy_cache()

def _load_visual_taxonomy(
    custom_path: Optional[Path] = None,
    required_domains: Optional[list[str]] = None
) -> Dict[str, Any]:
    """Loads external taxonomy config (Rule 128 & 132 SoT).
    Fails closed if taxonomy file is missing, empty, schema is corrupted,
    or required domains specified by consumers are missing.
    Keyed by canonical path and validation requirements to guarantee cache isolation.
    """
    global _TAXONOMY_CACHE
    tax_path = (custom_path or (ROOT_DIR / "config" / "taxonomies" / "visual_rosters.json")).resolve()
    req_tuple = tuple(sorted(required_domains)) if required_domains else ()
    cache_key = f"{tax_path}::{req_tuple}"
    if cache_key in _TAXONOMY_CACHE:
        return _TAXONOMY_CACHE[cache_key]

    if not tax_path.exists():
        raise FileNotFoundError(f"[unified_vox_director] Critical SoT failure: visual taxonomy file not found: {tax_path}")
    try:
        with open(tax_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or not data:
                raise ValueError(f"Taxonomy root must be a non-empty JSON object: {tax_path}")
            if "domains" not in data or not isinstance(data["domains"], dict) or not data["domains"]:
                raise ValueError(f"Taxonomy root must contain a non-empty 'domains' mapping: {tax_path}")
            if required_domains:
                for req_d in required_domains:
                    if req_d not in data["domains"]:
                        raise ValueError(f"Taxonomy missing required domain '{req_d}' expected by consumer: {tax_path}")
            for d_name, d_val in data["domains"].items():
                if not isinstance(d_val, dict):
                    raise ValueError(f"Domain '{d_name}' must be a dict: {tax_path}")
                if "keywords_cjk" not in d_val or not isinstance(d_val["keywords_cjk"], list) or not d_val["keywords_cjk"]:
                    raise ValueError(f"Domain '{d_name}' missing non-empty 'keywords_cjk' list: {tax_path}")
                for kw in d_val["keywords_cjk"]:
                    if not isinstance(kw, str) or not kw.strip():
                        raise ValueError(f"Domain '{d_name}' keywords_cjk contains invalid element {kw!r} (must be non-empty string): {tax_path}")
                if "keywords_en_regex" not in d_val or not isinstance(d_val["keywords_en_regex"], str) or not d_val["keywords_en_regex"].strip():
                    raise ValueError(f"Domain '{d_name}' missing valid 'keywords_en_regex' string: {tax_path}")
                try:
                    d_val["_compiled_en_regex"] = re.compile(d_val["keywords_en_regex"], re.IGNORECASE)
                except re.error as re_err:
                    raise ValueError(f"Domain '{d_name}' invalid 'keywords_en_regex' {d_val['keywords_en_regex']!r}: {re_err}")
                if "markets" not in d_val or not isinstance(d_val["markets"], dict) or not d_val["markets"]:
                    raise ValueError(f"Domain '{d_name}' missing non-empty 'markets' mapping: {tax_path}")
                for mkt_name, mkt_val in d_val["markets"].items():
                    if not isinstance(mkt_val, dict):
                        raise ValueError(f"Market '{mkt_name}' in domain '{d_name}' must be a dict: {tax_path}")
                    if "bg_roster" not in mkt_val or not isinstance(mkt_val["bg_roster"], dict) or not mkt_val["bg_roster"]:
                        raise ValueError(f"Market '{mkt_name}' in domain '{d_name}' missing non-empty 'bg_roster' dict: {tax_path}")
                    if "fg_roster" not in mkt_val or not isinstance(mkt_val["fg_roster"], dict) or not mkt_val["fg_roster"]:
                        raise ValueError(f"Market '{mkt_name}' in domain '{d_name}' missing non-empty 'fg_roster' dict: {tax_path}")
                    for r_type, r_map in [("bg_roster", mkt_val["bg_roster"]), ("fg_roster", mkt_val["fg_roster"])]:
                        for item_k, item_v in r_map.items():
                            if not isinstance(item_v, dict):
                                raise ValueError(f"Item '{item_k}' in {r_type} must be a dict: {tax_path}")
                            if not isinstance(item_v.get("title"), str) or not item_v["title"].strip():
                                raise ValueError(f"Item '{item_k}' in {r_type} missing valid 'title': {tax_path}")
                            if not isinstance(item_v.get("description"), str) or not item_v["description"].strip():
                                raise ValueError(f"Item '{item_k}' in {r_type} missing valid 'description': {tax_path}")
                            beats = item_v.get("beats")
                            if not isinstance(beats, list) or not beats or not all(isinstance(b, int) and not isinstance(b, bool) and 1 <= b <= 5 for b in beats):
                                raise ValueError(f"Item '{item_k}' in {r_type} invalid 'beats' array (must be list of ints 1..5): {tax_path}")
                            if r_type == "fg_roster":
                                if not isinstance(item_v.get("role"), str) or not item_v["role"].strip():
                                    raise ValueError(f"FG item '{item_k}' missing valid 'role' string: {tax_path}")
                                fg_type = item_v.get("type")
                                if not isinstance(fg_type, str) or fg_type not in ("character", "document", "data_metric", "artifact"):
                                    raise ValueError(f"FG item '{item_k}' invalid 'type': {fg_type} (expected character|document|data_metric|artifact): {tax_path}")
                                kw = item_v.get("keywords")
                                if not isinstance(kw, list) or not kw or not all(isinstance(k, str) and k.strip() for k in kw):
                                    raise ValueError(f"FG item '{item_k}' invalid 'keywords' list (must be non-empty list of strings): {tax_path}")
            _TAXONOMY_CACHE[cache_key] = data
            return data
    except Exception as _e:
        logger.error(f"[unified_vox_director] Fail-closed: corrupted visual taxonomy file {tax_path}: {_e}")
        raise

def generate_topic_anchored_roster(
    topic: str,
    market: str,
    key_metrics: list,
    claims: list,
    domain: Optional[str] = None,
    taxonomy_path: Optional[Path] = None,
) -> tuple:
    """Rule 128 & Rule 132: Topic-Anchored Deterministic Visual Roster.
    Generates rich, fully differentiated environmental BGs and tactile evidentiary FGs tailored
    to the target market (JP, KR, VN, EN) and narrative domain (Healthcare, Financial/Debt, Tech/Antitrust).
    Guarantees zero photorealism, strict 2D stylized graphic novel aesthetic, and zero empty scenes.
    """
    m_up = str(market or "EN").upper().strip()
    topic_low = f"{topic or ''} {' '.join(claims or [])}".lower()
    if key_metrics:
        metric_highlight = key_metrics[0]
    elif m_up in ["JP", "JA"]:
        metric_highlight = "定量監査データ // 検証記録"
    elif m_up in ["KR", "KO"]:
        metric_highlight = "정량감사데이터 // 검증기록"
    else:
        metric_highlight = "FORENSIC QUANTITATIVE RECORD // AUDIT FINDING"

    # 1. Configuration-Driven Domain Taxonomy Matching (Rule 128 & Rule 132 SoT)
    taxonomy = _load_visual_taxonomy(custom_path=taxonomy_path)
    domains = taxonomy.get("domains")
    if not isinstance(domains, dict) or not domains:
        raise ValueError(f"Taxonomy root must contain a non-empty 'domains' mapping (fail-closed, Rule 128)")

    matched_domain = None
    matched_domain_name = None

    if domain:
        if domain not in domains:
            raise ValueError(f"Requested domain '{domain}' is not configured in visual taxonomy (fail-closed, Rule 128)")
        matched_domain = domains[domain]
        matched_domain_name = domain
    else:
        for dom_name, dom_cfg in domains.items():
            cjk_kws = dom_cfg.get("keywords_cjk", [])
            compiled_re = dom_cfg.get("_compiled_en_regex")
            if compiled_re is None:
                compiled_re = re.compile(dom_cfg["keywords_en_regex"], re.IGNORECASE)

            if any(kw in topic_low for kw in cjk_kws) or bool(compiled_re.search(topic_low)):
                matched_domain = dom_cfg
                matched_domain_name = dom_name
                break

    if matched_domain is None:
        raise ValueError(f"Topic '{topic}' does not match any configured domain in visual taxonomy (fail-closed, Rule 128 & Rule 132)")

    markets = matched_domain.get("markets", {})
    m_key = "JP" if m_up in ["JP", "JA"] else ("KR" if m_up in ["KR", "KO"] else m_up)
    market_data = markets.get(m_key) or markets.get("EN") or markets.get("JP")
    if not market_data:
        raise ValueError(f"Configured domain '{matched_domain_name}' has no roster for market '{m_up}' (fail-closed, Rule 128)")
    bg_roster = market_data.get("bg_roster")
    fg_roster = market_data.get("fg_roster")
    if not (bg_roster and fg_roster):
        raise ValueError(f"Market '{m_key}' in domain '{matched_domain_name}' missing required rosters (fail-closed, Rule 128)")

    return bg_roster, fg_roster

# Canonical deterministic roster generator & backwards-compatibility alias (Rule 118)
_generate_topic_anchored_roster_fallback = generate_topic_anchored_roster


def extract_dynamic_visual_roster(
    story_text: str = "",
    spoken_sentences: Optional[List[Dict[str, Any]]] = None,
    grounding_intel: Optional[Dict[str, Any]] = None,
    competitor_card: Optional[Dict[str, Any]] = None,
    market: str = "EN",
    topic: str = "",
    dynamic_context: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Rule 128 & Rule 122: Trích xuất danh mục Đạo cụ (Foreground) & Bối cảnh (Background)
    hoàn toàn động theo thị trường bản địa (JP, KR, VN, EN) và dữ liệu thực tế (grounding).
    Sản sinh:
      - 16 đến 20 Backgrounds (16:9 2560x1440) phân bổ đều qua 5 Beats.
      - 20 đến 26 Foregrounds (1:1 2048x2048 trên nền phẳng #FF00FF magenta chroma):
        + 4-6 Nhân vật chủ chốt (type: 'character')
        + 16-20 Đạo cụ bằng chứng / Chứng từ pháp y / Biểu đồ xúc giác (type: 'evidence_prop' | 'document' | 'data_metric')
    CẤM TUYỆT ĐỐI hardcode chỉ 8 items hoặc hardcode tên tập/đạo cụ vụ án cụ thể.
    """
    m_up = str(market or "EN").upper().strip()
    g_intel = grounding_intel or {}
    topic_str = topic or (g_intel.get("topic") if isinstance(g_intel, dict) else "") or "Investigative Docudrama"

    # Trích xuất số liệu định lượng và claims thực tế từ grounding
    claims = []
    if isinstance(g_intel, dict):
        for c in (g_intel.get("claims") or g_intel.get("verified_claims") or [])[:10]:
            txt = c.get("claim") or c.get("text") or c.get("fact") if isinstance(c, dict) else str(c)
            if txt:
                claims.append(txt[:150])

    key_metrics = []
    if isinstance(g_intel, dict) and g_intel.get("grounding_table"):
        for row in g_intel.get("grounding_table", [])[:8]:
            val = row.get("value") or row.get("metric_value")
            unit = row.get("unit") or ""
            param = row.get("parameter") or row.get("claim_id") or ""
            if val:
                key_metrics.append(f"{param}: {val} {unit}".strip())
    elif isinstance(g_intel, dict) and g_intel.get("key_figures"):
        key_metrics.extend([str(x) for x in g_intel.get("key_figures", [])[:6]])

    # Narrative sample
    sample_narr = []
    if spoken_sentences:
        step = max(1, len(spoken_sentences) // 10)
        sample_narr = [s.get("text", "") for s in spoken_sentences[::step][:8]]
    elif story_text:
        sample_narr = [line.strip() for line in story_text.split("\n") if line.strip()][:5]

    if not key_metrics:
        combined_text_src = story_text or " ".join(s.get("text", "") for s in (spoken_sentences or []))
        if combined_text_src:
            found_nums = re.findall(
                r"(?:[$¥₩€£]\s*\d+(?:[.,]\d+)?\s*(?:billion|trillion|million|B|T|M|k|万件|万人|万円|億|兆|万|조|억|만|tỷ|triệu)?|\d+(?:[.,]\d+)?\s*(?:%|percent|billion|trillion|million|万件|万人|万円|億円|兆円|億|兆|万|年|ヶ月|か月|件|조|억|만|년|개월|tỷ|triệu|năm|tháng))",
                combined_text_src,
                flags=re.IGNORECASE
            )
            key_metrics.extend(list(dict.fromkeys([m.strip() for m in found_nums if m.strip()]))[:6])

    bg_roster = None
    fg_roster = None

    # Thử gọi LLM Gateway để sinh Roster hoàn toàn độc lập và động (bỏ qua trong pytest/ci_neighbor_tester để test chạy tức thì)
    is_testing = bool(
        os.environ.get("PYTEST_CURRENT_TEST")
        or "pytest" in sys.modules
        or os.getenv("VF_SMOKE_TEST")
        or os.getenv("FAST_ROSTER")
        or any("ci_neighbor_tester" in str(a) or "smoketest" in str(a) for a in sys.argv)
    )
    use_llm_roster = not bool(os.getenv("DISABLE_LLM_ROSTER", "").lower() in ("1", "true", "yes"))
    if not is_testing and use_llm_roster:
        try:
            from app.services.model_gateway import get_global_gateway
            gateway = get_global_gateway()

            system_prompt = (
                "You are the Lead Cinematographer & VOX Motion Graphics Visual Director (Claude Opus 5.5) for AI Video Factory.\n"
                "Your mission is to architect an authentic, topic-anchored Visual Asset Roster for a 12-20 minute investigative docudrama in VOX / Johnny Harris style.\n"
                "The documentary is structured across 5 Beats:\n"
                "Beat 1: Cold Strike & Paradox Hook (0-60s) | Beat 2: Historical Origin & False Narrative | Beat 3: Forensic Paper Trail | Beat 4: Systemic Climax & Crisis | Beat 5: Modern Warning.\n\n"
                "DIRECTORIAL MANDATES (TOKEN-OPTIMIZED COMPACT SCHEMA):\n"
                "1. 'background_roster': 16 to 20 distinct environmental Backgrounds (keys: 'bg_<slug>').\n"
                "   - Focus strictly on: specific architectural setting, period textures, chiaroscuro lighting mood, and negative space for overlay.\n"
                "   - Schema: {\"title\": \"...\", \"description\": \"Concise 1-2 sentence setting & lighting description\", \"beats\": [1, 2]}\n\n"
                "2. 'foreground_roster': 20 to 24 distinct Foregrounds (keys: 'fg_character_<role>' or 'fg_evidence_<name>').\n"
                "   - Characters (6-8 items): waist-up action framing obeying Vox Actor-Prop Invariant (Actor + Active Verb + Physical Prop + Gaze Target). NO static passport poses. NO magenta clothing.\n"
                "   - Evidence Props (12-16 items): centered tactile documentary artifact, docket, ledger, or chart. Zero human figures, blank templates.\n"
                "   - Schema: {\"title\": \"...\", \"description\": \"Concise 1-2 sentence action and prop manipulation\", \"role\": \"...\", \"beats\": [1, 2], \"keywords\": [\"kw1\", \"kw2\"], \"type\": \"character\"|\"document\"|\"evidence_prop\"|\"data_metric\"}\n\n"
                "3. TOKEN CONSERVATION RULE: Do NOT repeat technical chroma key boilerplate ('isolated on pure #FF00FF...', 'clean cutout', '1:1 ratio') in your output text. Focus 100% on creative narrative authenticity and actions; our downstream pipeline decorates technical chroma parameters deterministically.\n"
                "4. ETHICAL SHIELD: Minors -> Symbolic artifacts only (empty swing, backpack). Named figures -> solid black censor bar across eyes.\n\n"
                "Output ONLY valid JSON matching:\n"
                "{\n"
                "  \"background_roster\": { \"<bg_key>\": { \"title\": \"...\", \"description\": \"...\", \"beats\": [...] } },\n"
                "  \"foreground_roster\": { \"<fg_key>\": { \"title\": \"...\", \"description\": \"...\", \"role\": \"...\", \"beats\": [...], \"keywords\": [...], \"type\": \"...\" } }\n"
                "}"
            )

            user_prompt = json.dumps({
                "topic": topic_str,
                "target_market": m_up,
                "verified_claims": claims[:8] if claims else [],
                "key_metrics": key_metrics[:4] if key_metrics else [],
                "narrative_samples": sample_narr[:2] if sample_narr else []
            }, ensure_ascii=False)

            models_to_try = ["claude-opus-5-5", "gpt-6-astra"]
            resp = None
            for m_candidate in models_to_try:
                try:
                    logger.info(f"[unified_vox_director] Invoking Lead Visual Director ({m_candidate})...")
                    resp = gateway.call_llm(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        model=m_candidate,
                        max_tokens=3000,
                        timeout=90.0,
                        fallback="gpt-6-astra" if m_candidate == "claude-opus-5-5" else None
                    )
                    if resp:
                        break
                except Exception as ex_m:
                    logger.warning(f"[unified_vox_director] Director model {m_candidate} failed: {ex_m}")
            if resp:
                cleaned_json = re.sub(r"^```(?:json)?\s*", "", resp.strip(), flags=re.MULTILINE)
                cleaned_json = re.sub(r"\s*```$", "", cleaned_json, flags=re.MULTILINE)
                try:
                    parsed = json.loads(cleaned_json)
                except Exception:
                    m_json = re.search(r"(\{.*\})", cleaned_json, re.DOTALL)
                    parsed = json.loads(m_json.group(1)) if m_json else {}
                bgs = parsed.get("background_roster", {})
                fgs = parsed.get("foreground_roster", {})
                if len(bgs) >= 8 and len(fgs) >= 10:
                    fb_bgs, fb_fgs = _generate_topic_anchored_roster_fallback(topic_str, m_up, key_metrics, claims)
                    # Decorate and guarantee technical chroma invariants on LLM generated items
                    for bg_k, bg_v in bgs.items():
                        desc = bg_v.get("description", "")
                        if "graphic novel" not in desc.lower() and "illustration" not in desc.lower():
                            bg_v["description"] = f"{desc}, non-photorealistic 2D stylized graphic novel editorial illustration, bold ink linework, cel-shading, 16:9 aspect ratio."
                    for fg_k, fg_v in fgs.items():
                        desc = fg_v.get("description", "")
                        if "#FF00FF" not in desc and "magenta" not in desc.lower():
                            fg_v["description"] = f"{desc}, isolated on a solid flat #FF00FF pure magenta background, clean chroma-key cutout, sharp silhouette, no borders, 1:1 aspect ratio."

                    for k, v in fb_bgs.items():
                        if len(bgs) >= 48:
                            break
                        if k not in bgs:
                            bgs[k] = v
                    for k, v in fb_fgs.items():
                        if len(fgs) >= 32:
                            break
                        if k not in fgs:
                            fgs[k] = v
                    bg_roster = bgs
                    fg_roster = fgs
        except Exception as e:
            logger.info(f"[unified_vox_director] LLM dynamic roster extraction bypassed or failed: {e}")

    # Fallback chất lượng cao nếu LLM không trả kết quả đủ chuẩn
    if not bg_roster or not fg_roster:
        bg_roster, fg_roster = _generate_topic_anchored_roster_fallback(topic_str, m_up, key_metrics, claims)

    # Expand background capacity to 45-48 unique BGs for long-form episodes (>= 10 min / >= 75 scenes / >= 1200 words)
    n_sents = len(spoken_sentences or [])
    n_words = len((story_text or "").split())
    if n_sents >= 75 or n_words >= 1200 or not is_testing:
        bg_roster = expand_longform_background_roster(
            bg_roster=bg_roster,
            target_count=46,
            market=m_up,
            topic=topic_str,
        )

    # Master Representation Shield Gate: Audit Child & Real-Person rules BEFORE B3
    try:
        from app.services.representation_shield import shield_visual_roster
        bg_roster, fg_roster = shield_visual_roster(
            bg_roster=bg_roster,
            fg_roster=fg_roster,
            story_text=story_text,
            market=m_up
        )
    except Exception as ex_shield:
        logger.warning(f"[unified_vox_director] Shield gate execution warning: {ex_shield}")

    return bg_roster, fg_roster


def expand_longform_background_roster(
    bg_roster: Dict[str, Any],
    target_count: int = 46,
    market: str = "EN",
    topic: str = "",
) -> Dict[str, Any]:
    """Expands background roster to 45-50 distinct environmental perspectives for >=10min documentaries.

    Prevents severe asset starvation (where 18 backgrounds repeat 7-27 times across 135+ scenes)
    by generating distinct architectural angles, lighting phases, and archival spatial layers across all 5 Beats.
    """
    expanded = dict(bg_roster or {})
    if len(expanded) >= target_count:
        return expanded

    perspective_variants = [
        (
            "macro_desk_angle",
            "Close architectural tabletop perspective focusing on mahogany surface textures, warm brass banker lamp illumination, and deep chiaroscuro background shadows",
            [1, 3],
        ),
        (
            "nocturnal_overlook",
            "High-elevation nocturnal architectural perspective through rain-streaked glass overlooking city financial district lights, moody cyan and amber atmospheric lighting",
            [2, 4],
        ),
        (
            "archival_corridor_depth",
            "Deep vanishing-point perspective along institutional archival shelving and reinforced steel doors, dramatic overhead fluorescent pool lighting, clean negative space",
            [3, 5],
        ),
    ]

    base_items = list(expanded.items())
    for var_idx, (suffix, angle_desc, fallback_beat_indices) in enumerate(perspective_variants):
        for k, v in base_items:
            if len(expanded) >= target_count:
                break
            new_key = f"{k}_{suffix}"
            if new_key in expanded:
                continue
            v_dict = dict(v) if isinstance(v, dict) else {"title": str(k), "description": str(v)}
            base_desc = v_dict.get("description", "")
            base_title = v_dict.get("title", k)
            beats = v_dict.get("beats") or fallback_beat_indices
            shifted_beats = [((int(b) + var_idx) % 5) + 1 for b in beats]
            expanded[new_key] = {
                "title": f"{base_title} ({suffix.replace('_', ' ').title()})",
                "description": f"{base_desc} Framed from {angle_desc}.",
                "beats": sorted(list(set(shifted_beats))),
            }
        if len(expanded) >= target_count:
            break

    return expanded


# ============================================================================
# DYNAMIC HERO CADENCE & SPATIAL PHYSICS (RULE 128)
# ============================================================================

def select_dynamic_hero_indices(
    spoken_sentences: List[Dict[str, Any]],
    video_budget_mode: Optional[str] = None
) -> List[int]:
    """Rule 128 & User Mandate: Tuyển chọn các cảnh Hero AI Video (VEO / Omni) hoàn toàn động dựa trên nhịp điệu kể chuyện (cadence).
    Hỗ trợ 3 chế độ ngân sách trên 6 tài khoản Gmail:
    - 'standard_18': Tối đa 18 clips (6 acc x 3 clips Veo Quality, min_dist=3).
    - 'low_token_36': Tối đa 36 clips (6 acc x 6 clips Veo Fast / Low-Token, ~216s AI Video, min_dist=2).
    - 'omni_48': Tối đa 48 clips (6 acc x 8 clips Omni Flash / Low-Token, ~288s AI Video, min_dist=2).
    """
    total = len(spoken_sentences)
    if total == 0:
        return []
    if total <= 3:
        return [0]

    mode = (video_budget_mode or os.getenv("VF_VIDEO_BUDGET_MODE", "standard_18")).lower().strip()
    if mode == "omni_48":
        max_cap = 48
        min_dist = 2
        max_gap = 4
    elif mode in ("low_token_36", "veo_fast_36", "veo_fast"):
        max_cap = 36
        min_dist = 2
        max_gap = 5
    else:
        max_cap = 18
        min_dist = 3
        max_gap = 8

    # Nhận diện điểm khởi đầu các Beat
    beat_first_indices = {}
    for idx, s in enumerate(spoken_sentences):
        b = int(s.get("beat_index") or ((idx // max(1, total // 5)) + 1))
        b = min(max(b, 1), 5)
        if b not in beat_first_indices:
            beat_first_indices[b] = idx

    # Từ khóa bằng chứng / xúc tác căng thẳng cao độ (đa ngôn ngữ EN, JP, KR, VN)
    catalyst_keywords = [
        # Numbers & metrics
        "billion", "tỷ", "million", "triệu", "억", "조", "万", "億", "兆", "mg/kg", "ppm", "percent", "%",
        # Legal & documents
        "docket", "complaint", "vụ kiện", "bản án", "cáo trạng", "khởi tố", "기소", "소송", "訴訟", "起訴",
        "gavel", "búa gỗ", "judge", "thẩm phán", "판사", "裁判",
        "statute", "đạo luật", "luật", "법률", "法律",
        "algorithm", "thuật toán", "알고리즘", "アルゴリズム",
        "secret", "bí mật", "whistleblower", "nội bộ", "내부고발", "内部告発",
        "damages", "thiệt hại", "hóa đơn", "invoice", "손해", "損害", "賠償",
        "memo", "redacted", "bôi đen", "ledger", "sổ sách", "장부", "帳簿",
        "court", "tòa án", "법원", "裁判所", "hearing", "điều trần", "청문회", "公聴会",
        "inspect", "quarantine", "thanh tra", "kiểm định", "감사", "검사", "監査", "検査"
    ]

    selected = [0]  # Scene 0 luôn là Hero
    last_hero = 0

    for idx in range(1, total):
        sent = spoken_sentences[idx]
        text = (sent.get("text") or "").lower()
        dist = idx - last_hero

        if dist < min_dist:
            continue

        is_beat_start = any(idx == b_idx for b_idx in beat_first_indices.values())
        is_climax_or_end = (idx == total - 1) or (idx >= total - 3 and any(w in text for w in ["gavel", "verdict", "judge", "court", "warning", "lesson", "búa", "kết luận", "판결", "判決"]))
        has_catalyst = any(kw in text for kw in catalyst_keywords)

        if dist >= max_gap:
            selected.append(idx)
            last_hero = idx
        elif is_beat_start and dist >= max(min_dist, 3 if max_cap == 18 else 2):
            selected.append(idx)
            last_hero = idx
        elif is_climax_or_end and dist >= min_dist:
            selected.append(idx)
            last_hero = idx
        elif has_catalyst and dist >= (5 if max_cap == 18 else 2):
            selected.append(idx)
            last_hero = idx

    if len(selected) > max_cap:
        mandatory = {0, selected[-1]}
        for b_idx in beat_first_indices.values():
            if b_idx in selected:
                mandatory.add(b_idx)
        remaining = [x for x in selected if x not in mandatory]
        needed = max_cap - len(mandatory)
        if needed > 0 and remaining:
            step = len(remaining) / needed
            picked = [remaining[int(i * step)] for i in range(needed)]
            selected = sorted(list(mandatory.union(picked)))
        else:
            selected = sorted(list(mandatory))[:max_cap]

    return selected


def determine_spatial_physics(narr: str, fg_key: Optional[str], hero_index: int) -> Tuple[str, str, str, str]:
    """Xác định hành vi xúc giác (Tactile Spatial Physics) dựa trên bản chất vật thể và ngữ cảnh kể chuyện (Rule 128).
    Hỗ trợ đối chiếu đa ngôn ngữ: EN, JP, KR, VN.
    Sử dụng CANONICAL_SFX_REGISTRY tuyệt đối, cấm sinh cue tùy tiện.
    Trả về: (physics_type, action_type, seed_mode, foleys)
    """
    foleys = resolve_semantic_foley(narr, fg_key, hero_index)
    n_low = (narr or "").lower()
    fg_low = (fg_key or "").lower()
    combined = f"{n_low} {fg_low}"

    if foleys in ["gavel_thud", "gauge_needle_hiss"]:
        return "MACRO_HIGHLIGHT_WIPE", "MACRO_HIGHLIGHT_WIPE", "CUTOUT_ONLY", foleys
    elif any(k in combined for k in ["docket", "memo", "confidential", "secret", "whistleblower", "dog-ear", "peel", "cáo trạng", "khởi tố", "mật", "bóc tách", "기소", "고발", "비밀", "内部告発"]):
        return "CORNER_DOGEAR_PEEL", "CORNER_DOGEAR_PEEL", "COMPOSITE_16_9", foleys
    elif any(k in combined for k in ["invoice", "damage", "bill", "check", "listing", "card", "hóa đơn", "bồi thường", "chi phí", "영수증", "손해", "請求書", "損害"]):
        return "DOCUMENT_TABLE_DROP", "DOCUMENT_TABLE_DROP", "COMPOSITE_16_9", foleys
    elif any(k in combined for k in ["dossier", "contract", "agreement", "binder", "ledger", "book", "hợp đồng", "sổ sách", "hồ sơ", "계약", "장부", "契約", "帳簿"]):
        return "BIFOLD_DOSSIER_OPEN", "BIFOLD_DOSSIER_OPEN", "COMPOSITE_16_9", foleys
    else:
        cycle = hero_index % 3
        if cycle == 0:
            return "CORNER_DOGEAR_PEEL", "CORNER_DOGEAR_PEEL", "COMPOSITE_16_9", foleys
        elif cycle == 1:
            return "DOCUMENT_TABLE_DROP", "DOCUMENT_TABLE_DROP", "COMPOSITE_16_9", foleys
        else:
            return "BIFOLD_DOSSIER_OPEN", "BIFOLD_DOSSIER_OPEN", "COMPOSITE_16_9", foleys


def load_style_config(preset_name: Optional[str] = None) -> Dict[str, Any]:
    """Nạp cấu hình phong cách từ config/prompts/style-config.yaml (Rule 128 & Rule 132)."""
    config_path = ROOT_DIR / "config" / "prompts" / "style-config.yaml"
    if not config_path.exists():
        return {
            "name": "vox_forensic_paper",
            "positive": "tangible forensic investigative paper docudrama, heavy 300gsm fibrous cardstock, sharp cardstock creases, official audit stamps, classified exhibit labels, clean 2D stylized graphic novel comic ink outlines, bold linework, crosshatching, flat cel-shading, tabletop flat-lay evidence setting",
            "motion_behavior": "12fps tactile stop-motion documentary motion, mechanical paper folding and dog-ear corner peel, crisp document table drop with subtle paper flutter, steady tripod camera drift, zero warping or morphing of text, staggered discrete frame steps",
            "negative": "no photorealism, no live-action video, no real people, no 3D wax characters, no smooth 60fps interpolation, no gooey liquid warping, no anime, no watercolor",
            "camera_defaults": {"allowed": ["static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"]},
            "lighting_defaults": "45-degree directional evening boardroom keylight, deep contact shadows onto dark mahogany surface",
            "clip_duration_seconds": {"min": 4, "max": 8, "default": 5},
            "prompt_template": "{style_anchor.positive}, {style_anchor.motion_behavior}. Scene: {scene.subject} {scene.action} in {scene.setting}. Camera: {scene.camera}. Lighting: {scene.lighting}. {style_anchor.negative}"
        }

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    presets = data.get("presets", {})
    chosen_name = preset_name or data.get("active_preset", "vox_forensic_paper")
    preset_data = presets.get(chosen_name)
    if not preset_data:
        chosen_name = next(iter(presets.keys()), "vox_forensic_paper")
        preset_data = presets.get(chosen_name, {})

    return {
        "name": chosen_name,
        "positive": " ".join(str(preset_data.get("positive", "")).split()),
        "motion_behavior": " ".join(str(preset_data.get("motion_behavior", "")).split()),
        "negative": " ".join(str(preset_data.get("negative", "")).split()),
        "camera_defaults": preset_data.get("camera_defaults", {"allowed": ["static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"]}),
        "lighting_defaults": " ".join(str(preset_data.get("lighting_defaults", "warm diorama studio light, soft shadows, subtle rim light")).split()),
        "clip_duration_seconds": preset_data.get("clip_duration_seconds", {"min": 4, "max": 8, "default": 5}),
        "prompt_template": data.get("prompt_template", "")
    }


def format_final_veo_prompt(
    preset: Dict[str, Any],
    subject: str,
    action: str,
    setting: str,
    camera: str,
    lighting: Optional[str] = None
) -> str:
    """Ghép final_veo_prompt theo template chuẩn:
    {style_anchor.positive}, {style_anchor.motion_behavior}.
    Scene: {scene.subject} {scene.action} in {scene.setting}.
    Camera: {scene.camera}. Lighting: {scene.lighting}.
    {style_anchor.negative}
    """
    pos = preset.get("positive", "")
    mot = preset.get("motion_behavior", "")
    neg = preset.get("negative", "")
    lt = lighting or preset.get("lighting_defaults", "")

    prompt = (
        f"{pos}, {mot}. "
        f"Scene: {subject} {action} in {setting}. "
        f"Camera: {camera}. Lighting: {lt}. "
        f"{neg}"
    )
    return " ".join(prompt.split())


def get_action_description(action_type: str, seed_title: str, narration: str) -> str:
    """Tạo mô tả hành động xúc giác ngắn gọn cho VEO physics prompt (không lặp lại subject)."""
    if action_type == "CORNER_DOGEAR_PEEL":
        return "top sheet dog-ear corner curling and peeling backward in crisp 12fps mechanical steps, lifting upward to reveal confidential audit docket beneath"
    elif action_type == "DOCUMENT_TABLE_DROP":
        return "sliding rapidly into frame and slamming onto executive table with a sharp stop-motion bounce, settling flat with paper flutter"
    elif action_type == "BIFOLD_DOSSIER_OPEN":
        return "with sharp center crease opening outward flat onto table in clean mechanical 12fps steps, revealing internal financial charts"
    elif action_type == "MACRO_HIGHLIGHT_WIPE":
        n_low = narration.lower()
        if any(k in n_low for k in ["gavel", "judge", "court", "verdict", "búa", "toà"]):
            return "resting beside brass scales of justice on mahogany table under dramatic directional spotlight with subtle dust motes and micro-vibrations"
        elif any(k in n_low for k in ["gauge", "needle", "chemical", "sulfur", "residue", "hóa chất"]):
            return "industrial circular analog gauge needle rising steadily toward danger threshold zone with warm reflection"
        elif any(k in n_low for k in ["server", "hardware", "rack", "máy chủ"]):
            return "high-tech enterprise server rack drive module with rhythmic blue data activity LEDs flashing in cool mist"
        else:
            return "resting on dark mahogany desk under dramatic directional studio keylight with 12fps documentary tracking motion"
    else:
        return "resting on table with subtle 12fps micro-jitter in steady documentary tracking"


def inject_speech_timestamp_cue(sentence_obj: Dict[str, Any], dur_sec: float) -> str:
    """Trích xuất mốc giây từ khóa hành động/con số trong câu thoại để nhúng vào Video Prompt (Speech-Locked Timestamp Cue)."""
    if not isinstance(sentence_obj, dict):
        return ""
    text = (sentence_obj.get("text") or "").strip()
    if not text:
        return ""

    words_arr = sentence_obj.get("words") or []
    start_base = float(sentence_obj.get("start_sec") or sentence_obj.get("start") or 0.0)

    # 1. Nếu có word-level timestamps từ Whisper / Edge-TTS
    if isinstance(words_arr, list) and words_arr:
        for w_item in words_arr:
            if not isinstance(w_item, dict):
                continue
            w_txt = str(w_item.get("word") or w_item.get("text") or "").strip()
            if re.search(r"(\d+|%|billion|million|trillion|collapse|open|slam|drop|crash|tear|stamp|verdict|secret|leak)", w_txt, re.I):
                w_start = float(w_item.get("start") or w_item.get("start_sec") or start_base)
                rel_sec = max(0.4, min(round(w_start - start_base, 1), max(1.0, round(dur_sec - 0.8, 1))))
                clean_w = re.sub(r"[^\w$%.-]", "", w_txt)
                return f"At {rel_sec:.1f}s when narration hits '{clean_w}', trigger primary cutout snap and focus rack."

    # 2. Ước lượng vị trí từ khóa theo vị trí từ trong câu (2.5 words/sec)
    tokens = text.split()
    for idx, tok in enumerate(tokens):
        if re.search(r"(\d+|%|billion|million|trillion|collapse|open|slam|drop|crash|tear|stamp|verdict|secret|leak|tỷ|triệu)", tok, re.I):
            rel_sec = max(0.5, min(round((idx / max(1, len(tokens))) * dur_sec, 1), max(1.0, round(dur_sec - 0.8, 1))))
            clean_w = re.sub(r"[^\w$%.-]", "", tok)
            return f"At {rel_sec:.1f}s when narration hits '{clean_w}', trigger primary cutout snap and focus rack."

    mid_sec = round(dur_sec * 0.45, 1)
    return f"At {mid_sec:.1f}s mid-sentence beat, trigger primary layer snap and focus rack."


def generate_tactile_physics_prompt(scene_idx: int, narration: str, action_type: str, seed_title: str) -> str:
    """Backward-compatible wrapper for tactile physics prompt."""
    preset = load_style_config("vox_forensic_paper")
    action_desc = get_action_description(action_type, seed_title, narration)
    return format_final_veo_prompt(
        preset=preset,
        subject=seed_title,
        action=action_desc,
        setting="dark mahogany executive boardroom table at dusk",
        camera="slow_push_in" if scene_idx % 2 == 0 else "cinematic_pan"
    )


def validate_director_sfx_compliance(scenes: List[Dict[str, Any]], hero_clips: List[Dict[str, Any]]) -> None:
    """Chốt chặn kiểm toán pháp y SFX B3 (Rule 120, Rule 128 & Rule 134).
    Bắt buộc 100% scenes và hero_clips phải dùng foley cue nằm trong CANONICAL_SFX_REGISTRY.
    CẤM TUYỆT ĐỐI lọt cue lạ hoặc unconstrained string sang B4-B6.
    """
    invalid_cues = []
    for sc in scenes:
        cue = sc.get("foleys_audio") or sc.get("audio_cue")
        if cue and not is_valid_sfx(cue):
            invalid_cues.append(f"Scene {sc.get('scene_id')}: invalid foley cue '{cue}'")
    for hc in hero_clips:
        cue = hc.get("foleys_audio") or hc.get("audio_cue")
        if cue and not is_valid_sfx(cue):
            invalid_cues.append(f"Hero Clip {hc.get('scene_id')}: invalid foley cue '{cue}'")

    if invalid_cues:
        raise ValueError(
            f"❌ B3 DIRECTOR SFX COMPLIANCE FAILED ({len(invalid_cues)} violations):\n" +
            "\n".join(invalid_cues) +
            f"\nAllowed Canonical SFX: {get_canonical_sfx_list()}"
        )


def generate_cinematography_scene_data(
    idx: int,
    beat_idx: int,
    dur_frames: int,
    assigned_fg: Optional[str],
    fg_info: Optional[Dict[str, Any]],
    bg_key: str,
    layout_choice: str,
    cam_move: str,
    narr: str,
    mkt: str,
    key_metrics: List[Any],
    topic: str
) -> Dict[str, Any]:
    """Generate 3-entity hierarchy, virtual camera, and parametric motion path waypoints
    per Opus 5.5 Cinematography Director Engine (Plan Section III).
    """
    focal = 28 if beat_idx == 1 else (35 if beat_idx in (2, 3) else (50 if beat_idx == 4 else 85))
    dof_blur = 3.5 if assigned_fg else 0.5
    virtual_camera = {
        "focal_length_mm": focal,
        "depth_of_field_blur": dof_blur,
        "key_lighting": "chiaroscuro_noir_top_left" if beat_idx in (1, 4) else "diffused_institutional_daylight",
        "camera_move": cam_move,
        "scale_range": [1.0, 1.08] if beat_idx == 1 else ([1.0, 1.05] if beat_idx in (2, 3) else [1.0, 1.10])
    }

    primary_hero = None
    if assigned_fg:
        is_left = "left" in layout_choice
        start_x = -15 if is_left else 115
        target_x = 45 if is_left else 55
        target_y = 50
        primary_hero = {
            "id": f"hero_{assigned_fg}",
            "src": f"pulled/{assigned_fg}.png",
            "role": (fg_info or {}).get("role", "central_investigative_subject"),
            "motion_path": [
                {"frame": 0, "x_pct": start_x, "y_pct": 58, "z_depth": 0.85, "scale": 0.88, "rot_deg": -6 if is_left else 6, "easing": "bezier"},
                {"frame": 24, "x_pct": target_x, "y_pct": target_y, "z_depth": 1.0, "scale": 1.08, "rot_deg": 1.5 if is_left else -1.5, "easing": "spring_overshoot"},
                {"frame": 36, "x_pct": target_x, "y_pct": target_y + 2, "z_depth": 1.0, "scale": 1.0, "rot_deg": 0, "easing": "settle_lock"},
                {"frame": dur_frames, "x_pct": target_x + (1.5 if is_left else -1.5), "y_pct": target_y + 2, "z_depth": 1.0, "scale": 1.02, "rot_deg": 0.2 if is_left else -0.2, "easing": "micro_breathing"}
            ]
        }

    linked_secondary = []
    narr_l = narr.lower()
    stamp_triggers = [
        "reject", "rejected", "denied", "dismissed", "stay", "stayed", "bankruptcy",
        "fraud", "confidential", "violation", "evidence", "void", "audit",
        "bằng chứng", "gian lận", "mật", "vi phạm",
        "사기", "증거", "비밀", "위반", "기각",
        "証拠", "違反", "漏洩", "却下", "拒否", "極秘", "機密", "不正", "監査", "記録なし", "未回答", "発覚", "流出", "処分"
    ]
    if any(w in narr_l for w in stamp_triggers):
        if any(w in narr_l for w in ["reject", "rejected", "denied", "dismissed", "却下", "拒否", "기각"]):
            stamp_label = "REJECTED" if mkt not in ("JP", "JA") else "却下 // REJECTED"
        elif any(w in narr_l for w in ["stay", "stayed", "bankruptcy", "insolvency", "freeze", "破産", "凍結"]):
            stamp_label = "STAYED"
        elif any(w in narr_l for w in ["fraud", "gian lận", "不正", "違反", "漏洩", "流出", "사기", "위반"]):
            stamp_label = "VIOLATION_FOUND" if mkt not in ("JP", "JA") else "違反確認 // BREACH"
        elif any(w in narr_l for w in ["confidential", "mật", "極秘", "機密", "비밀", "未回答", "記録なし"]):
            stamp_label = "REDACTED" if mkt not in ("JP", "JA") else "極秘 // UNDISCLOSED"
        else:
            stamp_label = "AUDIT_FINDING" if mkt not in ("JP", "JA") else "監査証拠 // EXHIBIT"
        linked_secondary.append({
            "id": f"stamp_{idx}",
            "type": "stamp",
            "label": stamp_label,
            "slam_frame": 18,
            "x_pct": 68 if "left" in layout_choice else 32,
            "y_pct": 45,
            "theme": "danger" if beat_idx >= 3 else "investigation",
            "rot_deg": -5.5 if idx % 2 == 0 else 4.5
        })

    marker_triggers = [
        "article", "clause", "provision", "document", "record",
        "hồ sơ", "điều khoản", "tài liệu",
        "기록", "조항", "문서", "보고서",
        "条項", "規定", "文書", "報告書", "記録", "データ", "規約", "契約", "調査", "リスト", "一覧", "公表"
    ]
    if any(w in narr_l for w in marker_triggers):
        linked_secondary.append({
            "id": f"marker_{idx}",
            "type": "marker_sweep",
            "sweep_start_frame": 12,
            "sweep_duration_frames": 14,
            "color": "#ffe600"
        })

    stat_val_extracted = None
    stat_lbl_extracted = None
    for m_num in re.finditer(
        r'(?:([\$¥₩€£])\s*)?(\d+(?:[.,]\d+)?)\s*(万件|万人|万円|億円|兆円|億|兆|万|%|年|ヶ月|か月|日間|時間|件|倍|조|억|만|년|개월|(?:percent|billion|million|trillion|tỷ|triệu|nghìn|năm|tháng|years|months|days|B|M|T)\b)',
        narr,
        re.IGNORECASE
    ):
        prefix_sym = m_num.group(1) or ""
        raw_num_str = m_num.group(2).replace(",", "")
        unit_str = m_num.group(3) or ""
        try:
            val = float(raw_num_str)
        except ValueError:
            continue
        # Skip 4-digit calendar years (e.g. 2024年, 2026年) so they aren't mistaken for quantitative metrics
        if unit_str in ("年", "년") and 1900 <= val <= 2099:
            continue
        stat_val_extracted = f"{prefix_sym}{m_num.group(2)}{unit_str}"
        stat_lbl_extracted = (
            "重要検証データ // VERIFIED METRIC" if mkt in ("JP", "JA") else
            ("핵심 검증 지표 // VERIFIED METRIC" if mkt in ("KR", "KO") else "VERIFIED FORENSIC METRIC")
        )
        if beat_idx in (1, 3, 4):
            linked_secondary.append({
                "id": f"odometer_{idx}",
                "type": "odometer",
                "start_value": 0,
                "end_value": val,
                "prefix": prefix_sym,
                "suffix": unit_str[:4],
                "label": stat_lbl_extracted,
                "start_frame": 6,
                "duration_frames": 24
            })
        break

    headline_info = {}
    if idx == 0 and key_metrics:
        m_val = key_metrics[0]
        headline_info = {
            "headline": f"CRITICAL ANOMALY: {m_val}".upper(),
            "highlight_word": str(m_val),
            "category": f"FORENSIC INVESTIGATION // {mkt} ANALYSIS",
            "subtext": "STATUTORY SYSTEMIC AUDIT",
            "accent_color": "#f59e0b"
        }

    return {
        "virtual_camera": virtual_camera,
        "primary_hero": primary_hero,
        "linked_secondary_objects": linked_secondary,
        "headline_info": headline_info,
        "stat_value": stat_val_extracted,
        "stat_label": stat_lbl_extracted,
    }


def compile_stateful_boards(scenes: List[Dict[str, Any]], board_size: int = 4) -> List[Dict[str, Any]]:
    """Group individual sentence-scenes into Stateful Investigation Boards (3-4 scenes per Board).
    - Persists the Board tabletop background across scenes within the same Board.
    - Accumulates evidentiary foreground props across beats within the Board so the tabletop builds a living argument.
    - Assigns motivated Vox transitions (paper_slide, vox_push_zoom, match_cut within a Board;
      push_through or vox_paper_wipe between Boards; hard_cut reserved strictly for Beat boundaries <= 15%).
    """
    boards: List[Dict[str, Any]] = []
    current_board: List[Dict[str, Any]] = []
    last_beat = None

    for sc in scenes:
        b_idx = sc.get("beat_index", 1)
        if current_board and (len(current_board) >= board_size or b_idx != last_beat):
            boards.append({"board_index": len(boards), "beat_index": last_beat, "scenes": current_board})
            current_board = []
        current_board.append(sc)
        last_beat = b_idx
    if current_board:
        boards.append({"board_index": len(boards), "beat_index": last_beat, "scenes": current_board})

    internal_transitions = ["paper_slide", "vox_push_zoom", "match_cut", "vox_tape_snap"]
    boundary_transitions = ["push_through", "vox_paper_wipe"]

    for b_meta in boards:
        b_idx = b_meta["board_index"]
        b_id = f"board_{b_idx:02d}"
        b_scenes = b_meta["scenes"]
        primary_bg = b_scenes[0].get("background")
        accumulated_props: List[Dict[str, Any]] = []

        for step_idx, sc in enumerate(b_scenes):
            sc["board_id"] = b_id
            sc["board_step"] = step_idx
            has_own_bg = isinstance(sc.get("background"), dict) and bool(sc["background"].get("reuse_key"))
            if primary_bg and isinstance(sc.get("background"), dict) and not has_own_bg:
                sc["background"] = dict(primary_bg)

            # Copy accumulated props from earlier steps in this Board before adding current FG
            sc["board_accumulated_props"] = list(accumulated_props)

            fg = sc.get("foreground")
            if isinstance(fg, dict) and fg.get("reuse_key"):
                rk = fg["reuse_key"]
                if not any(p.get("reuse_key") == rk for p in accumulated_props):
                    accumulated_props.append({
                        "reuse_key": rk,
                        "title": fg.get("title") or rk,
                        "role": fg.get("role") or "EVIDENCE",
                        "step_added": step_idx,
                    })

            # Motivated Transition Assignment (Hard-cut capped <= 15%)
            is_last_in_board = (step_idx == len(b_scenes) - 1)
            if not is_last_in_board:
                sc["transition_out"] = internal_transitions[(b_idx + step_idx) % len(internal_transitions)]
            else:
                next_board = boards[b_idx + 1] if (b_idx + 1) < len(boards) else None
                is_beat_change = bool(next_board and next_board["beat_index"] != b_meta["beat_index"])
                if is_beat_change or (b_idx % 6 == 5):
                    sc["transition_out"] = "hard_cut"
                else:
                    sc["transition_out"] = boundary_transitions[b_idx % len(boundary_transitions)]


        b_meta["board_id"] = b_id
        b_meta["surface_bg"] = (primary_bg or {}).get("reuse_key") if isinstance(primary_bg, dict) else None
        b_meta["scene_ids"] = [s.get("scene_id") for s in b_scenes]
        b_meta["accumulated_prop_keys"] = [p["reuse_key"] for p in accumulated_props]

    return boards



# ============================================================================
# MASTER UNIFIED DIRECTOR PLANNER (RULE 125 SINGLE TRUTH & RULE 128)
# ============================================================================

def build_unified_director_plan(
    spoken_sentences: List[Dict[str, Any]],
    ep_dir: Path,
    style_preset: Optional[str] = None,
    story_text: Optional[str] = None,
    grounding_intel: Optional[Dict[str, Any]] = None,
    competitor_card: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    market: Optional[str] = None
) -> Dict[str, Any]:
    """Hợp nhất B3 + B3.5:
    Tạo cấu trúc phân cảnh, gán Veo clips Tactile Physics động và Remotion Stop-Motion Directives.
    Hoàn toàn Generic 100%, không bị bias hay hardcode vào bất kỳ đề tài đơn lẻ nào (Rule 128).
    """
    preset = load_style_config(style_preset)
    allowed_cameras = preset.get("camera_defaults", {}).get("allowed", [
        "static", "slow_push_in", "slow_pull_out", "cinematic_pan", "macro_tilt"
    ])
    layout_zones = ["split_evidence_left", "center_hero_document", "split_evidence_right", "macro_detail_focus"]

    if metadata is None:
        for meta_candidate in ("metadata.json", "brain_input.json"):
            if (ep_dir / meta_candidate).exists():
                try:
                    with open(ep_dir / meta_candidate, "r", encoding="utf-8") as mf_in:
                        metadata = json.load(mf_in)
                    break
                except Exception as _e_meta:
                    logger.debug("Optional %s load skipped: %s", meta_candidate, _e_meta)

    if grounding_intel is None:
        for gi_candidate in ("grounding_intelligence.json", "grounding_intel.json"):
            if (ep_dir / gi_candidate).exists():
                try:
                    with open(ep_dir / gi_candidate, "r", encoding="utf-8") as gf_in:
                        grounding_intel = json.load(gf_in)
                    break
                except Exception as _e_gi:
                    logger.debug("Optional %s load skipped: %s", gi_candidate, _e_gi)

    if competitor_card is None:
        for cc_candidate in ("competitor_intel_card.json", "competitor_card.json"):
            if (ep_dir / cc_candidate).exists():
                try:
                    with open(ep_dir / cc_candidate, "r", encoding="utf-8") as cf_in:
                        competitor_card = json.load(cf_in)
                    break
                except Exception as _e_cc:
                    logger.debug("Optional %s load skipped: %s", cc_candidate, _e_cc)

    if not story_text:
        for s_candidate in ("story_script.md", "script.md", "story.txt", "spoken_script.txt"):
            if (ep_dir / s_candidate).exists():
                try:
                    story_text = (ep_dir / s_candidate).read_text(encoding="utf-8")
                    break
                except Exception as _e_st:
                    logger.debug("Optional story script load skipped: %s", _e_st)

    meta = metadata or {}
    ep_id = meta.get("episode_id") or ep_dir.name
    mkt = (market or meta.get("market") or ep_id.split("_")[0]).upper()
    gi_topic = grounding_intel.get("topic") if isinstance(grounding_intel, dict) else None
    topic = gi_topic or meta.get("topic") or meta.get("raw_term") or ep_id

    # 1. Trích xuất Dynamic Visual Roster: Ưu tiên nạp trực tiếp từ images/manifest.json nếu đã có tài nguyên phê duyệt
    approved_manifest_path = ep_dir / "images" / "manifest.json"
    if not approved_manifest_path.exists():
        approved_manifest_path = ep_dir / "manifest.json"

    bg_roster, fg_roster = {}, {}
    if approved_manifest_path.exists():
        try:
            with open(approved_manifest_path, "r", encoding="utf-8") as am_f:
                m_items = json.load(am_f)
            if isinstance(m_items, list):
                for item in m_items:
                    rk = item.get("reuse_key") or item.get("name")
                    lt = (item.get("layer_type") or "").lower()
                    if "background" in lt or rk.startswith("bg_"):
                        bg_roster[rk] = {
                            "title": item.get("name", rk),
                            "description": item.get("description", rk),
                            "beats": [1, 2, 3, 4, 5]
                        }
                    else:
                        fg_roster[rk] = {
                            "title": item.get("name", rk),
                            "description": item.get("description", rk),
                            "role": item.get("role", "evidentiary_subject"),
                            "beats": [1, 2, 3, 4, 5],
                            "type": "character" if "char" in rk else "evidence_prop"
                        }
            logger.info("Loaded %d BGs and %d FGs directly from approved manifest: %s", len(bg_roster), len(fg_roster), approved_manifest_path)
        except Exception as ex:
            logger.warning("Failed loading approved manifest %s: %s", approved_manifest_path, ex)

    if not bg_roster or not fg_roster:
        bg_roster, fg_roster = extract_dynamic_visual_roster(
            story_text=story_text or "",
            spoken_sentences=spoken_sentences,
            grounding_intel=grounding_intel,
            competitor_card=competitor_card,
            market=mkt,
            topic=topic
        )
    else:
        if len(spoken_sentences) >= 25 and len(bg_roster) < 46:
            bg_roster = expand_longform_background_roster(
                bg_roster=bg_roster,
                target_count=46,
                market=mkt,
                topic=topic,
            )
        try:
            from app.services.representation_shield import shield_visual_roster
            bg_roster, fg_roster = shield_visual_roster(
                bg_roster=bg_roster,
                fg_roster=fg_roster,
                story_text=story_text or "",
                market=mkt,
            )
        except Exception as _ex_sh:
            logger.warning("Manifest roster shield warning: %s", _ex_sh)

    key_metrics: List[Any] = []
    if isinstance(grounding_intel, dict):
        gt = grounding_intel.get("grounding_table") or []
        if isinstance(gt, list):
            for r in gt:
                if isinstance(r, dict):
                    p = r.get("parameter") or r.get("metric") or ""
                    v = r.get("value") or ""
                    u = r.get("unit") or ""
                    if p or v:
                        key_metrics.append(f"{p}: {v} {u}".strip())
        if not key_metrics and grounding_intel.get("key_figures"):
            key_metrics.extend([str(x) for x in grounding_intel.get("key_figures", [])[:6]])

    scenes = []
    hero_clips = []
    hero_count = 0

    dynamic_hero_indices = set(select_dynamic_hero_indices(spoken_sentences))
    bg_keys = list(bg_roster.keys())
    fg_keys = list(fg_roster.keys())

    # Phân loại Foreground: Nhân vật (character) vs Đạo cụ bằng chứng (evidence prop / document)
    char_fg_keys = [
        k for k in fg_keys
        if fg_roster[k].get("type") == "character"
        or k.startswith("char_") or k.startswith("fg_character_")
        or any(w in k.lower() for w in ["character", "official", "banker", "investigator", "trader", "eyewitness", "minister"])
    ]
    prop_fg_keys = [k for k in fg_keys if k not in char_fg_keys]
    if not prop_fg_keys:
        prop_fg_keys = fg_keys

    char_count = 0
    last_char_scene = -99
    prev_bg_key = None
    distinct_sent_beats = {
        int(val)
        for s in spoken_sentences
        for val in [s.get("beat_phase") or s.get("beat_index")]
        if isinstance(val, (int, str)) and str(val).isdigit()
    }
    sent_beats_degenerate = (len(spoken_sentences) >= 5 and len(distinct_sent_beats) <= 1) or (max(distinct_sent_beats, default=1) > 5)

    for idx, sent in enumerate(spoken_sentences):
        narr = sent.get("text", "")
        dur_frames = int(sent.get("duration_frames") or 150)
        dur_sec = float(sent.get("duration_sec") or ((sent.get("end_ms", 0) - sent.get("start_ms", 0)) / 1000.0 if sent.get("end_ms") else 0.0) or round(dur_frames / 30.0, 3))
        raw_b = sent.get("beat_phase") or (None if sent_beats_degenerate else sent.get("beat_index"))
        if isinstance(raw_b, int) and 1 <= raw_b <= 5 and not sent_beats_degenerate:
            beat_idx = raw_b
        else:
            pct_s = (idx + 1) / max(1, len(spoken_sentences))
            beat_idx = 1 if pct_s <= 0.15 else (2 if pct_s <= 0.35 else (3 if pct_s <= 0.65 else (4 if pct_s <= 0.85 else 5)))

        # Matching Background phù hợp theo Beat và thứ tự cảnh (0 lặp liên tiếp)
        matching_bgs = [k for k, v in bg_roster.items() if beat_idx in v.get("beats", [1, 2, 3, 4, 5])]
        if not matching_bgs:
            matching_bgs = bg_keys
        bg_candidate_idx = idx % len(matching_bgs)
        bg_key = matching_bgs[bg_candidate_idx]
        if bg_key == prev_bg_key and len(matching_bgs) > 1:
            bg_key = matching_bgs[(bg_candidate_idx + 1) % len(matching_bgs)]
        prev_bg_key = bg_key

        # Matching Foreground Evidence dựa trên từ khóa kể chuyện hoặc luân phiên Beat
        narr_lower = narr.lower()
        fg_key = None

        # Kiểm tra khoảnh khắc xuất hiện nhân vật (nhân vật con người xuất hiện có chọn lọc <= 10-12 cảnh)
        is_char_moment = (
            bool(char_fg_keys) and
            (char_count < 10) and
            (idx - last_char_scene >= 12) and
            (any(q in narr for q in ['"', '“', '”', '「', '」']) or
             any(w in narr_lower for w in ["said", "testified", "admitted", "warned", "declared", "tuyên bố", "thừa nhận", "chỉ trích", "phát biểu", "증언", "발언", "発言", "証言"]))
        )

        if is_char_moment:
            matched_char = None
            for ck in char_fg_keys:
                c_info = fg_roster[ck]
                kws = c_info.get("keywords", []) + c_info.get("title", "").lower().split()
                if any(kw in narr_lower for kw in kws if len(kw) > 3):
                    matched_char = ck
                    break
            if not matched_char:
                matched_char = char_fg_keys[char_count % len(char_fg_keys)]
            fg_key = matched_char
            char_count += 1
            last_char_scene = idx
        else:
            # Gán đạo cụ bằng chứng pháp y dựa trên điểm tương đồng từ khóa
            matched_prop = None
            best_score = 0
            for pk in prop_fg_keys:
                p_info = fg_roster[pk]
                p_beats = p_info.get("beats", [1, 2, 3, 4, 5])
                kws = p_info.get("keywords", []) + p_info.get("title", "").lower().split()
                score = sum(1 for kw in kws if len(kw) > 3 and kw in narr_lower)
                if beat_idx in p_beats:
                    score += 1
                if score > best_score:
                    best_score = score
                    matched_prop = pk

            if not matched_prop or best_score <= 1:
                beat_props = [k for k in prop_fg_keys if beat_idx in fg_roster[k].get("beats", [1, 2, 3, 4, 5])] or prop_fg_keys
                matched_prop = beat_props[(idx // 2) % len(beat_props)]
            fg_key = matched_prop

        cam_move = allowed_cameras[idx % len(allowed_cameras)]
        layout_choice = layout_zones[idx % len(layout_zones)]
        transition_choice = "stop_motion_flicker_cut" if idx % 2 == 1 else "hard_cut"

        seed_title = fg_roster[fg_key]["title"] if fg_key else bg_roster[bg_key]["title"]
        setting_desc = bg_roster[bg_key]["title"]

        # Kinetic Sub-Director Plan (Rule 140 / Vox Engine v3)
        sub_plan = {}
        kinetic_i2v_prompt = ""
        try:
            from app.services.kinetic_sub_director import (
                build_natural_kinetic_i2v_prompt,
                generate_scene_sub_director_plan,
            )
            from core.market_resolver import resolve_canonical_market
            from app.services.semantic_evidence_extractor import extract_evidence_for_sentence

            resolved_market = resolve_canonical_market(market_raw=mkt)
            scene_whisper_words = sent.get("words") or sent.get("subtitles") if isinstance(sent, dict) else None
            ev = extract_evidence_for_sentence(narr or seed_title, market=resolved_market, scene_id=f"sc{idx:03d}")

            sub_plan = generate_scene_sub_director_plan(
                scene_id=f"sc{idx:03d}",
                sentence=narr or seed_title,
                hero_cutout_object=seed_title,
                interacting_objects=[ev.interacting_tool_prop],
                duration_sec=dur_sec,
                market=resolved_market,
                whisper_words=scene_whisper_words,
            )
            kinetic_i2v_prompt = build_natural_kinetic_i2v_prompt(sub_plan, market=resolved_market, camera_directive=cam_move)
        except (ValueError, TypeError, KeyError, ImportError) as _k_err:
            logger.warning("[unified_vox_director] Kinetic sub-director notice: %s", _k_err)

        is_hero_video = idx in dynamic_hero_indices
        if is_hero_video:
            flow_slot = FLOW_ACCOUNTS[hero_count % len(FLOW_ACCOUNTS)]
            physics_type, action_type, seed_mode, foleys = determine_spatial_physics(narr, fg_key, hero_count)
            action_desc = get_action_description(action_type, seed_title, narr)
            veo_prompt = format_final_veo_prompt(
                preset,
                subject=seed_title,
                action=action_desc,
                setting=setting_desc,
                camera=cam_move,
                lighting=preset["lighting_defaults"]
            )
            source_img = f"assets/keyframes/hero_sc{idx:03d}_seed.png" if seed_mode == "CUTOUT_ONLY" else f"assets/composite/sc{idx:03d}_composite.png"

            shot_type = "HERO_AI_VIDEO"
            clip_entry = {
                "scene_id": f"sc{idx:03d}",
                "hero_index": hero_count + 1,
                "flow_slot": flow_slot,
                "spatial_physics_type": physics_type,
                "action_type": action_type,
                "seed_asset_mode": seed_mode,
                "source_image": source_img,
                "subject": seed_title,
                "action": action_desc,
                "setting": setting_desc,
                "camera": cam_move,
                "lighting": preset["lighting_defaults"],
                "duration_seconds": dur_sec,
                "duration_sec": dur_sec,
                "transition_out": transition_choice,
                "audio_cue": foleys,
                "text_overlay": None,
                "final_veo_prompt": kinetic_i2v_prompt or veo_prompt,
                "bg_key": bg_key,
                "fg_key": fg_key,
                "prompt": kinetic_i2v_prompt or veo_prompt,
                "scene_sub_director_plan": sub_plan,
                "foleys_audio": foleys,
                "output_filename": f"hero_video_sc{idx:03d}.mp4"
            }
            hero_clips.append(clip_entry)
            hero_count += 1
        else:
            shot_type = "TACTILE_STOP_MOTION_COLLAGE"
            physics_type = "REMOTION_FORENSIC"
            flow_slot = None
            foleys = resolve_semantic_foley(narr, fg_key, idx)
            action_desc = f"{seed_title} evidentiary display in tactile stop-motion"
            veo_prompt = None
            source_img = f"assets/composite/sc{idx:03d}_composite.png"

        has_foreground = (shot_type == "TACTILE_STOP_MOTION_COLLAGE" and idx % 3 != 2)
        assigned_fg = fg_key if has_foreground else None

        # Remotion Stop-Motion Animation Directives
        remotion_instructions = {
            "layout": "FULLSCREEN_AI_VIDEO" if shot_type == "HERO_AI_VIDEO" else "MULTI_LAYER_COLLAGE",
            "camera_drift": cam_move,
            "spatial_physics_type": physics_type,
            "foleys_trigger": foleys,
            "stop_motion": {
                "enabled": (shot_type == "TACTILE_STOP_MOTION_COLLAGE"),
                "stepped_fps": 12,
                "jitter_px": 2,
                "rotation_deg": 1.2 if idx % 2 == 0 else -1.2,
                "entrance": "SNAP_DROP_BOUNCE" if idx % 3 == 0 else "PAPER_SLIDE_IN"
            },
            "overlays": (
                ["RED_YARN_CONNECTOR", "YELLOW_MARKER_STRIKE"] if "docket" in (assigned_fg or "") or "inspection" in (assigned_fg or "") else
                ["RED_STAMP_SLAM", "CASE_STAMP"] if "invoice" in (assigned_fg or "") or "memo" in (assigned_fg or "") or "seal" in (assigned_fg or "") else
                ["COUNTER_ROLLUP"] if "gauge" in (assigned_fg or "") or "ledger" in (assigned_fg or "") else
                []
            )
        }

        fg_side = "left" if ("left" in layout_choice or idx % 2 == 0) else "right"
        scene_obj = {
            "scene_id": f"sc{idx:03d}",
            "source_image": source_img,
            "subject": seed_title,
            "action": action_desc,
            "setting": setting_desc,
            "camera": cam_move,
            "lighting": preset["lighting_defaults"],
            "duration_seconds": dur_sec,
            "duration_frames": dur_frames,
            "duration_sec": dur_sec,
            "audio_cue": foleys,
            "text_overlay": None,
            "transition_out": transition_choice,
            "final_veo_prompt": veo_prompt,
            "beat_index": beat_idx,
            "beat_phase": beat_idx,
            "narration": narr,
            "shot_type": shot_type,
            "spatial_physics_type": physics_type,
            "flow_slot": flow_slot,
            "foleys_audio": foleys,
            "veo_action_prompt": veo_prompt,
            "foregroundPosition": fg_side,
            "heroPosition": {
                "xPct": 34 if fg_side == "left" else 66,
                "yPct": 54,
                "widthPct": 38,
            },
            "background": {
                "reuse_key": bg_key,
                "title": bg_roster[bg_key]["title"],
                "description": bg_roster[bg_key]["description"]
            },
            "foreground": {
                "reuse_key": assigned_fg,
                "title": fg_roster[assigned_fg]["title"] if assigned_fg else None,
                "description": fg_roster[assigned_fg]["description"] if assigned_fg else None,
                "role": fg_roster[assigned_fg]["role"] if assigned_fg else None,
                "position": fg_side
            } if assigned_fg else None,
            "remotion_instructions": remotion_instructions
        }

        # Opus 5.5 Full Cinematography Director Engine (Plan Section III)
        cine_data = generate_cinematography_scene_data(
            idx=idx,
            beat_idx=beat_idx,
            dur_frames=dur_frames,
            assigned_fg=assigned_fg,
            fg_info=fg_roster.get(assigned_fg) if assigned_fg else None,
            bg_key=bg_key,
            layout_choice=layout_choice,
            cam_move=cam_move,
            narr=narr,
            mkt=mkt,
            key_metrics=key_metrics,
            topic=topic
        )
        scene_obj["virtual_camera"] = cine_data["virtual_camera"]
        scene_obj["primary_hero"] = cine_data["primary_hero"]
        scene_obj["motion_path"] = (cine_data["primary_hero"] or {}).get("motion_path")
        scene_obj["linked_secondary_objects"] = cine_data["linked_secondary_objects"]
        if cine_data.get("stat_value"):
            scene_obj["stat_value"] = cine_data["stat_value"]
            scene_obj["stat_label"] = cine_data.get("stat_label")
        if cine_data["headline_info"]:
            scene_obj.update(cine_data["headline_info"])

        # VOX Mixed-Media Paper Collage & Multi-Scene Pacing Layout (Plan Section VI)
        resolved_layout_variant = (
            "paper_collage"
            if (idx == 0 or idx % 6 == 0)
            else (
                "cinematic_doc"
                if idx % 6 in (1, 4)
                else ("kinetic_headline" if idx % 6 == 2 else "evidence_dossier")
            )
        )
        is_collage_mode = (resolved_layout_variant == "paper_collage")
        scene_obj["layoutVariant"] = resolved_layout_variant
        scene_obj["sceneLayoutMode"] = resolved_layout_variant
        from app.services.vox_automated_director import DIORAMA_STYLE_BLOCKS, VOX_PAPER_MATERIALS_LIBRARY
        paper_mat_keys = list(VOX_PAPER_MATERIALS_LIBRARY.keys())
        if paper_mat_keys:
            mat_key = paper_mat_keys[(idx + beat_idx) % len(paper_mat_keys)]
            scene_obj["paper_material"] = dict(VOX_PAPER_MATERIALS_LIBRARY[mat_key])
            scene_obj["paper_material_id"] = mat_key
        diorama_keys = list(DIORAMA_STYLE_BLOCKS.keys())
        if diorama_keys:
            scene_obj["diorama_style_block"] = diorama_keys[idx % len(diorama_keys)]

        paper_theme = "blueprint" if beat_idx in (1, 4) else ("parchment" if beat_idx in (3, 5) else "manila")
        narr_low_sc = narr.lower()
        if any(w in narr_low_sc for w in ["reject", "rejected", "denied", "dismissed", "veto", "却下", "拒否"]):
            stamp_badge_text = f"PLAN REJECTED // BEAT {beat_idx}"
        elif any(w in narr_low_sc for w in ["stay", "stayed", "bankruptcy", "chapter 11", "insolvency", "破産"]):
            stamp_badge_text = f"STAYED // BEAT {beat_idx}"
        elif any(w in narr_low_sc for w in ["confidential", "secret", "redacted", "classified", "極秘", "機密", "未回答"]):
            stamp_badge_text = f"REDACTED // BEAT {beat_idx}"
        elif beat_idx == 1:
            stamp_badge_text = f"CASE FILE // BEAT {beat_idx}"
        elif beat_idx == 2:
            stamp_badge_text = f"ARCHIVAL RECORD // BEAT {beat_idx}"
        elif beat_idx == 3:
            stamp_badge_text = f"FORENSIC AUDIT // BEAT {beat_idx}"
        elif beat_idx == 4:
            stamp_badge_text = f"JUDICIAL RULING // BEAT {beat_idx}"
        else:
            stamp_badge_text = f"SYSTEMIC RECORD // BEAT {beat_idx}"
        scene_obj["papercraft_theme"] = paper_theme
        scene_obj["papercraft_layout"] = {
            "backdrop_theme": paper_theme,
            "has_washi_tape": is_collage_mode,
            "has_brass_pins": is_collage_mode,
            "has_connecting_yarn": bool(is_collage_mode and beat_idx in (3, 4)),
            "yarn_connections": [
                {"from": "evidence_pin", "to": "hero_pin", "curvature": 25, "isYarn": True, "color": "#dc2626"}
            ] if (is_collage_mode and beat_idx in (3, 4)) else [],
            "stamp_badge": {
                "text": stamp_badge_text,
                "rotation": -8 if (idx % 2 == 0) else -14
            } if (is_collage_mode or resolved_layout_variant == "evidence_dossier") else None,
            "has_sticker_cutout": bool(is_collage_mode and assigned_fg),
            "torn_paper": {
                "color": "blueprint_dark" if paper_theme == "blueprint" else ("manila" if paper_theme == "manila" else "ivory"),
                "roughness": "medium",
                "rotation": -1.5 if (idx % 2 == 0) else 1.2,
            }
        }

        # Physical Object Decomposition & Kinematics for Omni Video Effects (Rule 128 & AVF-VOX-001)
        hero_entry = fg_roster.get(assigned_fg) if assigned_fg else None
        hero_title = (hero_entry.get("title") if hero_entry else None) or scene_obj.get("headline") or f"Tactile evidentiary document representing beat {beat_idx}"
        bg_title = (bg_roster.get(bg_key) or {}).get("title") or "Aged Cream Newsprint Desk #F4F1EA"
        sc_headline = scene_obj.get("headline") or f"BEAT {beat_idx:02d}"

        scene_obj["objects"] = [
            {
                "id": f"o{idx+1}_1",
                "name": hero_title,
                "attributes": ["tactile paper cutout", "2-4px deckle edge", "soft drop shadow"],
                "role": "primary"
            },
            {
                "id": f"o{idx+1}_2",
                "name": "crimson forensic seal and brass anchor pin",
                "attributes": ["crimson wax imprint", "brass patina pin"],
                "role": "secondary"
            },
            {
                "id": f"o{idx+1}_3",
                "name": bg_title,
                "attributes": ["#F4F1EA", "vintage print halftone grid", "creased archival paper"],
                "role": "backdrop"
            }
        ]

        scene_obj["actions"] = [
            {
                "subject": f"o{idx+1}_1",
                "verb": "slides_in",
                "target": "center_stage",
                "motion": "smooth_slide_left_to_right" if fg_side == "left" else "smooth_slide_right_to_left",
                "intensity": "low",
                "role": "primary"
            },
            {
                "subject": f"o{idx+1}_2",
                "verb": "stamps",
                "target": f"o{idx+1}_1",
                "motion": "downward_impact",
                "intensity": "high",
                "role": "secondary"
            }
        ]

        scene_obj["scene_sub_director_plan"] = sub_plan
        fallback_prompt = (
            f"[CAMERA & ENVIRONMENT]: {cam_move} on Aged Cream Paper #F4F1EA desk.\n"
            f"[ACTION PHASE (0.2s - 0.4s)]: The tactile investigative tool interacts with {hero_title}.\n"
            f"[PHYSICAL REACTION & RESIDUE]: Planar cutout anchors firmly into composition, leaving subtle tactile imprint.\n"
            f"[HOLD & LIVING TEXTURE]: All objects hold firmly in place with subtle living paper grain flutter and micro shadow breathing at 12fps (on twos). Zero 3D camera drift, zero static freeze."
        )
        scene_obj["flow_video_prompt"] = kinetic_i2v_prompt or fallback_prompt
        scene_obj["i2v_prompt_omni"] = kinetic_i2v_prompt or fallback_prompt
        scene_obj["i2v_prompt_google_flow"] = kinetic_i2v_prompt or fallback_prompt

        scenes.append(scene_obj)

    # 1.5. Compile Stateful Investigation Boards (3-4 scenes per Board, capping hard_cut <= 15%)
    stateful_boards = compile_stateful_boards(scenes, board_size=4)

    # 2. Tự động sinh và ghi file flow_video_manifest.json & vox_scene_manifest.json
    manifest_data = {
        "episode_id": ep_id,
        "total_clips": len(hero_clips),
        "clips": hero_clips
    }

    vox_manifest_data = {
        "episode_id": ep_id,
        "market": mkt,
        "topic": topic,
        "total_scenes": len(scenes),
        "total_boards": len(stateful_boards),
        "scenes": [
            {
                "scene_id": sc["scene_id"],
                "beat": f"Beat {sc['beat_index']}",
                "narrative_motif": (
                    "Cold Strike Shockwave" if sc['beat_index'] == 1 else
                    "Architecture of Deception" if sc['beat_index'] == 2 else
                    "Forensic Paper Trail" if sc['beat_index'] == 3 else
                    "Smoking Gun Climax" if sc['beat_index'] == 4 else
                    "Systemic Warning & Reckoning"
                ),
                "durationInFrames": sc["duration_frames"],
                "virtual_camera": sc.get("virtual_camera"),
                "background": {
                    "src": f"pulled/{sc['background']['reuse_key']}.png",
                    "reuse_key": sc['background']['reuse_key'],
                    "motion_path": [
                        {"frame": 0, "x_pct": 50, "y_pct": 50, "scale": 1.0, "rot_deg": 0},
                        {"frame": sc["duration_frames"], "x_pct": 50, "y_pct": 52, "scale": 1.05, "rot_deg": 0.25 if sc.get("scene_id", "").endswith(("0", "2", "4", "6", "8")) else -0.25}
                    ]
                },
                "primary_hero": sc.get("primary_hero"),
                "linked_secondary_objects": sc.get("linked_secondary_objects", []),
                "headline": sc.get("headline"),
                "highlight_word": sc.get("highlight_word"),
                "category": sc.get("category"),
                "subtext": sc.get("subtext"),
                "accent_color": sc.get("accent_color"),
                "scene_sub_director_plan": sc.get("scene_sub_director_plan"),
                "flow_video_prompt": sc.get("flow_video_prompt") or sc.get("i2v_prompt_google_flow"),
            }
            for sc in scenes
        ]
    }

    # Ghi vào ep_dir và /var/vf/episodes/<ep_id> nếu có
    target_dirs = [ep_dir]
    var_ep_dir = Path(f"/var/vf/episodes/{ep_id}")
    if var_ep_dir.exists() and var_ep_dir not in target_dirs:
        target_dirs.append(var_ep_dir)

    for td in target_dirs:
        try:
            td.mkdir(parents=True, exist_ok=True)
            with open(td / "flow_video_manifest.json", "w", encoding="utf-8") as mf:
                json.dump(manifest_data, mf, indent=2, ensure_ascii=False)
            with open(td / "vox_scene_manifest.json", "w", encoding="utf-8") as vf:
                json.dump(vox_manifest_data, vf, indent=2, ensure_ascii=False)
        except Exception as ex:
            logger.warning("Failed writing flow/vox manifests to %s: %s", td, ex)

    # 3. Tự động sinh và lưu file showrunner_dossier.json (Khế ước Điều Phối Toàn Trình Opus 5.5)
    dossier_scenes = []
    for sc in scenes:
        fg_info = sc.get("foreground")
        is_char = bool(fg_info and fg_info.get("role"))
        dossier_scenes.append({
            "scene_id": sc.get("scene_id"),
            "beat_index": sc.get("beat_index"),
            "narration": sc.get("narration"),
            "visual_archetype": "character" if is_char else ("evidence_prop" if fg_info else "macro_environment"),
            "camera_movement": sc.get("camera"),
            "transition": sc.get("transition_out"),
            "motion_directive": sc.get("remotion_instructions", {}).get("motion_directive", "dramatic_push"),
            "assigned_bg": sc.get("background", {}).get("reuse_key"),
            "assigned_fg": fg_info.get("reuse_key") if fg_info else None,
            "acceptance_criteria": {
                "no_blank_stare": is_char,
                "dynamic_pose": is_char,
                "style_conformance": "stylized_graphic_novel_editorial_illustration",
                "chroma_key": "#FF00FF",
                "max_bleed_ratio": 0.0005,
                "paper_texture": not is_char
            }
        })

    showrunner_dossier = {
        "showrunner_model": "claude-opus-5-5",
        "episode_id": ep_id,
        "market": mkt,
        "topic": topic,
        "vision_statement": f"Master Vox Docudrama Directorial Blueprint for {ep_id} ({mkt}) under Claude Opus 5.5 Showrunner Governance.",
        "total_scenes": len(scenes),
        "total_hero_clips": len(hero_clips),
        "total_backgrounds": len(bg_roster),
        "total_foregrounds": len(fg_roster),
        "scenes": dossier_scenes,
        "background_roster": bg_roster,
        "foreground_roster": fg_roster,
        "b5_audit_criteria": {
            "max_magenta_bleed_pct": 0.05,
            "zero_ui_artifacts": True,
            "non_photorealistic_graphic_novel": True,
            "ethnic_context_lock": mkt,
            "dynamic_character_posing": True
        }
    }

    for td in target_dirs:
        try:
            td.mkdir(parents=True, exist_ok=True)
            with open(td / "showrunner_dossier.json", "w", encoding="utf-8") as sf:
                json.dump(showrunner_dossier, sf, indent=2, ensure_ascii=False)
        except Exception as ex:
            logger.warning("Failed writing showrunner_dossier.json to %s: %s", td, ex)

    # Validate director SFX compliance prior to return (Fail-Fast Gate)
    validate_director_sfx_compliance(scenes, hero_clips)

    return {
        "scenes": scenes,
        "hero_clips": hero_clips,
        "background_roster": bg_roster,
        "foreground_roster": fg_roster,
        "showrunner_dossier": showrunner_dossier
    }


def main():
    parser = argparse.ArgumentParser(description="Unified VOX Director Engine (B3 + B3.5)")
    parser.add_argument("--episode", default=None, help="Episode ID (e.g. <MARKET>_EP<XXXX>_<slug>)")
    parser.add_argument("--ep-dir", default=None, help="Explicit path to episode folder")
    parser.add_argument("--style-preset", default="vox_forensic_paper", help="Style preset from style-config.yaml")
    args = parser.parse_args()

    ep_id = args.episode
    if not ep_id:
        pending_dir = Path("/var/vf/pending_tasks")
        if pending_dir.exists():
            tasks = [f.stem for f in pending_dir.glob("*.json")]
            if tasks:
                ep_id = tasks[0]
        if not ep_id:
            episodes_dir = Path("/var/vf/episodes")
            if episodes_dir.exists():
                active = [d.name for d in episodes_dir.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
                if active:
                    ep_id = sorted(active)[-1]
        if not ep_id:
            parser.error("Episode ID is required via --episode")

    if args.ep_dir:
        ep_dir = Path(args.ep_dir)
    else:
        vps_ep_dir = Path(f"/var/vf/episodes/{ep_id}")
        local_ep_dir = ROOT_DIR / "episodes" / ep_id
        ep_dir = vps_ep_dir if vps_ep_dir.exists() else local_ep_dir

    print(f"🚀 Chạy Unified VOX Spatial Physics Director cho {ep_id} tại {ep_dir}...")
    ep_dir.mkdir(parents=True, exist_ok=True)

    spoken_file = ep_dir / "spoken_sentences.json"
    if spoken_file.exists():
        with open(spoken_file, "r", encoding="utf-8") as f:
            spoken_sentences = json.load(f)
    elif (ep_dir / "director_plan.json").exists():
        print("💡 Nạp danh sách câu thoại từ director_plan.json hiện có...")
        with open(ep_dir / "director_plan.json", "r", encoding="utf-8") as f:
            dp = json.load(f)
            spoken_sentences = [
                {
                    "text": s.get("narration", ""),
                    "duration_frames": s.get("duration_frames", 150),
                    "duration_sec": s.get("duration_sec", 5.0),
                    "beat_index": s.get("beat_index", 1)
                }
                for s in dp.get("scenes", [])
            ]
    else:
        print(f"❌ Không tìm thấy dữ liệu kịch bản tại {ep_dir}")
        sys.exit(1)

    result = build_unified_director_plan(spoken_sentences, ep_dir, style_preset=args.style_preset)
    scenes = result["scenes"]
    hero_clips = result["hero_clips"]
    bg_roster = result.get("background_roster", {})
    fg_roster = result.get("foreground_roster", {})

    # 1. Sanitize & Forge Prompts (B3.5)
    from app.services.prompt_forge import UNIVERSAL_VOX_ANIMATION_PROMPT, _synthesize_vox_collage_prompt
    mkt = ep_id.split("_")[0].upper() if ep_id and "_" in ep_id else "EN"
    bg_prompts = {k: _sanitize_background_prompt(v["description"], bg_key=k, market=mkt) for k, v in bg_roster.items()}
    fg_prompts = {k: _sanitize_foreground_prompt(v["description"], fg_key=k, market=mkt) for k, v in fg_roster.items()}
    vox_collages = {}
    animation_tiers = {}
    for idx, sc in enumerate(scenes):
        bg_k = (sc.get("background") or {}).get("reuse_key") or sc.get("background_reuse_key") or sc.get("bg_reuse_key") or "bg_00"
        fg_k = (sc.get("foreground") or {}).get("reuse_key") or sc.get("foreground_reuse_key") or sc.get("fg_reuse_key")
        bg_desc = bg_prompts.get(bg_k, "")
        fg_desc = fg_prompts.get(fg_k, "") if fg_k else ""
        if bg_desc:
            sc["bg_prompt"] = bg_desc
            sc["image_prompt"] = bg_desc
            if isinstance(sc.get("background"), dict):
                sc["background"]["description"] = bg_desc
        if fg_desc:
            sc["fg_prompt"] = fg_desc
            sc["foreground_prompt"] = fg_desc
            if isinstance(sc.get("foreground"), dict):
                sc["foreground"]["description"] = fg_desc
        vox_key = f"vox_sc_{idx+1:03d}_{bg_k}"
        vox_collages[vox_key] = _synthesize_vox_collage_prompt(
            bg_desc=bg_desc,
            fg_desc=fg_desc,
            object_focus=sc.get("object_focus"),
            market=mkt,
            scene_idx=idx+1
        )
        animation_tiers[vox_key] = sc.get("animation_tier") or ("HERO_AI_VIDEO_6S" if sc.get("is_hero_video") or sc.get("shot_type") == "HERO_AI_VIDEO" else "TACTILE_STOPMOTION_STILL")

    # 2. Lưu director_plan.json & dp_plan.json
    dp_data = {
        "episode_id": ep_id,
        "total_scenes": len(scenes),
        "total_hero_ai_videos": len(hero_clips),
        "hero_clips": hero_clips,
        "background_roster": bg_roster,
        "foreground_roster": fg_roster,
        "scenes": scenes
    }
    dp_path = ep_dir / "director_plan.json"
    with open(dp_path, "w", encoding="utf-8") as f:
        json.dump(dp_data, f, indent=2, ensure_ascii=False)
    with open(ep_dir / "dp_plan.json", "w", encoding="utf-8") as f:
        json.dump({"episode_id": ep_id, "scenes": scenes}, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã tạo director_plan.json & dp_plan.json ({len(scenes)} cảnh, {len(hero_clips)} Veo 3D clips) -> {dp_path}")

    # 3. Lưu prompts_forge.json & prompts.json
    prompts_data = {
        "episode_id": ep_id,
        "backgrounds": bg_prompts,
        "foregrounds": fg_prompts,
        "vox_collages": vox_collages,
        "animation_tiers": animation_tiers,
        "universal_video_prompt": UNIVERSAL_VOX_ANIMATION_PROMPT,
        "omni_i2v_prompts": {f"sc_{idx+1:03d}": sc.get("i2v_prompt_omni") for idx, sc in enumerate(scenes)},
        "flow_i2v_prompts": {f"sc_{idx+1:03d}": sc.get("i2v_prompt_google_flow") for idx, sc in enumerate(scenes)},
        "thumbnails": {}
    }
    pf_path = ep_dir / "prompts_forge.json"
    with open(pf_path, "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)
    with open(ep_dir / "prompts.json", "w", encoding="utf-8") as f:
        json.dump(prompts_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Đã tạo prompts_forge.json ({len(bg_prompts)} BGs, {len(fg_prompts)} FGs, {len(vox_collages)} VOX Collages) -> {pf_path}")

    # 4. flow_video_manifest.json đã được tự động lưu trong build_unified_director_plan()
    man_path = ep_dir / "flow_video_manifest.json"
    print(f"✅ Đã tạo flow_video_manifest.json ({len(hero_clips)} clips phân bổ {len(FLOW_ACCOUNTS)} tài khoản) -> {man_path}")

    # 4. showrunner_dossier.json + Active Opus 5.5 In-Flight Gate
    dos_path = ep_dir / "showrunner_dossier.json"
    try:
        from scripts.orchestrator.opus55_supervisor_gate import audit_director_assets_in_flight
        gate_res = audit_director_assets_in_flight(ep_dir, call_llm_audit=False)
        print(f"🛡️ [Opus 5.5 In-Flight Gate] Verdict: {gate_res['verdict']} (Score: {gate_res['score']}, Defects: {gate_res['defects_count']}) -> {dos_path}")
        if gate_res["defects"]:
            for d_msg in gate_res["defects"][:5]:
                print(f"   ⚠️ Defect: {d_msg}")
    except Exception as ex_gate:
        logger.warning("Opus 5.5 In-Flight Gate check skipped: %s", ex_gate)
    print(f"✅ Đã tạo showrunner_dossier.json (Opus 5.5 Showrunner Governance) -> {dos_path}")

    print("\n" + "=" * 70)
    print(f"📊 BẢO CHỨNG PHÂN BỔ {len(hero_clips)} CLIPS VEO CHO {len(FLOW_ACCOUNTS)} TÀI KHOẢN GOOGLE FLOW:")
    print("=" * 70)
    acc_distribution = {}
    for c in hero_clips:
        slot = c["flow_slot"]
        acc_distribution[slot] = acc_distribution.get(slot, 0) + 1
    for slot, count in sorted(acc_distribution.items()):
        print(f"• {slot}: {count} clips")


if __name__ == "__main__":
    main()
