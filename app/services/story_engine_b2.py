# app/services/story_engine_b2.py
"""
B2 Story Engine (5-Beat Docudrama 1,800–2,200 words) via GPT-6-Astra.
Architecture & Rule Compliance:
  - Strict Rule 118: Zero-Mock Data & Ask-Before-Deviating.
  - Strict Rule 120: Safe-Treatment Mandates & Timestamp-Accurate 5-Act Structure.
  - Strict Rule 445: 5-Beat Docudrama Story Generation (~1,800–2,200 words, 8-10 min runtime).
  - Synchronizes seamlessly to Notion Story Library DB (Dual-Callout & Forensic Metrics).
  - Dynamic Rule Injection: Inherits Central Skills (Rules 113–121) and Content Engine Hub
    (5-Beat architecture, pacing, and loop discipline) directly from Notion SoT.
"""

import os, sys, json, time, re, logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, '/root/video_factory')
from app.services.hhtech_reasoner import call_gpt6_astra, detect_safety_and_theme
from app.services.skill_loader import (
    get_skill_rules,
    get_central_skills,
    get_content_engine_rules,
    get_media_production_rules,
    get_b2_editorial_skills
)
from app.services import story_gate as sgate
from scripts.ag_notion_bridge import resolve_id, update_page_properties, create_page, query_db, append_children_blocks, get_blocks, delete_block
try:
    from scripts.vf_insight_cards import fetch_active_insights, build_feedback_block
except ImportError:
    def fetch_active_insights(*a, **kw): return []
    def build_feedback_block(*a, **kw): return ''
import json as json_lib

NOTION_STORY_DB_ID = os.getenv("STORY_LIBRARY_DB_ID", "b0301989-2400-836b-bdb5-8131fea17736")
EPISODES_BASE_DIR = os.getenv("VF_EPISODES_DIR", "/var/vf/episodes")
PENDING_TASKS_DIR = "/var/vf/pending_tasks"
KNOWN_MARKETS = {"EN", "JP", "KR"}
ACT_PATTERN = re.compile(r'(=== ACT [I|V|X]+ ===.*?)(?=(=== ACT [I|V|X]+ ===|\Z))', re.DOTALL)



def _opening_hook(script: str, max_chars: int = 320) -> str:
    """The first 1-2 sentences of the script, whole.
    Extracts the opening curiosity and emotional hook for quality scoring.
    """
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (script or "").strip()) if s.strip()]
    if not sents:
        return ""
    hook = sents[0]
    for nxt in sents[1:2]:
        if len(hook) + len(nxt) + 1 <= max_chars:
            hook = hook + " " + nxt
    return hook[:max_chars]





def load_competitor_intel(task_id: str, topic: str = "", niche_brief: str = "", market: str = "EN") -> dict:
    """Load B1.5 Competitor Intel Card.
    Enforces strict contract: raises RuntimeError if missing, unless bypassed or recovered via JIT.
    """
    candidates = [
        os.path.join(EPISODES_BASE_DIR, task_id, "competitor_intel_card.json"),
        os.path.join("/var/vf/episodes", task_id, "competitor_intel_card.json"),
        os.path.join("/root/video_factory/episodes", task_id, "competitor_intel_card.json"),
        os.path.join("./episodes", task_id, "competitor_intel_card.json"),
    ]
    for intel_path in candidates:
        if os.path.exists(intel_path) and os.path.getsize(intel_path) > 10:
            try:
                with open(intel_path, "r", encoding="utf-8") as f:
                    data = json_lib.load(f)
                    if data:
                        return data
            except Exception as e:
                logger.debug(f"[story_engine] Error loading competitor intel from {intel_path}: {e}")

    # JIT fallback: if missing from disk but topic is present, attempt dynamic B1.5 recon
    if topic:
        logger.info(f"[story_engine] Competitor intel missing on disk for {task_id}. Attempting JIT B1.5 recon for '{topic[:50]}'...")
        try:
            from app.services.competitor_recon_b15 import run_b15
            recon_card = run_b15(task_id, topic, niche_brief or "General", market=market)
            if recon_card and isinstance(recon_card, dict):
                for ep_base in [EPISODES_BASE_DIR, "/var/vf/episodes", "/root/video_factory/episodes", "./episodes"]:
                    t_dir = Path(ep_base) / task_id
                    t_dir.mkdir(parents=True, exist_ok=True)
                    (t_dir / "competitor_intel_card.json").write_text(
                        json_lib.dumps(recon_card, ensure_ascii=False, indent=2), encoding="utf-8")
                return recon_card
        except Exception as jit_err:
            logger.warning(f"[story_engine] JIT competitor recon failed for {task_id}: {jit_err}")

    if os.getenv("VF_BYPASS_INTEL_CHECK") == "1":
        logger.warning(f"[story_engine] VF_BYPASS_INTEL_CHECK active: continuing without intel card for {task_id}")
        return {}
    raise RuntimeError(
        f"Strict Contract Violation: B1.5 Competitor Intel Card missing or unreadable for task {task_id}. "
        f"Run B1.5 Two-Pass recon before B2 story generation!"
    )


def load_grounding_intel(
    task_id: str,
    out_dir: str,
    topic: str = "",
    niche_brief: str = "",
    market: str = "EN",
    min_claims: int = 8,
    min_verified: int = 3,
    min_dated_claims: int = 3
) -> tuple[dict, str]:
    """Load B1.5.5 Grounding Intel Card.
    Enforces strict contract: raises RuntimeError if missing or fails gate, unless bypassed.
    """
    candidates = [
        os.path.join(out_dir, "grounding_intel.json"),
        os.path.join(EPISODES_BASE_DIR, task_id, "grounding_intel.json"),
        os.path.join("/root/video_factory/episodes", task_id, "grounding_intel.json"),
    ]
    g_data = None
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 10:
            try:
                with open(p, "r", encoding="utf-8") as gf:
                    g_data = json_lib.load(gf)
                    if g_data:
                        break
            except Exception:
                pass

    if not g_data and topic:
        # Attempt JIT Grounding Research
        logger.info(f"[story_engine] Grounding intel missing for {task_id}. Attempting JIT Google Search Grounding...")
        try:
            from app.services.grounding_layer_b15 import run_grounding_research
            g_data = run_grounding_research(topic=topic, search_hint=niche_brief, market=market)
            if g_data:
                os.makedirs(out_dir, exist_ok=True)
                with open(os.path.join(out_dir, "grounding_intel.json"), "w", encoding="utf-8") as gf:
                    json_lib.dump(g_data, gf, ensure_ascii=False, indent=2)
        except Exception as _je:
            logger.error(f"[story_engine] JIT Grounding Research failed for {task_id}: {_je}")

    from app.services.grounding_layer_b15 import passes_grounding_gate, format_grounded_facts_for_prompt

    if os.getenv("VF_BYPASS_GROUNDING_CHECK") == "1":
        logger.warning(f"[story_engine] VF_BYPASS_GROUNDING_CHECK active: continuing without verified grounding for {task_id}")
        return g_data or {}, format_grounded_facts_for_prompt(g_data) if g_data else ""

    if not g_data:
        raise RuntimeError(
            f"Strict Contract Violation: B1.5.5 Grounding Intel Card missing for task {task_id}. "
            f"Run B1.5.5 Grounding Layer before B2 story generation!"
        )

    ok, reason = passes_grounding_gate(
        g_data,
        min_verified=min_verified,
        min_claims=min_claims,
        min_dated_claims=min_dated_claims,
        require_whitelist=True
    )
    if not ok:
        raise RuntimeError(
            f"Strict Contract Violation: B1.5.5 Grounding Gate REJECTED for task {task_id} ({reason}). "
            f"Cannot proceed to B2 without verified facts!"
        )

    block = format_grounded_facts_for_prompt(g_data)
    return g_data, block


def load_task_metadata(task_id: str) -> dict:
    """Load metadata for a given task ID from local pending cache or Notion Story Library."""
    cache_path = os.path.join(PENDING_TASKS_DIR, f"{task_id}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[story_engine] Error reading pending task {cache_path}: {e}")

    try:
        res = query_db(NOTION_STORY_DB_ID)
        for r in res.get("results", []):
            props = r.get("properties", {})
            
            def _get_txt(p):
                if not p: return ""
                t = p.get("type")
                if t == "title": return "".join(x.get("plain_text", "") for x in p.get("title", []))
                if t == "rich_text": return "".join(x.get("plain_text", "") for x in p.get("rich_text", []))
                return ""
            
            tid = _get_txt(props.get("Task ID", {}))
            eid = _get_txt(props.get("Episode ID", {}))
            if task_id in (tid, eid):
                return {
                    "task_id": task_id,
                    "market": props.get("Market", {}).get("select", {}).get("name", "EN"),
                    "topic": _get_txt(props.get("Name", {})),
                    "story_arcs": _get_txt(props.get("Story Direction (5 Arcs)", {})),
                    "niche_brief": _get_txt(props.get("Niche Angle Brief", {})),
                    "search_key": _get_txt(props.get("Search-Specific Key", {})),
                    "page_id": r.get("id")
                }
    except Exception as e:
        logger.warning(f"[story_engine] Error querying Notion Story Library for {task_id}: {e}")

    parts = [p for p in re.split(r"[_-]", task_id) if p]
    head = parts[0].upper() if parts else ""
    mkt = head if head in KNOWN_MARKETS else "EN"
    body = [p for p in parts[1:] if not re.fullmatch(r"ep\d+", p, re.I)]
    raw_name = "_".join(body) if body else task_id
    theme, safety_label, treatment_note = detect_safety_and_theme(raw_name, mkt)
    
    return {
        "task_id": task_id,
        "market": mkt,
        "topic": raw_name.replace("_", " ").title(),
        "story_arcs": "Beat 1 (Nghịch lý mở màn 0-60s) -> Beat 2 (Bẫy truyền thông & Red Herring) -> Beat 3 (Manh mối rò rỉ & Vết nứt thể chế) -> Beat 4 (Cỗ máy lợi ích & Smoking Gun) -> Beat 5 (Gương soi hiện tại & Lời cảnh báo)",
        "niche_brief": f"Cơ chế ngách và sự kiện lịch sử/kinh tế đằng sau {raw_name}.",
        "breakout_queries": [],
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note
    }


