#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/generate_vox_b3_director.py
Sinh bảng Director Plan & Prompt sinh ảnh B3 theo chuẩn Prompt 2 (Made by AI)
và kích hoạt Hội đồng Thẩm định LLM Đối kháng (Astra 6 & Opus 5.5).
"""

import sys
import os
import json
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.services.model_gateway import get_global_gateway
from app.services.vox_critic_council import audit_director_plan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_vox_b3_director")

PROMPT_FILE = ROOT_DIR / "config" / "prompts" / "vox_b3_director_image_prompt.md"

def generate_b3_director(episode_dir: Path, episode_id: str = "KR_EP0001_google_kr_tax_loss") -> dict:
    logger.info(f"🎬 BẮT ĐẦU SINH DIRECTOR PLAN & PROMPT B3 CHO EPISODE [{episode_id}]...")

    script_path = episode_dir / "b2_script.json"
    if not script_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file kịch bản tại {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        director_instruction = f.read()

    full_script = script_data.get("full_spoken_script", "")
    if not full_script:
        # Combine acts
        acts = [script_data.get(f"act_{i}", "") for i in range(1, 6)]
        full_script = " ".join([a for a in acts if a])

    user_payload = f"""[DOCUMENTARY SCRIPT INGESTION]
Episode Title: "{script_data.get('title', episode_id)}"
Target Market: "{script_data.get('market', 'KR')}"

Full Script Text:
\"\"\"{full_script}\"\"\"

[TASK INSTRUCTIONS]
Transform this entire investigative documentary script into a sequence of premium VOX-style editorial AI image prompts following the exact Master Prompt instructions.
Apply Hybrid Beat-Pacing:
- Divide into 20 - 30 scenes (~4-6s per scene matching narration rhythm).
- For each scene, determine:
  1. scene_id: "SCENE_01", "SCENE_02", ...
  2. timeframe: "00:00 - 00:05", "00:05 - 00:10", ...
  3. sentence: Exact spoken narration sentence(s) in Korean.
  4. core_idea: 1-2 words abstract concept (e.g. "Tax Loophole", "Asymmetric Loss", "Corporate Shield").
  5. editorial_title: 1-4 words bold documentary headline (e.g. "TAX REVERSAL", "PERMANENT ESTABLISHMENT", "THE SHELL GAME").
  6. visual_metaphor: Concrete symbolic object (e.g. "Scales weighing Server against Tax Vault", "Court Gavel with Digital Circuitry").
  7. layering: Summary of paper layers (Background paper -> Geometric shape -> Typography -> Cutout subject -> Supporting object -> Texture).
  8. image_prompt: Complete detailed prompt in English strictly following Vox paper collage style, editorial cutouts, muted 2-4 accent colors, and the negative prompt at the end.

Output JSON matching this exact structure:
{{
  "episode_id": "{episode_id}",
  "title": "{script_data.get('title', episode_id)}",
  "scenes": [
    {{
      "scene_id": "SCENE_01",
      "timeframe": "00:00 - 00:05",
      "sentence": "<Korean narration>",
      "core_idea": "<Concept>",
      "editorial_title": "<1-4 words bold headline>",
      "visual_metaphor": "<Symbolic object>",
      "layering": "<Layer breakdown>",
      "image_prompt": "<Full English prompt with negative prompt>"
    }}
  ]
}}
"""

    gateway = get_global_gateway()
    raw_response = gateway.call_llm(
        prompt=user_payload,
        system_prompt=director_instruction,
        model="claude-sonnet-5-5",
        temperature=0.4,
        max_tokens=6000
    )

    cleaned = raw_response.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    director_data = json.loads(cleaned)

    # Enrich with Kinetic Sub-Director Plan (Rule 140 / Vox Engine v3)
    try:
        from app.services.kinetic_sub_director import (
            build_kinetic_causal_i2v_prompt,
            generate_scene_sub_director_plan,
        )
        from core.market_resolver import resolve_canonical_market

        mkt = script_data.get("market") or (episode_id.split("_")[0] if "_" in episode_id else "EN")
        resolved_mkt = resolve_canonical_market(market_raw=mkt)
        for sc in director_data.get("scenes", []):
            sc_id = sc.get("scene_id", "SCENE_01")
            sc_text = sc.get("sentence", "") or sc.get("narration", "") or sc.get("core_idea", "")
            sc_hero = sc.get("visual_metaphor", "") or sc.get("editorial_title", "")
            raw_dur = sc.get("duration_sec") or sc.get("duration_est_sec") or 5.0
            sub_plan = generate_scene_sub_director_plan(
                scene_id=sc_id,
                sentence=sc_text,
                hero_cutout_object=sc_hero,
                interacting_objects=sc.get("interacting_objects"),
                duration_sec=float(raw_dur),
                market=resolved_mkt,
            )
            i2v_p = build_kinetic_causal_i2v_prompt(sub_plan, camera_directive=sc.get("camera_directive", "STATIC_OVERHEAD"))
            sc["scene_sub_director_plan"] = sub_plan
            sc["interacting_objects"] = [o["label"] for o in sub_plan.get("object_roster", []) if o.get("role") != "primary_anchor"]
            sc["flow_video_prompt"] = i2v_p
            sc["i2v_prompt_google_flow"] = i2v_p
            sc["i2v_prompt_omni"] = i2v_p

        from stages.s05_director_plan import generate_7acc_flow_manifest
        generate_7acc_flow_manifest(episode_dir, episode_id, director_data.get("scenes", []))
    except (ValueError, TypeError, KeyError, ImportError) as _ex:
        logger.warning(f"Kinetic sub-director enrichment notice: {_ex}")

    # Lưu director_plan.json
    out_file = episode_dir / "director_plan.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(director_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ ĐÃ SINH BẢNG DIRECTOR PLAN ({len(director_data.get('scenes', []))} SCENES) TẠI: {out_file}")

    # 3. KÍCH HOẠT HỘI ĐỒNG THẨM ĐỊNH LLM ĐỐI KHÁNG (ASTRA 6 + OPUS 5.5)
    logger.info("⚖️ KÍCH HOẠT HỘI ĐỒNG THẨM ĐỊNH (ASTRA 6 & OPUS 5.5)...")
    hook_text = full_script[:300]
    audit_verdict = audit_director_plan(
        episode_id=episode_id,
        director_plan=director_data.get("scenes", []),
        script_hook=hook_text
    )

    review_file = episode_dir / "critic_council_review.json"
    with open(review_file, "w", encoding="utf-8") as f:
        json.dump(audit_verdict, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ ĐÃ HOÀN TẤT THẨM ĐỊNH ĐỐI KHÁNG: VERDICT = {audit_verdict.get('verdict')} (SCORE: {audit_verdict.get('overall_score')}/10)")
    return {
        "director_plan": director_data,
        "critic_review": audit_verdict
    }

if __name__ == "__main__":
    ep_dir = ROOT_DIR / "episodes" / "KR_EP0001_google_kr_tax_loss"
    generate_b3_director(ep_dir)
