#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/generate_vox_b2_story.py
Sinh kịch bản điều tra B2 (5-Beat Docudrama) từ ứng viên Candidate Step 1.
Nạp quy chuẩn biên tập từ config/prompts/b2_editorial_prompt.md qua ModelGateway.
"""

import sys
import os
import json
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.model_gateway import get_global_gateway

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_vox_b2_story")

PROMPT_FILE = ROOT_DIR / "config" / "prompts" / "b2_editorial_prompt.md"

def generate_b2_story(candidate_dir: Path, output_dir: Path, market: str = "KR") -> Path:
    logger.info(f"🚀 BẮT ĐẦU SINH KỊCH BẢN B2 (5-BEAT DOCUDRAMA) CHO MARKET [{market}]...")

    card_path = candidate_dir / "competitor_intel_card.json"
    grounding_path = candidate_dir / "grounding_intel.json"

    if not card_path.exists() or not grounding_path.exists():
        raise FileNotFoundError(f"Thiếu file candidate tại {candidate_dir}")

    with open(card_path, "r", encoding="utf-8") as f:
        card_data = json.load(f)
    with open(grounding_path, "r", encoding="utf-8") as f:
        grounding_data = json.load(f)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        editorial_rules = f.read()

    keyword = card_data.get("target_keyword", "")
    niche = card_data.get("niche", "Trending Investigative")
    anatomy = card_data.get("competitor_narrative_anatomy", {})
    vacuum = anatomy.get("fatal_explanatory_vacuum", "")
    pivot_angle = anatomy.get("our_10x_angle", anatomy.get("our_10x_pivot_angle", ""))

    golden_facts = grounding_data.get("golden_facts", grounding_data.get("facts", []))
    chronology = grounding_data.get("chronology", grounding_data.get("timeline", []))

    user_prompt = f"""[CANDIDATE INTELLIGENCE]
Target Keyword: "{keyword}"
Niche: "{niche}"
Market: "{market}"

Competitor Fatal Explanatory Vacuum:
{vacuum}

Our 10X Pivot Angle:
{pivot_angle}

Golden Factual Data:
{json.dumps(golden_facts, ensure_ascii=False, indent=2)}

Chronology / Timeline:
{json.dumps(chronology, ensure_ascii=False, indent=2)}

[TASK REQUIREMENT]
Write a complete, highly engaging 5-Beat Docudrama Script in KOREAN (Hangul) following the exact B2 Investigative Docudrama Editorial Rules provided in the system prompt.
Total Length: 1,800 - 2,200 words (~3,200 - 3,600 Hangul syllables).
Make sure to satisfy all 5 Acts:
- Act I: Impossible Contradiction & Cold Strike (Lead with exact numbers in first 60 words: 1,540억 won vs $0 permanent establishment).
- Act II: False Narrative & The Amazon Contrast (Amazon conceded 1,500억 won, Google appealed and won).
- Act III: Systemic Blindspot & Paper Trail (Permanent establishment legal loophole, transfer pricing fee, cost-plus marketing contract).
- Act IV: The Smoking Gun & Climax (The court verdict, NTS evidentiary breakdown).
- Act V: Modern Mirror & Living Warning (Global digital tax reforms, OECD Pillar One, ongoing public revenue leak).

Output JSON matching this exact structure:
{{
  "title": "<Catchy Korean Investigative Title>",
  "topic_slug": "google_kr_tax_loss",
  "market": "{market}",
  "act_1_cold_strike": "<Act 1 Hangul text>",
  "act_2_false_narrative": "<Act 2 Hangul text>",
  "act_3_paper_trail": "<Act 3 Hangul text>",
  "act_4_smoking_gun": "<Act 4 Hangul text>",
  "act_5_modern_mirror": "<Act 5 Hangul text>",
  "full_spoken_script": "<Combined continuous voiceover narrative text>"
}}
"""

    gateway = get_global_gateway()
    raw_response = gateway.call_llm(
        prompt=user_prompt,
        system_prompt=editorial_rules,
        model="claude-sonnet-5-5",
        temperature=0.4,
        max_tokens=6000
    )

    cleaned = raw_response.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    script_data = json.loads(cleaned)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "b2_script.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ ĐÃ SINH XONG KỊCH BẢN B2 TẠI: {out_file}")
    return out_file

if __name__ == "__main__":
    cand_dir = ROOT_DIR / "active_candidate"
    ep_dir = ROOT_DIR / "episodes" / "KR_EP0001_google_kr_tax_loss"
    generate_b2_story(cand_dir, ep_dir, market="KR")