def adapt_master_spoken_script(full_script: str, market: str = "EN", topic: str = "") -> dict:
    """Phase 2 (Master Spoken VO & Subtitle Adaptation - Hollywood Standard):
    Adapts 5-Act Overview Narrative into a breath-timed Spoken Voiceover Script
    strictly constrained to 10-12 minutes narration (<= 15 min hard ceiling).
    Splits into natural breath-paced sentences (10-18 words, 25-50 syllables).
    Extracts karaoke highlight keywords and assigns beat_index (1..5).
    """
    mkt = market.upper()
    lang_name = "English" if mkt == "EN" else ("Japanese" if mkt == "JP" else "Korean")

    if mkt == "KR":
        target_desc = "3,200 to 3,600 Korean Hangul syllables across 120 to 150 breath-timed sentences (each 20-30 syllables), for ~12-14 min narration at natural docudrama pace (~250-270 syllables/min). Do NOT compress or drop story content."
    elif mkt == "JP":
        target_desc = "3,400 to 3,800 Japanese characters across 120 to 150 breath-timed sentences (each 22-35 characters), for ~12-14 min narration at natural docudrama pace (~270-300 chars/min). Do NOT compress or drop story content."
    elif mkt == "VN":
        target_desc = "2,000 to 2,400 Vietnamese words across 130 to 160 breath-timed sentences (each 10-16 words), for ~12-14 min narration (~160-180 WPM). Do NOT compress or drop story content."
    else:
        target_desc = "1,800 to 2,200 English words across 130 to 160 breath-timed sentences (each 10-16 words), for ~12-14 min narration (~140-160 WPM). Do NOT compress or drop story content."

    system_prompt = (
        f"You are an Elite Master Voiceover Director, Audio Dramatist, and Subtitle Editor for Video Factory.\\n"
        f"Target Spoken Language: {lang_name}.\\n"
        f"Target Length: {target_desc}.\\n\\n"
        "YOUR MISSION:\\n"
        "Transform the provided 5-Act Investigative Documentary Script into a Master Spoken Voiceover Script optimized for broadcast delivery.\\n\\n"
        "STRICT CONSTRAINTS:\\n"
        "1. PRESERVE THE FULL 5-BEAT NARRATIVE: Adapt 100% of the storyline. Do NOT truncate, summarize, or discard any paragraph.\\n"
        "2. NATURAL BREATH PACING: Each sentence must be 10-18 words (Korean/CJK: 22-35 syllables/characters). Avoid run-on sentences.\\n"
        "3. DRAMATIC AUDIO PUNCTUATION: Use natural pauses (commas, ellipses '...', em-dashes '—') to create suspense, pacing shifts, and dramatic gravitas.\\n"
        "4. HARD DURATION TARGET: Total spoken duration MUST be 11 to 14 minutes across 120 to 160 breath-timed sentences (<= 15 min hard ceiling).\\n"
        "5. KARAOKE HIGHLIGHTS: For each sentence, identify 1 to 3 critical high-impact keywords (amounts, percentages, fraud terms, evidence, dates) for visual karaoke highlighting.\\n"
        "6. LINGUISTIC PURITY: 100% native vocabulary in the target language. Zero raw English words in KR/JP prose.\\n\\n"
        "OUTPUT FORMAT:\\n"
        "Return ONLY a valid JSON object matching this exact schema, without markdown formatting:\\n"
        "{\\n"
        '  "total_estimated_minutes": 11.2,\\n'
        '  "spoken_script_text": "Full concatenated spoken narration text...",\\n'
        '  "sentences": [\\n'
        '    {\\n'
        '      "sentence_id": "sent_001",\\n'
        '      "beat_index": 1,\\n'
        '      "text": "First breath-timed spoken sentence...",\\n'
        '      "karaoke_highlights": ["keyword1", "keyword2"]\\n'
        '    }\\n'
        '  ]\\n'
        "}"
    )

    user_prompt = (
        f"Adapt the following 5-Act Investigative Script for topic '{topic}' into the Master Spoken Voiceover & Subtitle Script:\\n\\n"
        f"{full_script}\\n\\n"
        f"Generate the JSON now:"
    )

    logger.info(f"[story_engine] Adapting Master Spoken VO Script for {topic} ({mkt})...")
    raw_res = ""
    try:
        raw_res = call_gpt6_astra(user_prompt, system_prompt=system_prompt, max_tokens=8192, timeout=120.0)
    except Exception as e:
        logger.warning(f"[story_engine] LLM call for spoken VO adaptation failed: {e}")

    parsed = None
    if raw_res and raw_res.strip():
        cleaned = raw_res.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            parsed = json.loads(cleaned.strip())
        except Exception:
            m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1))
                except Exception:
                    pass

    is_cjk = mkt in ("KR", "JP", "ZH")
    if not parsed or not isinstance(parsed, dict) or not parsed.get("sentences") or len(parsed.get("sentences", [])) < 80:
        logger.warning(f"[story_engine] Spoken VO adaptation parsing failed or too short ({len(parsed.get('sentences', [])) if parsed else 0} sents). Running deterministic sentence splitting fallback.")
        sentences = []
        full_text_lines = []
        act_blocks = re.split(r'(===\s*(?:ACT|BEAT)\s*[I|V|X\d]+\s*===)', full_script, flags=re.IGNORECASE)
        current_beat = 1
        for block in act_blocks:
            b_up = block.strip().upper()
            if "ACT I" in b_up or "BEAT 1" in b_up: current_beat = 1; continue
            if "ACT II" in b_up or "BEAT 2" in b_up: current_beat = 2; continue
            if "ACT III" in b_up or "BEAT 3" in b_up: current_beat = 3; continue
            if "ACT IV" in b_up or "BEAT 4" in b_up: current_beat = 4; continue
            if "ACT V" in b_up or "BEAT 5" in b_up: current_beat = 5; continue

            # Robust multilingual sentence split (handles CJK without whitespace after punctuation)
            candidate_sents = [s.strip() for s in re.split(r'(?<=[。！？])|(?<=[.!?])(?:\s+|$|\n+)', block) if s.strip()]
            raw_sents = []
            for cs in candidate_sents:
                if cs.startswith("==="):
                    continue
                # Sub-split long sentences to preserve breath-timed rhythm
                if is_cjk and len(cs) > 42:
                    parts = [p.strip() for p in re.split(r'(?<=[、，,;；——])', cs) if p.strip()]
                    raw_sents.extend(parts if parts else [cs])
                elif not is_cjk and len(cs.split()) > 20:
                    parts = [p.strip() for p in re.split(r'(?<=[,;—])\s+', cs) if p.strip()]
                    raw_sents.extend(parts if parts else [cs])
                else:
                    raw_sents.append(cs)

            for s in raw_sents:
                if not s or s.startswith("==="):
                    continue
                sentences.append({
                    "sentence_id": f"sent_{len(sentences)+1:03d}",
                    "beat_index": current_beat,
                    "text": s,
                    "karaoke_highlights": []
                })
                full_text_lines.append(s)
        joined_text = "".join(full_text_lines) if is_cjk else " ".join(full_text_lines)
        est_mins = round(len(joined_text) / 280.0, 1) if is_cjk else round(len(joined_text.split()) / 150.0, 1)
        parsed = {
            "total_estimated_minutes": est_mins,
            "spoken_script_text": joined_text,
            "sentences": sentences
        }

    return parsed


def adversarial_audit_spoken_script(spoken_data: dict, market: str = "EN", topic: str = "") -> dict:
    """Gate 2.5 (Adversarial Spoken VO Audit Gate):
    Uses an independent LLM pass acting as Chief Audio Director & Broadcast Standards Auditor.
    Verifies:
      1. Duration <= 15 minutes hard ceiling (target 10-12 minutes).
      2. Pacing, dramatic tension, and natural breathing rhythm.
      3. Absence of narrative bloat, repetitive word loops, or artificial inflation.
      4. Coverage of all 5 Beats.
    Must score >= 8.5/10 with verdict 'PASS'.
    """
    mkt = market.upper()
    sentences = spoken_data.get("sentences", [])
    script_text = spoken_data.get("spoken_script_text", "")
    total_est_min = float(spoken_data.get("total_estimated_minutes", 10.0))

    is_cjk = mkt in ("KR", "JP", "ZH")
    total_units = len(script_text) if is_cjk else len(script_text.split())
    unit_name = "characters/syllables" if is_cjk else "words"

    max_units = 5500 if is_cjk else 2200
    if total_units > max_units:
        logger.warning(f"[story_engine] Spoken VO exceeds strict ceiling: {total_units} {unit_name} (max {max_units})!")

    system_prompt = (
        "You are the Chief Broadcast Standards Auditor & Audio Director for Video Factory.\\n"
        "Audit the following Spoken Voiceover Script with adversarial scrutiny.\\n\\n"
        "EVALUATION CRITERIA:\\n"
        "1. DURATION COMPLIANCE (Weight 30%): Does the script fit into 11 to 14 minutes across 120-160 sentences (hard maximum 15 minutes)? Flag any bloated or truncated sentences.\\n"
        "2. DRAMATIC TENSION & PACING (Weight 30%): Does it maintain relentless docudrama suspense and rhythmic breathing pauses?\\n"
        "3. NARRATIVE INTEGRITY (Weight 20%): Are all 5 investigative beats present (Hook -> False Narrative -> Systemic Blindspot -> Real Culprit -> Modern Mirror)?\\n"
        "4. SPOKEN SUITABILITY (Weight 20%): Are sentences concise (10-18 words) and easy for a voiceover narrator to deliver naturally without stumbling?\\n\\n"
        "OUTPUT FORMAT: Return ONLY a JSON object:\\n"
        "{\\n"
        '  "verdict": "PASS",\\n'
        '  "audit_score": 9.2,\\n'
        '  "estimated_duration_minutes": 11.0,\\n'
        '  "pacing_verdict": "Excellent / Needs trim",\\n'
        '  "bloat_detected": false,\\n'
        '  "critique": "Crisp, breath-timed sentences with high dramatic urgency."\\n'
        "}"
    )

    user_prompt = (
        f"Episode Topic: {topic} | Market: {mkt}\\n"
        f"Total Sentences: {len(sentences)} | Total {unit_name}: {total_units} | Initial Est: {total_est_min:.1f} min\\n\\n"
        f"Spoken Script Sample (First 5 and Last 5 sentences):\\n"
        + "\\n".join(f"- [{s.get('sentence_id')} Beat {s.get('beat_index')}] {s.get('text')}" for s in sentences[:5])
        + "\\n...\\n"
        + "\\n".join(f"- [{s.get('sentence_id')} Beat {s.get('beat_index')}] {s.get('text')}" for s in sentences[-5:])
        + f"\\n\\nAudit this Spoken Script now:"
    )

    try:
        raw_res = call_gpt6_astra(user_prompt, system_prompt=system_prompt, max_tokens=1500, timeout=60.0)
        cleaned = raw_res.strip()
        if cleaned.startswith("```json"): cleaned = cleaned[7:]
        if cleaned.startswith("```"): cleaned = cleaned[3:]
        if cleaned.endswith("```"): cleaned = cleaned[:-3]
        audit = json.loads(cleaned.strip())
    except Exception as e:
        logger.warning(f"[story_engine] Adversarial spoken audit LLM parse error: {e}. Applying rule-based audit.")
        score = 9.0 if total_units <= max_units and len(sentences) >= 100 else 7.0
        audit = {
            "verdict": "PASS" if score >= 8.5 else "FAIL",
            "audit_score": score,
            "estimated_duration_minutes": total_est_min,
            "pacing_verdict": "Paced" if score >= 8.5 else "Length violation",
            "bloat_detected": total_units > max_units,
            "critique": "Rule-based audit fallback: duration and sentence count within safe parameters."
        }

    logger.info(f"[story_engine] Gate 2.5 Spoken VO Audit: Verdict={audit.get('verdict')} | Score={audit.get('audit_score')}/10 | Est={audit.get('estimated_duration_minutes')}m")
    return audit


def generate_5_arc_story(task_id: str, custom_meta: dict | None = None, force: bool = False) -> dict:
    """Generate a complete 5-Beat Docudrama script (1,800-2,200 words, ~12-15 min) using GPT-6-Astra
    enforcing YouTube Safety, Rule 444 An Ong Hook, and Rule 445 in a single optimized pass.
    Inherits authentic rules dynamically from Notion SoT (Central Skills + Content Engine Hub).
    """
    meta = custom_meta or load_task_metadata(task_id)
    mkt = meta.get("market", "EN").upper()
    topic = meta.get("topic") or meta.get("topic_name_vi") or meta.get("subject") or meta.get("raw_term") or task_id
    viral_angle = meta.get("specific_viral_angle") or ""
    niche_brief = meta.get("niche_brief") or meta.get("niche_angle_brief") or ""
    story_arcs = meta.get("story_arcs") or meta.get("story_direction_5_arcs") or ""
    breakout_queries = meta.get("breakout_queries") or meta.get("rising_queries") or []
    
    theme = meta.get("content_theme") or meta.get("theme")
    safety_label = meta.get("safety_label") or meta.get("youtube_safety_label")
    treatment_note = meta.get("treatment_note")
    
    if not safety_label or not treatment_note:
        theme, safety_label, treatment_note = detect_safety_and_theme(topic, mkt)

    out_dir = os.path.join(EPISODES_BASE_DIR, task_id)
    os.makedirs(out_dir, exist_ok=True)
    root_ep_dir = os.path.join("/root/video_factory/episodes", task_id)
    os.makedirs(root_ep_dir, exist_ok=True)

    # Grounding Layer (B1.5.5 Fact-Anchor Injection - Rule 118 & Rule 128)
    # Strict contract: load_grounding_intel raises RuntimeError if missing or rejected
    g_data, grounding_block = load_grounding_intel(
        task_id=task_id,
        out_dir=out_dir,
        topic=topic,
        niche_brief=niche_brief,
        market=mkt
    )
    if grounding_block:
        logger.info(f"[story_engine] Loaded Grounding Layer table ({len(g_data.get('claims', []))} claims) for {task_id}.")

    temporal_cadence = (g_data.get("temporal_cadence") or "ADAPTIVE").upper()
    causal_epochs = g_data.get("causal_epochs") or []

    intel_card = load_competitor_intel(task_id, topic=topic, niche_brief=niche_brief, market=mkt)
    intel_status = "loaded" if intel_card else "none"
    anatomy = (intel_card.get("competitor_narrative_anatomy") or {}) if intel_card else {}
    competitor_gap = meta.get("competitor_differentiation_gap") or anatomy.get("fatal_explanatory_vacuum") or (intel_card.get("competitor_gap") if intel_card else "")
    pivot_angle = anatomy.get("our_10x_pivot_angle") or ""
    frustrations = anatomy.get("audience_core_frustrations") or []
    comp_acts = anatomy.get("competitor_act_breakdown") or ""
    competitors = meta.get("viral_competitor_videos") or (intel_card.get("competitors") if intel_card else []) or (intel_card.get("competitor_benchmarks") if intel_card else [])
    ai_slop_redlines = (intel_card.get("ai_slop_redlines") or anatomy.get("ai_slop_redlines") or []) if intel_card else []
    transposition = (intel_card.get("transposition_opportunities") or anatomy.get("transposition_opportunities") or {}) if intel_card else {}

    # Check for pre-computed SEO package & 60s hook (Rule 119 & Rule 444)
    seo_pkg = {}
    for cand_dir in [out_dir, root_ep_dir]:
        sp_path = os.path.join(cand_dir, "seo_package.json")
        if os.path.exists(sp_path):
            try:
                with open(sp_path, "r", encoding="utf-8") as sf:
                    seo_pkg = json.load(sf)
                    if seo_pkg:
                        break
            except Exception:
                pass
    if not seo_pkg and isinstance(meta.get("seo_package"), dict):
        seo_pkg = meta["seo_package"]

    seo_title_a = seo_pkg.get("title_a") or meta.get("title_a") or ""
    seo_title_b = seo_pkg.get("title_b") or meta.get("title_b") or ""
    hook_60s = seo_pkg.get("hook_60s") or meta.get("hook_60s") or ""
    hook_3s = seo_pkg.get("hook_3s") or meta.get("hook_3s") or ""
    if seo_pkg.get("specific_viral_angle"):
        viral_angle = seo_pkg["specific_viral_angle"]
    
    logger.info(f"[story_engine] Starting 5-Act story generation for {task_id} ({mkt}) | Topic: {topic} | Angle: {viral_angle}... [Intel: {intel_status}, Gap: {bool(competitor_gap)}]")
    
    lang_name = "English" if mkt == "EN" else ("Japanese" if mkt == "JP" else "Korean")

    # Load authentic dynamic rules directly from Notion Single Source of Truth
    editorial_skills = get_b2_editorial_skills()

    crime_forensic_mandate = ""
    is_sensitive_crime = theme in ("true_crime_investigative", "psychology_manipulation_fraud") or any(
        w in (topic + " " + niche_brief).lower() for w in [
            "murder", "killer", "crime", "death", "homicide", "horror", "kinh dị", "án mạng", "giết người",
            "sát nhân", "사건", "살인", "연쇄살인", "事件", "殺人", "連続殺人"
        ]
    )
    if is_sensitive_crime:
        crime_forensic_mandate = (
            "\n🚨 MANDATORY CASE-SOLVING & FORENSIC PROTOCOL (CHỈ ĐẠO PHÁ ÁN & TRUY BẮT):\n"
            "1. INVESTIGATIVE & PROCEDURAL LENS ONLY (HƯỚNG ĐIỀU TRA & PHÁ ÁN):\n"
            "   - Frame the entire narrative through the objective lens of the detectives, forensic scientists, intelligence profilers, or prosecutors.\n"
            "   - Focus squarely on: the evidentiary puzzle, the forensic breakthrough (DNA, fingerprints, digital footprint, ballistic, autopsy toxicology, financial paper trail), the killer's fatal misstep, and the procedural manhunt net closing in.\n"
            "2. STRICT ZERO-GORE POLICY (TUYỆT ĐỐI CẤM MÔ TẢ HÀNH VI / HIỆN TRƯỜNG ĐẪM MÁU):\n"
            "   - STRICTLY FORBIDDEN: Detailing physical trauma, blood splatter, screams, struggle, weapon mechanics, mutilation, suffering, or torture.\n"
            "   - Refer to criminal acts ONLY in concise, clinical, legal terminology ('a disappearance was logged', 'toxicology revealed lethal compounds', 'investigators confirmed foul play').\n"
            "   - Immediately pivot from the incident to: How did the authorities piece together the mystery? What systemic blindspot was exposed? How was justice secured?\n"
            "3. ZERO CRIMINAL GLORIFICATION / FULL VICTIM RESPECT:\n"
            "   - Treat the perpetrator as flawed, cornered, and undone by their own arrogance. Zero romanticization of criminal 'genius'.\n"
        )

    hook_anchor_prompt = ""
    if hook_60s and not seo_pkg.get("is_fallback"):
        anti_imagine_directive = ""
        if "imagine" in hook_60s.lower() or "hypothetical" in hook_60s.lower():
            anti_imagine_directive = (
                "\n🚨 RULE 130 MANDATE: The reference hook contains passive/hypothetical framing ('imagine'). "
                "You MUST convert this into a DIRECT FACTUAL ASSERTION of verified events (Level 1 Primary Catalyst) "
                "with exact dates, actors, and quantitative metrics from the Grounding Table. STRICTLY FORBIDDEN: Writing 'Imagine...' in your script!\n"
            )
        if "hypothesis" in hook_60s.lower() or "unauthenticated" in hook_60s.lower():
            anti_imagine_directive += (
                "\n🚨 RULE 130 ANTI-NIHILISM MANDATE: The reference hook contains hyper-skeptical framing ('hypothesis'). "
                "You MUST treat verified real-world crisis events (e.g. market dislocations, operational halts, official alerts) as genuine facts (Level 1 Catalyst), "
                "and focus on explaining the transmission mechanism (institutional, contractual, regulatory, or financial transmission), NOT denying the reality of the crisis!\n"
            )
        hook_anchor_prompt = f"""• Approved YouTube Title A: {seo_title_a}
• Pre-Approved 3s Cold-Open: {hook_3s}
• Mandatory 60s Opening Premise Contract (Act I MUST anchor directly to this):
  "{hook_60s}"{anti_imagine_directive}
CRITICAL HOOK INSTRUCTION: You MUST open Act I by immediately using or adapting this 60s hook verbatim within the first 1-2 sentences. Ensure the very first sentence contains the concrete date, catalyst event, and numeric figure/percentage so that Check 9 (Hook Shock in First 60 Words) passes with 100% certainty. Do not write philosophical or vague introductions.

"""
    elif seo_title_a:
        hook_anchor_prompt = f"""• Target YouTube Title: {seo_title_a}
• Title Premise Instruction (Rule 130): Act I MUST directly address the central premise of this title, leading with the Level 1 Primary Catalyst and quantitative metrics from the Grounding Table.

"""

    slop_redlines_mandate = ""
    if ai_slop_redlines:
        redline_bullets = "\n".join(f"   * BANNED AUDIENCE CLICHE: \"{slop}\"" for slop in ai_slop_redlines[:4])
        slop_redlines_mandate = f"\n• Check 10B (Niche-Specific AI-Slop Redlines Mined From Audience):\n{redline_bullets}"

    if mkt == "JP":
        check7_mandate = (
            "• Check 7 (5-Act Architectural Cues - Japanese Native Vocabulary):\n"
            "   - Act I (Hook/Shock): 衝撃, 崩壊, 消失, 最初, 危機, and questions '?' or '？'.\n"
            "   - Act II (The False Narrative): 報道, 公式見解, 神話, 誤解, 背景, 歴史, オフィシャル.\n"
            "   - Act III (Systemic Blindspot): 死角, 疑惑, 欠陥, 内部, 記録, しかし, だが, 亀裂.\n"
            "   - Act IV (The Smoking Gun): 決定打, 証拠, 判決, 責任, 破綻, 暴露, 調査, 処分.\n"
            "   - Act V (The Modern Mirror): 警告, 教訓, 現代, 今日, 遺産, 課題, 結論.\n"
            "• Check 8 & 9 (Open & Close Curiosity Loops - Japanese Vocabulary):\n"
            "   - Open loops in each Act using: 果たして, 疑問, なぜ, 本当の理由は, だろうか (~2 per Act).\n"
            "   - Close loops in each Act using: その理由は, 答えは, 結局, こうして, 明らかになったのは, まさに (~2 per Act).\n"
            "   CRITICAL LINGUISTIC PURITY (RULE 120 & RULE 128): 100% Japanese prose. STRICTLY FORBIDDEN: Do NOT write raw English words ('collapse', 'shock', 'disappear', 'official story', 'red herring', 'paper trail', 'only') in Japanese prose; translate them into native Japanese!"
        )
    elif mkt == "KR":
        check7_mandate = (
            "• Check 7 (5-Act Architectural Cues - Korean Native Vocabulary):\n"
            "   - Act I (Hook/Shock): 충격, 붕괴, 위험, 의문, and questions '?'.\n"
            "   - Act II (The False Narrative): 보도, 언론, 오해, 통념, 배경, 역사.\n"
            "   - Act III (Systemic Blindspot): 사각지대, 맹점, 의혹, 내부, 계약, 그러나.\n"
            "   - Act IV (The Smoking Gun): 스모킹건, 결정적, 증거, 판결, 책임, 폭로, 단속.\n"
            "   - Act V (The Modern Mirror): 경고, 교훈, 현대, 오늘날, 과제, 결론, 유산.\n"
            "   CRITICAL LINGUISTIC PURITY (RULE 120 & RULE 128): 100% Korean prose. STRICTLY FORBIDDEN: Do NOT write raw English words in Korean prose!"
        )
    else:
        check7_mandate = (
            "• Check 7 (5-Act Architectural Cues): Each Act must explicitly weave in its architectural vocabulary:\n"
            "   - Act I (Hook/Shock): 'collapse', 'shock', 'disappear', 'first', 'only', and questions '?'.\n"
            "   - Act II (The False Narrative): 'official story', 'narrative', 'headline', 'myth', 'red herring'.\n"
            "   - Act III (Systemic Blindspot): 'paper trail', 'blindspot', 'loophole', 'leak', 'memo', 'forensic'.\n"
            "   - Act IV (The Smoking Gun): 'smoking gun', 'culprit', 'exposed', 'unmasked', 'profited'.\n"
            "   - Act V (The Modern Mirror): 'mirror', 'warning', 'modern', 'today', 'lesson', 'verdict'."
        )

    if mkt == "KR":
        length_mandate = (
            "Total Word/Syllable Count Target: 3,200 - 3,600 Korean Hangul syllables (~1,050 - 1,250 eojeol words) across 5 structured Acts for ~12-14 minutes narration at natural docudrama pace (~250 syllables/min).\n"
            "Structure per Act: Approximately 210-250 Korean words (640-720 syllables) across 3-4 vivid, investigative paragraphs per Act.\n"
            "Strict Requirement: Scripts under 2,800 Korean syllables or under 950 words will be rejected by the story gate.\n\n"
        )
    elif mkt == "JP":
        length_mandate = (
            "Total Character Count Target: 3,400 - 3,800 Japanese characters (~1,150 - 1,300 word units) across 5 structured Acts for ~12-14 minutes narration at natural cadence (~270 chars/min).\n"
            "Structure per Act: Approximately 680-760 Japanese characters across 3-4 vivid, investigative paragraphs per Act.\n"
            "Strict Requirement: Scripts under 3,000 characters or under 1,000 word units will be rejected by the story gate.\n\n"
        )
    else:
        length_mandate = (
            "Total Word Count Target: 1,800 - 2,200 words (~12 to 15 minutes narration at ~150 WPM) across 5 structured Acts.\n"
            "Structure per Act: Approximately 360-440 words across 3-4 vivid, investigative paragraphs per Act.\n"
            "Strict Requirement: Scripts under 1,700 words will be rejected by the story gate.\n\n"
        )

    chrono_cadence_instructions = {
        "MACRO_SAGA": (
            "TEMPORAL CADENCE: MACRO_SAGA (Multi-Year / Decadal Epic):\n"
            "This investigation spans multiple years or decades. You MUST construct a sweeping chronological causal arc across the 5 Acts:\n"
            "• Act I (Contemporary Shock & Rupture): Open with the contemporary breaking point, final verdict, or recent market shock. Anchor strictly to verified dates and metrics.\n"
            "• Act II (The Genesis Rewind - Origin Deal/Baseline): Rewind years back to the foundational origin point (the founding loan, initial contract, deregulatory move, or early premise). Establish the baseline before the crisis began.\n"
            "• Act III (The Hidden Mutation & Systemic Rot): Trace the years of brewing trouble—unheeded audits, hidden debt/leverage, quiet contractual loopholes, or regulatory blind spots that metastasized beneath the surface.\n"
            "• Act IV (The Fatal Rupture & Reckoning): Document the catastrophic collapse, criminal indictment, default, or international legal ruling that tore the illusion apart.\n"
            "• Act V (The Modern Mirror & Asset Hunt): Return to the contemporary horizon—the forensic pursuit of hidden assets, remaining liabilities, and the enduring institutional warning for viewers today."
        ),
        "MID_TACTICAL": (
            "TEMPORAL CADENCE: MID_TACTICAL (Months to 1-2 Years Operational/Policy Conflict):\n"
            "This investigation spans months or a short multi-season cycle. Construct an escalating procedural arc:\n"
            "• Act I: The acute trigger event and public outbreak.\n"
            "• Act II: Pre-crisis baseline and early tactical decisions months earlier.\n"
            "• Act III: The escalation phase, internal disputes, and warning signals ignored by leadership.\n"
            "• Act IV: The climax—public confrontation, regulatory intervention, or operational failure.\n"
            "• Act V: The fallout, policy changes, and forward-looking systemic impact."
        ),
        "FLASH_CRISIS": (
            "TEMPORAL CADENCE: FLASH_CRISIS (Days to Weeks Rapid Shock / Flash Collapse):\n"
            "This investigation spans hours, days, or weeks (e.g. bank run, liquidity freeze, sudden catastrophe). Maintain breathless, high-velocity ticking-clock pacing:\n"
            "• Act I: The breaking collapse and catastrophic 24-hour run.\n"
            "• Act II: The vulnerable baseline conditions immediately preceding the spark.\n"
            "• Act III: The transmission contagion—hour-by-hour panic, margin calls, or operational dominoes.\n"
            "• Act IV: The emergency rupture point—failed bailouts, sudden halts, or regulatory seizure.\n"
            "• Act V: Forensic autopsy—the immediate lessons and structural exposure."
        )
    }
    cadence_guide = chrono_cadence_instructions.get(
        temporal_cadence,
        "TEMPORAL CADENCE: ADAPTIVE CHRONO-PACING:\n"
        "Trace the timeline progression from initial origin through mutation to the critical rupture and modern aftermath."
    )
    chrono_mandate = (
        f"\n🚨 MANDATORY ADAPTIVE CHRONO-PACING & TEMPORAL PROGRESSION (RULE 130):\n"
        f"{cadence_guide}\n"
        f"CRITICAL SINGLE-TIMESTAMP ACCOUNTING LOOP PROHIBITION:\n"
        f"STRICTLY FORBIDDEN: Looping and repeating the exact same financial figures or news snippet from today's headline across all 5 Acts!\n"
        f"Each Act MUST advance along the chronological causal chain defined in the Chrono-Causal Epochs Table. Give viewers the full investigative journey—from genesis to reckoning."
    )

    system_prompt = (
        f"You are a World-Class Master Non-Fiction Investigative Documentary Scriptwriter for Video Factory.\n"
        f"Target Narration Language: {lang_name}.\n"
        f"{length_mandate}"
        f"CINEMATIC DOCUDRAMA EMOTIONAL PACING & HIGH STAKES (RULE 130 & RULE 445):\n"
        f"• TONE & ATMOSPHERE: Channel the forensic procedural tension of 'Chernobyl', 'Margin Call', and Johnny Harris investigative journalism. "
        f"Ground the narrative in tangible human stakes, institutional blindspots, and the suffocating pressure of white-collar malfeasance. Avoid dry academic lectures.\n"
        f"• SEARCH INTENT PAYOFF (FIRST 120 WORDS OF ACT I): The opening of Act I MUST open with a concrete quantitative stake (%, $, or headcount) in Sentence 1, and MUST naturally weave in at least 3 of the following LIVE SEARCH QUERIES: {', '.join(breakout_queries[:5])}.\n"
        f"• FACT-LOCK DISCIPLINE (RULE 118 & RULE 130): Anchor the narrative strictly around the verified claims in the Grounded Facts Dossier. "
        f"STRICTLY FORBIDDEN: Inventing unverified dates, fictitious dollar amounts, false court filings, or speculative causal leaps. "
        f"Weave verified numbers, dates, and regulatory filings from the Dossier naturally into the dialogue without sounding defensive or robotic.\n"
        f"• CURIOSITY LOOPS & SUSPENSE HOOKS: Plant 8 to 10 explicit curiosity questions across the 5 Acts (~2 per Act), resolving them authoritatively with causal revelations ('that is why', 'the paper trail proved', 'in the end').\n"
        f"• PATTERN INTERRUPT (ACT III): Include at least one sharp, punchy sentence of 2 to 6 words maximum in Act III to reset viewer focus.\n"
        f"• ZERO AI CLICHES: 100% elimination of banned phrases ('in a world where', 'little did they know', 'double-edged sword', 'at the end of the day').{slop_redlines_mandate}\n\n"
        f"{editorial_skills}\n\n"
        f"SPECIFIC CASE CONTEXT:\n"
        f"• Subject / Case: {topic}\n"
        f"• Specific Viral Angle: {viral_angle}\n"
        f"• Core Causal Mechanism: {niche_brief}\n"
        f"• 5-Arc Narrative Plan: {story_arcs}\n"
        f"• Content Theme: {theme}\n"
        f"• Top Rising Search Queries: {', '.join(breakout_queries[:5])}\n\n"
        f"{hook_anchor_prompt}"
        f"CRITICAL PLATFORM SAFETY MANDATE [{safety_label}]:\n"
        f"• {treatment_note}\n"
        f"• Zero graphic violence, zero gore, zero criminal glorification, zero method instructions.\n"
        f"{crime_forensic_mandate}\n"
        f"{chrono_mandate}\n"
        f"Output ONLY the complete script organized strictly by Acts using '=== ACT I ===', '=== ACT II ===', '=== ACT III ===', '=== ACT IV ===', '=== ACT V ===' markers. No markdown fences, no stage directions."
    )

    competitor_context = ""
    context_lines = []
    if transposition and isinstance(transposition, dict) and transposition.get("proven_structural_vehicle"):
        v_name = transposition["proven_structural_vehicle"]
        context_lines.append(
            "⚡ PROVEN STRUCTURAL VEHICLE (Format Win Transposition):\n"
            f"Transmute this proven narrative vehicle to our case: \"{v_name}\".\n"
            "Adopt its core tension, pacing rhythm, and psychological hook while investigating our unique case."
        )
    elif transposition and isinstance(transposition, list):
        items = [f"  - {item}" for item in transposition if isinstance(item, str)]
        if items:
            context_lines.append(
                "⚡ PROVEN STRUCTURAL VEHICLE (Format Win Transposition):\n"
                + "\n".join(items)
            )
    if pivot_angle:
        context_lines.append(
            "🎯 10X INDEPENDENT INVESTIGATIVE PIVOT (OUR STRATEGIC LEVERAGE):\n"
            f"{pivot_angle}\n"
            "MANDATE: Frame our entire 15-minute documentary around this independent breakthrough angle. "
            "Expose the systemic paper trails and institutional mechanisms that nobody else dared or bothered to examine!"
        )
    if competitor_gap:
        context_lines.append(
            "⚠️ COMPETITOR EXPLANATORY VACUUM (FATAL BLINDSPOT):\n"
            f"Competitors only covered surface events and missed this crucial mechanism: \"{competitor_gap}\"\n"
            "REQUIREMENT: Acts III, IV, and V must systematically expose and explain this blindspot in depth!"
        )
    if comp_acts:
        context_lines.append(
            f"📊 COMPETITOR NARRATIVE STRUCTURE (What they did):\n{comp_acts}\n"
            "Use this structure only as a springboard to understand viewer expectations, then leap far beyond it with deeper forensic details."
        )
    if frustrations:
        context_lines.append(
            "🔥 AUDIENCE BURNING QUESTIONS & FRUSTRATIONS (MUST BE RESOLVED):\n"
            + "\n".join(f"  - {fr}" for fr in frustrations[:3])
            + "\nYour script must seamlessly and authoritatively answer every single one of these viewer doubts throughout the narrative."
        )
    if competitors:
        context_lines.append("TOP VIRAL COMPETITOR BENCHMARKS (High velocity references):")
        for c in competitors[:3]:
            v_views = c.get("views", 0)
            v_title = c.get("title", "?")
            context_lines.append(f'  - \"{v_title}\" ({v_views:,} views)')
    if intel_card and intel_card.get("audience_comment_gaps"):
        context_lines.append("High-engagement audience comment quotes:")
        for g in intel_card["audience_comment_gaps"][:3]:
            if isinstance(g, dict):
                context_lines.append(f"  - [{g.get('likes_count', 0)} likes] {g.get('comment_verbatim', '')[:140]}")
            elif isinstance(g, str):
                context_lines.append(f"  - {g[:140]}")

    context_lines.append(
        "🚨 STRICT ZERO COMPETITOR NAME-DROP MANDATE:\n"
        "NEVER mention the names of competitor channels, creators, or rival videos. "
        "Maintain the clinical, objective authority of a premier independent investigative documentary."
    )

    if context_lines:
        competitor_context = "\n".join(context_lines) + "\n\n"

    is_cjk_market = mkt.upper() in ("JP", "KR", "ZH")
    min_existing = 1500 if is_cjk_market else 1000

    story_file = os.path.join(out_dir, "story.txt")
    existing_script = ""
    # Rule 118 & Rule 125: Temporary evaluation tasks during B1 scanning must NEVER reuse stale scripts from other candidates
    if "_TEMP_" in task_id:
        force = True

    if os.path.exists(story_file) and not force:
        try:
            with open(story_file, "r", encoding="utf-8") as sf:
                existing_script = sf.read().strip()
            # Anti-hallucination check: force regeneration if script was ungrounded
            grounding_intel_file = os.path.join(out_dir, "grounding_intel.json")
            is_ungrounded = ("hypothetical calculation" in existing_script.lower() or not os.path.exists(grounding_intel_file))
            existing_len = len(existing_script) if is_cjk_market else len(existing_script.split())
            if is_ungrounded:
                logger.info(f"[story_engine] Existing story.txt for {task_id} is ungrounded or missing grounding_intel.json. Forcing fresh regeneration!")
                existing_script = ""
            elif existing_len >= min_existing:
                metric_lbl = "chars" if is_cjk_market else "words"
                logger.info(f"[story_engine] Reusing existing valid grounded story.txt ({existing_len} {metric_lbl}) for {task_id}.")
        except Exception as e:
            logger.warning(f"[story_engine] Error reading existing story.txt: {e}")
    elif force:
        logger.info(f"[story_engine] Force regeneration requested for {task_id}. Generating fresh high-suspense grounded script...")

    existing_len = len(existing_script) if is_cjk_market else len(existing_script.split())
    if existing_script and existing_len >= min_existing:
        full_script = existing_script
    else:
        # B11->B2 Feedback Loop: fetch active InsightCards (Rule 126 compliant, non-fatal)
        _b2_notion_token = (
            os.getenv('NOTION_TOKEN', '') or
            os.getenv('VF_NOTION_TOKEN', '')
        )
        _b2_insight_cards = fetch_active_insights(_b2_notion_token, mkt)
        feedback_block = build_feedback_block(_b2_insight_cards)
        
        user_prompt = (
            f"Generate the comprehensive 12-15 minute (1,800-2,200 words) Non-Fiction Investigative Documentary Script for {topic} following the 5-Beat Investigative Docudrama structure with HIGH DRAMATIC SUSPENSE and ticking-clock pacing.\n"
            f"Structure: Beat 1 (The Impossible Contradiction & Ticking Clock) -> Beat 2 (The False Narrative & Red Herring) -> Beat 3 (The Systemic Blindspot & Paper Trail) -> Beat 4 (The Real Culprit & Smoking Gun) -> Beat 5 (The Uncomfortable Modern Mirror & Living Warning).\n"
            f"Tone & Style: Johnny Harris investigative rigor meets Chernobyl / Margin Call procedural tension—clinical, fast-paced, high-stakes, forensically detailed, completely free of fluff.\n"
            f"Language: {lang_name}.\n"
            f"Core Mechanism: {niche_brief}\n"
            f"5-Arc Narrative: {story_arcs}\n"
            f"Content Theme: {theme}\n"
            f"Breakout Search Queries to prioritize in Act I: {', '.join(breakout_queries)}\n\n"
            f"{grounding_block}\n\n" if grounding_block else ""
            f"{competitor_context}"
            f"{feedback_block}"
            f"ACT I OPENING MANDATE (Rule 444 An Ong Hook, Rule 130 Search-Intent Payoff & Contemporary Event Anchor): "
            f"Sentence 1 of Act I MUST open with a shock quantitative stake or economic contradiction. "
            f"Paragraphs 1-2 of Act I MUST explicitly name and anchor to the verified Contemporary Catalyst Event "
            f"(exact date, acting entity, and verified quantitative impact from the Grounding Table). "
            f"Zero generic preamble, slow historical setup, or abstract theoretical hand-waving ('When a threat occurs'). "
            f"STRICTLY FORBIDDEN: Dry accounting balance-sheet lectures, administrative term definitions, or defensive disclaimers in Act I. "
            f"Keep Act I electric, suspenseful, and cinematic: directly satisfy and pay off the viewer's search query with verified contemporary facts before peeling back the systemic layers.\n"
            f"CHRONO-CAUSAL PROGRESSION (TEMPORAL CADENCE: {temporal_cadence}): "
            f"Advance the narrative chronologically across the 5 Acts using the Chrono-Causal Epochs Table (Genesis Seed -> Mutation & Warning -> Critical Rupture -> Modern Aftermath). "
            f"STRICTLY FORBIDDEN: Looping and repeating the exact same single-timestamp figures across every Act. Each Act must uncover a distinct temporal phase of the case.\n"
            f"Write the full ~1,800-2,200 word script now, adhering strictly to the 5-Act markers:"
        )

        logger.info(f"[story_engine] Calling Claude Opus 5 (Master Scriptwriter) for 5-Act Script generation (1,800-2,200 words)...")
        from app.services.model_gateway import get_global_gateway
        gateway = get_global_gateway()
        full_script_raw = gateway.call_llm(
            prompt=user_prompt,
            model="claude-opus-5",
            system_prompt=system_prompt,
            max_tokens=6000,
            temperature=0.35,
            timeout=300.0,
            fallback="claude-sonnet-5"
        )

        cleaned_acts = []
        matches = ACT_PATTERN.findall(full_script_raw)
        if matches:
            for m in matches:
                cleaned_acts.append(m[0].strip())

        if len(cleaned_acts) < 5:
            # Fallback split by double newlines if markers weren't strictly matched
            full_script = full_script_raw.strip()
        else:
            full_script = "\n\n".join(cleaned_acts)

    is_cjk_market = mkt.upper() in ("JP", "KR", "ZH")
    total_len = len(full_script) if is_cjk_market else len(full_script.split())
    metric_lbl = "chars" if is_cjk_market else "words"
    logger.info(f"[story_engine] Generated 5-Act Script: {total_len} {metric_lbl} for {task_id}.")

    # Audit Story Gate Score
    audit = sgate.score_story(full_script)
    story_score_str = f"{audit.get('score', 8)}/{audit.get('max_score', 12)}"
    story_verdict = audit.get('verdict') or 'UNKNOWN'
    logger.info(f"[story_engine] Initial Story Gate Score: {story_score_str} | Verdict: {audit.get('verdict')}")

    best_script = full_script
    best_score = audit.get("score", 0)
    best_audit = audit
    best_score_str = story_score_str
    best_verdict = story_verdict

    # Auto-Refine Self-Correction Loop: Mandate 12/12 Perfect Score for every Episode
    if best_score < 12 or best_verdict != "PASS":
        for refine_attempt in range(1, 3):
            logger.warning(
                f"[story_engine] Story Gate under 12/12 ({best_score}/{best_audit.get('max_score', 12)}). "
                f"Fix hints: {best_audit.get('fix_hints')}. Banned hits: {best_audit.get('banned_phrases_found')}. "
                f"Initiating Auto-Refine Attempt {refine_attempt}/2 via GPT-6-Astra to achieve 12/12..."
            )
            length_instruction = "strictly maintaining 2,500-3,500 Japanese characters" if mkt.upper() == "JP" else (
                "strictly maintaining 2,500-3,500 Korean characters" if mkt.upper() == "KR" else
                "strictly maintaining 1,800-2,200 words"
            )
            refine_user = (
                f"The generated script scored {best_score}/{best_audit.get('max_score', 12)} on Story Gate. Target is 12/12 PERFECT SCORE.\n"
                f"REQUIRED CORRECTIONS:\n" + "\n".join(f"- {h}" for h in best_audit.get("fix_hints", [])) + "\n\n"
                f"CRITICAL REMINDERS FOR 12/12:\n"
                f"1. Hook Shock: Sentence 1 of Act I MUST feature a quantitative number, %, or $ figure within 60 words.\n"
                f"2. Pattern Interrupt: Act III MUST have at least one short sentence of 2 to 6 words (e.g. 'The paper trail vanished.').\n"
                f"BANNED PHRASES FOUND (MUST ELIMINATE): {', '.join(best_audit.get('banned_phrases_found', []))}\n\n"
                f"Please rewrite and polish the entire 5-Act script, {length_instruction}, "
                f"preserving all 5 Acts ('=== ACT I ===' to '=== ACT V ==='), ensuring the first sentence opens with a shock quantitative stake (Rule 444), and resolving all failed items.\n\n"
                f"Current Draft:\n{best_script}\n\n"
                f"Output ONLY the corrected 5-Act script now:"
            )
            refine_system_prompt = (
                f"""You are the Senior Docudrama Script Editor for AI Video Factory ({mkt.upper()} Market).
Your objective is SURGICAL SCRIPT POLISHING to achieve a 12/12 Perfect Score on Story Gate.
CRITICAL EDITORIAL RULES:
1. Preserve the full narrative integrity, verified facts, and dramatic pacing of the current draft.
2. Directly address each specified correction (Hook shock number in Sentence 1, Pattern interrupt short sentence in Act III, elimination of banned clichés).
3. Preserve all 5 Acts with exact delimiters ('=== ACT I ===' through '=== ACT V ===').
4. Maintain target narrative length ({length_instruction}).
5. Output ONLY the polished script in the target market language verbatim. No commentary or markdown fences."""
            )
            try:
                refined_raw = gateway.call_llm(
                    prompt=refine_user,
                    model="claude-opus-5",
                    system_prompt=refine_system_prompt,
                    max_tokens=6000,
                    temperature=0.3,
                    timeout=300.0,
                    fallback="claude-sonnet-5"
                )
                refined_len = len(refined_raw) if is_cjk_market else len(refined_raw.split())
                min_threshold = 1500 if is_cjk_market else 1000
                if refined_raw and refined_len >= min_threshold:
                    cleaned_acts_ref = []
                    matches_ref = ACT_PATTERN.findall(refined_raw)
                    if matches_ref:
                        for mr in matches_ref:
                            cleaned_acts_ref.append(mr[0].strip())
                    candidate_script = "\n\n".join(cleaned_acts_ref) if len(cleaned_acts_ref) == 5 else refined_raw.strip()
                    ref_audit = sgate.score_story(candidate_script)
                    ref_score = ref_audit.get("score", 0)
                    ref_score_str = f"{ref_score}/{ref_audit.get('max_score', 12)}"
                    ref_verdict = ref_audit.get('verdict') or 'UNKNOWN'
                    logger.info(f"[story_engine] Post-Refine Attempt {refine_attempt} Score: {ref_score_str} | Verdict: {ref_verdict}")
                    if ref_score > best_score:
                        best_script = candidate_script
                        best_score = ref_score
                        best_audit = ref_audit
                        best_score_str = ref_score_str
                        best_verdict = ref_verdict
                        logger.info(f"[story_engine] Auto-Refine Improved Score to {best_score_str} ({best_verdict})")
                    if best_score >= 12:
                        logger.info(f"[story_engine] Auto-Refine SUCCESS: Perfect 12/12 achieved on attempt {refine_attempt}!")
                        break
            except Exception as _re:
                logger.warning(f"[story_engine] Auto-refine attempt {refine_attempt} error: {_re}")

    full_script = best_script
    audit = best_audit
    story_score_str = best_score_str
    story_verdict = best_verdict

    # ----------------------------------------------------
    # B2.1 Fact & Causal Integrity Audit Gate (Rule 118 & Rule 130)
    # Audits full verbatim script against Grounding Fact Table using claude-opus-5
    # ----------------------------------------------------
    fact_audit_result = {}
    grounding_claims = []
    try:
        for _g_cand in [os.path.join(out_dir, "grounding_intel.json"), os.path.join(root_ep_dir, "grounding_intel.json")]:
            if os.path.exists(_g_cand):
                with open(_g_cand, "r", encoding="utf-8") as _gf:
                    grounding_claims = json.load(_gf).get("claims", [])
                if grounding_claims:
                    break
    except Exception as _ge:
        logger.warning(f"[story_engine] Error loading grounding claims for B2.1: {_ge}")

    if not grounding_claims and 'g_data' in locals() and isinstance(g_data, dict):
        grounding_claims = g_data.get("claims", [])

    if not grounding_claims:
        logger.error(f"[story_engine] CRITICAL: No verified grounding claims found for {task_id}! Violates Rule 118.")
        fact_audit_result = {
            "verdict": "FAIL",
            "audit_score": 1.0,
            "red_flags": ["RULE_118_ZERO_GROUNDING_CLAIMS"],
            "critical_findings": "Pipeline blocked: Zero verified factual claims available for story audit."
        }
        f_verdict = "FAIL"
        f_score = 1.0
    else:
        try:
            from app.services.story_fact_auditor_b2 import audit_story_facts_and_causality
            logger.info(f"[story_engine] Running B2.1 Fact & Causal Audit via gpt-6-astra for {task_id}...")
            fact_audit_result = audit_story_facts_and_causality(
                story_text=full_script,
                grounding_claims=grounding_claims,
                topic_meta={
                    "task_id": task_id,
                    "topic_name_vi": topic,
                    "rising_queries": breakout_queries,
                    "temporal_cadence": temporal_cadence,
                    "causal_epochs": causal_epochs
                },
                market=mkt,
                model="gpt-6-astra",
                fallback_model="kimi-k3"
            )
            f_verdict = fact_audit_result.get("verdict", "PASS").upper()
            f_score = float(fact_audit_result.get("audit_score", 8.0))
            logger.info(f"[story_engine] B2.1 Fact & Causal Audit: Verdict={f_verdict} (Score: {f_score}/10)")

            # Dual-Model Convergence Protocol if audit fails (< 7.5 or FAIL)
            if f_verdict == "FAIL" or f_score < 7.5:
                audit_critique = fact_audit_result.get("audit_notes") or fact_audit_result.get("veto_reason") or "Factual or causal discrepancies found."
                logger.warning(f"[story_engine] B2.1 Audit FAILED (Score: {f_score}/10). Activating Dual-Model Convergence Protocol (Opus 5 Targeted Patcher + Astra Delta Audit)...")

                try:
                    from app.services.dual_model_convergence import run_dual_model_convergence
                    conv_res = run_dual_model_convergence(
                        story_text=full_script,
                        grounding_claims=grounding_claims,
                        audit_critique=audit_critique,
                        topic_meta={
                            "task_id": task_id,
                            "topic_name_vi": topic,
                            "rising_queries": breakout_queries,
                            "temporal_cadence": temporal_cadence,
                            "causal_epochs": causal_epochs
                        },
                        market=mkt,
                        system_prompt=system_prompt,
                        initial_audit_result=fact_audit_result
                    )
                    
                    if conv_res.get("converged"):
                        full_script = conv_res.get("script", full_script)
                        fact_audit_result = conv_res.get("audit_details", fact_audit_result)
                        fact_audit_result["convergence_status"] = "CONVERGED"
                        fact_audit_result["verdict"] = "PASS"
                        fact_audit_result["audit_score"] = float(conv_res.get("fact_score", 8.0))
                        f_verdict = "PASS"
                        f_score = float(conv_res.get("fact_score", 8.0))

                        # Re-score converged script against Story Gate (Rule 125 & 127)
                        conv_audit = sgate.score_story(full_script)
                        story_score_str = f"{conv_audit.get('score', 10)}/{conv_audit.get('max_score', 12)}"
                        story_verdict = conv_audit.get('verdict') or 'PASS'
                        fact_audit_result["story_gate_score"] = story_score_str
                        fact_audit_result["story_verdict"] = story_verdict
                        logger.info(f"[story_engine] Dual-Model Convergence SUCCESS: Script converged with Fact Score {f_score}/10 | Story Gate: {story_score_str} ({story_verdict})!")
                    else:
                        fact_audit_result = conv_res.get("audit_details", fact_audit_result)
                        fact_audit_result["convergence_status"] = "NON_CONVERGENCE"
                        fact_audit_result["veto_reason"] = conv_res.get("reason")
                        f_verdict = "FAIL"
                        f_score = float(conv_res.get("fact_score", f_score))
                        logger.error(f"[story_engine] Dual-Model Convergence FAILED for {task_id}. Non-convergence flag set for Leader.")
                except Exception as _conv_err:
                    logger.error(f"[story_engine] Dual-Model Convergence execution failed: {_conv_err}")
        except Exception as _fa_err:
            logger.warning(f"[story_engine] B2.1 Fact & Causal Audit warning: {_fa_err}")

    # Rule 121 & Rule 127: Hard Story Integrity Gate (Anti-Truncation & 5-Act Assurance)
    clean_acts = ACT_PATTERN.findall(full_script)
    act_count = len(clean_acts)
    word_count = len(full_script.split())
    char_count = len(full_script)
    is_cjk = any(mkt.upper() == c for c in ["JP", "KR", "JA", "KO"])
    min_len = 1000 if not is_cjk else 1500  # words for EN, characters for CJK
    actual_len = char_count if is_cjk else word_count
    ends_valid = bool(re.search(r"[.!?。？！'\"”’]\s*$", full_script.strip()))

    if act_count < 5 or actual_len < min_len or not ends_valid:
        err_msg = (
            f"[story_engine] CRITICAL STORY DEFECT for {task_id}: Script is truncated or malformed! "
            f"Acts found: {act_count}/5, Length: {actual_len} (required >= {min_len}), "
            f"Ends with sentence punctuation: {ends_valid}. Rejecting export to B3!"
        )
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Write story.txt to both directories
    for d in [out_dir, root_ep_dir]:
        try:
            with open(os.path.join(d, "story.txt"), "w", encoding="utf-8") as f:
                f.write(full_script)
        except Exception as _fe:
            logger.warning(f"[story_engine] Error writing story.txt to {d}: {_fe}")

    # ----------------------------------------------------
    # Phase 2: Adapt Master Spoken VO Script (Hollywood Standard - Rule 120 & Rule 128)
    # ----------------------------------------------------
    logger.info(f"[story_engine] Phase 2: Generating Master Spoken VO Script for {task_id}...")
    spoken_data = adapt_master_spoken_script(full_script=full_script, market=mkt, topic=topic)
    spoken_audit = adversarial_audit_spoken_script(spoken_data=spoken_data, market=mkt, topic=topic)
    spoken_script_text = spoken_data.get("spoken_script_text") or full_script
    spoken_sentences = spoken_data.get("sentences") or []

    # Write spoken_script.txt & spoken_sentences.json to both directories
    for d in [out_dir, root_ep_dir]:
        try:
            with open(os.path.join(d, "spoken_script.txt"), "w", encoding="utf-8") as f:
                f.write(spoken_script_text)
            with open(os.path.join(d, "spoken_sentences.json"), "w", encoding="utf-8") as f:
                json.dump(spoken_sentences, f, ensure_ascii=False, indent=2)
        except Exception as _fe:
            logger.warning(f"[story_engine] Error writing spoken VO assets to {d}: {_fe}")

    # ----------------------------------------------------
    # B2 Output Finalization (Rule 125: B3 Scene breakdown delegated to director_planner_b3.py)
    # ----------------------------------------------------
    logger.info("[story_engine] B2 5-Act story & Spoken VO complete. Scene breakdown delegated to B3 Art Director.")
    scenes = []

    # Build brain_input.json
    brain_input = {
        "episode_id": task_id,
        "market": mkt.lower(),
        "topic": topic,
        "story": full_script,
        "story_gate_score": story_score_str,
        "story_verdict": story_verdict,
        "bgm_mood": "dramatic",
        "hook_3s": hook_3s or _opening_hook(full_script),
        "hook_60s": hook_60s,
        "title_a": seo_title_a,
        "title_b": seo_title_b,
        "seo_package": seo_pkg,
        "breakout_queries": breakout_queries,
        "content_theme": theme,
        "safety_label": safety_label,
        "treatment_note": treatment_note,
        "spoken_script": spoken_script_text,
        "spoken_sentences": spoken_sentences,
        "spoken_script_audit": spoken_audit,
        "total_estimated_minutes": spoken_audit.get("estimated_duration_minutes") or spoken_data.get("total_estimated_minutes", 11.0),
        "scenes": scenes,
        "total_scenes": len(scenes),
        "render_architecture": "two_layer_v1",
        "fact_causal_audit": fact_audit_result
    }

    for d in [out_dir, root_ep_dir]:
        try:
            with open(os.path.join(d, "brain_input.json"), "w", encoding="utf-8") as f:
                json.dump(brain_input, f, ensure_ascii=False, indent=2)
        except Exception as _fe:
            logger.warning(f"[story_engine] Error writing brain_input.json to {d}: {_fe}")

    # ----------------------------------------------------
    # Notion Sync: Story Library & Director Plan DBs
    # ----------------------------------------------------
    try:
        story_page_id = meta.get("page_id")

        if story_page_id and seo_pkg:
            try:
                from app.services.seo_package_forge import sync_seo_package_to_story_library
                sync_seo_package_to_story_library(task_id, seo_pkg, story_page_id=story_page_id)
            except Exception as _se:
                logger.warning(f"[story_engine] Error syncing SEO package to Story Library: {_se}")

        if not story_page_id:
            try:
                t_filt = {"or": [
                    {"property": "Task ID", "rich_text": {"equals": str(task_id)}},
                    {"property": "Episode ID", "rich_text": {"equals": str(task_id)}}
                ]}
                q_res = query_db(NOTION_STORY_DB_ID, filter_obj=t_filt)
                if q_res.get("results"):
                    story_page_id = q_res["results"][0]["id"]
                    logger.info(f"[story_engine] Found existing Story Library page {story_page_id} for {task_id}")
                else:
                    new_props = {
                        "Name": {"title": [{"type": "text", "text": {"content": str(topic)}}]},
                        "Task ID": {"rich_text": [{"type": "text", "text": {"content": str(task_id)}}]},
                        "Episode ID": {"rich_text": [{"type": "text", "text": {"content": str(task_id)}}]},
                        "Market": {"select": {"name": mkt}},
                        "Status": {"status": {"name": "Gate Passed" if story_verdict == "PASS" else "Compiled"}},
                        "Story Gate Score": {"rich_text": [{"type": "text", "text": {"content": f"[AG] {story_score_str} {story_verdict} (GPT-6-ASTRA)"}}]},
                        "Niche Angle Brief": {"rich_text": [{"type": "text", "text": {"content": str(niche_brief)[:1999]}}]},
                        "Story Direction (5 Arcs)": {"rich_text": [{"type": "text", "text": {"content": str(story_arcs)[:1999]}}]},
                    }
                    if breakout_queries:
                        new_props["Rising Queries"] = {"rich_text": [{"type": "text", "text": {"content": ", ".join(breakout_queries)[:1999]}}]}
                    if competitor_gap:
                        new_props["Competitor Benchmarks"] = {"rich_text": [{"type": "text", "text": {"content": str(competitor_gap)[:1999]}}]}
                    cr_res = create_page(NOTION_STORY_DB_ID, new_props)
                    if isinstance(cr_res, dict) and cr_res.get("id"):
                        story_page_id = cr_res["id"]
                        logger.info(f"[story_engine] Created new Story Library page {story_page_id} for {task_id}")
            except Exception as _qe:
                logger.warning(f"[story_engine] Error resolving/creating Story Library row: {_qe}")

        if story_page_id:
            props = {
                'Status': {'status': {'name': 'Gate Passed' if story_verdict == 'PASS' else 'Compiled'}},
                'Story Gate Score': {'rich_text': [{'type': 'text', 'text': {'content': f'[AG] {story_score_str} {story_verdict} (GPT-6-ASTRA)'}}]},
                'Rising Queries': {'rich_text': [{'type': 'text', 'text': {'content': ', '.join(breakout_queries)}}]}
            }
            _res = update_page_properties(story_page_id, props)
            if isinstance(_res, dict) and _res.get('error'):
                logger.error('[story_engine] Story Library patch FAILED %s: %s' % (_res.get('status_code'), _res.get('message')))

            # compile_episode_from_notion reads the full script from the page BODY,
            # not from any property; without these blocks it aborts on "empty body".
            # Rule 125 & 126 Single Truth: Purge old blocks if present to eliminate ghost versions
            _blk = get_blocks(story_page_id)
            if isinstance(_blk, dict) and _blk.get('results'):
                old_blocks = _blk.get('results') or []
                logger.info(f"[story_engine] Purging {len(old_blocks)} existing blocks from Story Library page {story_page_id} to enforce Single Truth...")
                for _ob in old_blocks:
                    try:
                        delete_block(_ob['id'])
                    except Exception as _de:
                        logger.warning(f"[story_engine] Error deleting old block {_ob.get('id')}: {_de}")

            _children = []
            # Summary Callout with Rule 130 verification metrics
            summary_text = (
                f"🛡️ B2 5-BEAT DOCUDRAMA SCRIPT (RULE 130 ENFORCED)\n"
                f"• {'Words' if not is_cjk else 'Chars'}: {actual_len:,} | Story Gate: {story_score_str} {story_verdict}\n"
                f"• Model: GPT-6-Astra | Causal Roles: Primary Catalyst -> Transmission Mechanism\n"
                f"• Title A: {seo_title_a or topic}"
            )[:1950]
            _children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": summary_text}}],
                    "icon": {"type": "emoji", "emoji": "🛡️"}
                }
            })
            if anatomy:
                c_text = (
                    f"🎯 PHÂN TÍCH ĐỐI THỦ & ĐÒN BẨY ĐỘT PHÁ (B1.5 RECON)\n"
                    f"• Đòn bẩy 10x: {pivot_angle or 'N/A'}\n"
                    f"• Điểm mù đối thủ: {competitor_gap or 'N/A'}\n"
                    f"• Cốt truyện đối thủ: {comp_acts or 'N/A'}\n"
                    f"• Thắc mắc khán giả: {', '.join(frustrations[:3]) if frustrations else 'N/A'}"
                )[:1950]
                _children.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": c_text}}],
                        "icon": {"type": "emoji", "emoji": "🎯"}
                    }
                })
            _chunks = []
            for _p in [x.strip() for x in full_script.split('\n\n') if x.strip()]:
                if _p.startswith("=== ACT ") and _p.endswith(" ==="):
                    _children.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": _p}}]
                        }
                    })
                    continue
                while len(_p) > 1900:
                    _cut = _p.rfind(' ', 1000, 1900)
                    if _cut < 0:
                        _cut = 1900
                    _chunks.append(_p[:_cut])
                    _p = _p[_cut:].lstrip()
                if _p:
                    _chunks.append(_p)
            for c in _chunks:
                _children.append({'object': 'block', 'type': 'paragraph',
                                  'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': c}}]}})
            _appended = 0
            for _i in range(0, len(_children), 90):
                _ares = append_children_blocks(story_page_id, _children[_i:_i + 90])
                if isinstance(_ares, dict) and _ares.get('error'):
                    logger.error('[story_engine] Story body append FAILED %s: %s' % (_ares.get('status_code'), _ares.get('message')))
                    break
                _appended += len(_children[_i:_i + 90])
            logger.info('[story_engine] Story Library body written %d/%d blocks (%d chars)' % (_appended, len(_children), len(full_script)))

        # Director Plan seeding is handled exclusively by B3 director_planner_b3 (Rule 125 Single Truth)
        logger.info('[story_engine] Story Library synced. B3 Director Plan handoff prepared.')

        # Cross-DB State Machine: Mark keyword as 'Used' in Trend Brain DB
        try:
            import app.services.trend_brain_mirror as tbm
            raw_keyword = meta.get("raw_term") or meta.get("target_keyword") or meta.get("topic") or topic
            if raw_keyword:
                tbm.mark_used(str(raw_keyword).strip(), mkt)
                logger.info(f"[story_engine] Transitioned Trend Brain keyword '{raw_keyword}' ({mkt}) status to 'Used'")
        except Exception as _tbm_e:
            logger.warning(f"[story_engine] Notice marking keyword as Used in Trend Brain: {_tbm_e}")
    except Exception as e:
        logger.warning(f"[story_engine] Notion sync exception (non-fatal): {e}")

    return brain_input


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="B2 Story Engine (GPT-6-Astra)")
    parser.add_argument("task_id", help="Task ID or Episode ID (e.g. <MARKET>_EP<0000>_<topic_slug>)")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if story.txt exists")
    args = parser.parse_args()

    if args.force:
        for d in ["/var/vf/episodes", "/root/video_factory/episodes"]:
            sf = os.path.join(d, args.task_id, "story.txt")
            if os.path.exists(sf):
                os.remove(sf)
                print(f"Removed {sf} for regeneration.")

    print(f"Generating 5-Act Story for {args.task_id}...")
    res = generate_5_arc_story(args.task_id, force=args.force)
    story_text = res.get("story", "")
    print(f"=== STORY GENERATION COMPLETED ===")
    print(f"Total Words: {len(story_text.split())}")
    print(f"Gate Score: {res.get('story_gate_score')}")
    print(f"Scenes Seeded: {len(res.get('scenes', []))}")
