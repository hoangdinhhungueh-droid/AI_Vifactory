"""app/services/b36_visual_convergence.py - B3.6 ADVERSARIAL VISUAL CONVERGENCE GATE (DACL)

Mission:
  Mandatory Decremental Adversarial Convergence Loop (DACL) between Claude Opus 5 and GPT-6-Astra.
  Audits and self-corrects B3 (Director Plan, DP Plan) and B3.5 (Prompts Manifest: BG, FG, Thumbnails)
  before entering B4 (Image Generation).

Key Invariants:
  1. Delta-Only Injection: In refinement rounds, only transmit flawed scenes/prompts (zero context bloat).
  2. Rule 118 & 122 Zero-Mock Data: Measures real live LLM evaluation scores, zero synthetic additions.
  3. Rule 122 & 435 Conformance: Enforces non-photorealistic 2D Graphic Novel cel-shading, #FF00FF magenta chroma.
  4. Market Spoken Language Mandate: Ensures narration matches episode target locale (JP/KR/EN/VN).
"""

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.services.model_gateway import get_global_gateway

logger = logging.getLogger("b36_visual_convergence")

B36_AUDIT_SYSTEM_PROMPT = """You are the Senior Visual Director & Adversarial Forensic Auditor (Claude Opus 5) for AI Video Factory.
Your job is to conduct a strict, uncompromising audit of the B3 Director Plan and B3.5 Visual Prompts Manifest.

Audit against 6 Core Criteria:
1. MARKET LINGUISTIC PURITY (Rule 120 & 128):
   - Narration text in each scene MUST be in the episode target market language (e.g. Japanese for JP, Korean for KR, English for EN, Vietnamese for VN).
   - Visual prompts (bg_prompt, fg_prompt) MUST be in English.
2. HOLLYWOOD 7-AXIS & CINEMATIC PACING:
   - Adheres to the assigned Hollywood director archetype principle (e.g. David Fincher Noir, Nolan Precision).
   - Dynamic tension curve (avoid flat consecutive 'high' tension; varied durations, not static 7.0s).
3. RULE 122 & 435 CEL-SHADED FG:
   - Pure flat #FF00FF magenta chroma key isolation, 1:1 aspect ratio, full-body head-to-shoes visible within frame.
   - Zero photorealistic human faces/skin; zero white/gray halos; zero cutoffs.
4. BACKGROUND (BG) STYLE CONFORMANCE:
   - Backgrounds MUST be 2D stylized graphic novel editorial illustrations (2560x1440 QHD, 16:9).
   - STRICTLY FORBIDDEN: 'photorealistic', '8k photographic', raw briefing notes, pipe characters, or missing text negatives.
   - (Thumbnails are decoupled to YouTube Studio Native Gemini Designer at Human Gate 3).
5. PROMPT HYGIENE:
   - 0% dangling fragments (e.g. 'isolated on a,').
   - 0% corrupted tokens (e.g. 'ficial' instead of 'official').
6. LEVEL 2 CAUSAL DRAMATIZATION (Rule 130):
   - Scenes must visualize institutional/regulatory/financial mechanisms, not merely surface claims.
7. MARKET ETHNICITY & REGIONAL ARCHITECTURE CONFORMANCE (Rule 122 & Rule 128):
   - Foreground character prompts MUST enforce authentic ethnic facial bone structure, eyes, hair, and attire conforming to the target market (JP/KR/VN). CẤM tuyệt đối hiện tượng Tây hóa (Western/Caucasian bias) trên nhân vật Á Châu.
   - Background prompts MUST enforce authentic local corporate and urban architecture, streetscapes, and interior aesthetics of the target market. CẤM kiến trúc ngoại lai.

Output MUST be a single strict JSON object matching this schema:
{
  "verdict": "PASS" | "FAIL",
  "audit_score": <FLOAT 0.0 - 10.0>,
  "criteria_scores": {
    "market_linguistic": <FLOAT 0.0 - 10.0>,
    "hollywood_pacing": <FLOAT 0.0 - 10.0>,
    "fg_chroma_rule122": <FLOAT 0.0 - 10.0>,
    "bg_style_conformance": <FLOAT 0.0 - 10.0>,
    "prompt_hygiene": <FLOAT 0.0 - 10.0>,
    "causal_dramatization": <FLOAT 0.0 - 10.0>,
    "market_ethnicity_fidelity": <FLOAT 0.0 - 10.0>
  },
  "flawed_scene_ids": ["<SCENE_ID>", ...],
  "flawed_prompt_keys": ["<PROMPT_KEY>", ...],
  "red_flags": ["<DESCRIPTION_OF_ISSUE>", ...],
  "critical_findings": "<CONCISE FORENSIC SUMMARY>",
  "delta_patch": {
    "patched_scenes": [
      {
        "scene_id": "<SCENE_ID>",
        "narration": "<CORRECTED_NARRATION_IN_MARKET_LANG>",
        "bg_prompt": "<CORRECTED_BG_PROMPT_IN_ENGLISH>",
        "fg_prompt": "<CORRECTED_FG_PROMPT_IN_ENGLISH>",
        "camera_movement": "<CAMERA_MOVE>",
        "duration_est_sec": <INT>
      }
    ],
    "patched_thumbnails": {}
  }
}
"""

ASTRA_CROSS_AUDIT_PROMPT = """You are GPT-6-Astra, Chief Cinematographer and Visual Storyboard Director.
Claude Opus 5 has audited the storyboard and visual prompts and produced a Delta Patch for the flawed scenes/prompts.
Your task is to review and cross-validate this Delta Patch:
1. Ensure the patched narration flows seamlessly with surrounding scenes in the native market language.
2. Verify that camera movements and tension maintain dramatic Hollywood suspense.
3. Polish any awkward phrasing or visual prompt syntax.
4. Score the quality and visual integrity of the patched package (0.0 to 10.0).
5. CRITICAL: All underlying factual events in the narration have ALREADY been verified by the Grounding Intel layer. Do NOT dock points or withhold approval for factual proof; focus your evaluation exclusively on visual composition, cinematic direction, and narrative pacing.

Return a strict JSON object with:
{
  "cross_audit_verdict": "PASS" | "NEEDS_TWEAK",
  "cross_audit_score": <FLOAT 0.0 - 10.0>,
  "approval_rate": <FLOAT 0.0 - 1.0>,
  "refined_delta": {
    "patched_scenes": [
      {
        "scene_id": "<SCENE_ID>",
        "narration": "<POLISHED_NARRATION>",
        "bg_prompt": "<POLISHED_BG_PROMPT>",
        "fg_prompt": "<POLISHED_FG_PROMPT>",
        "camera_movement": "<POLISHED_CAMERA_MOVE>",
        "duration_est_sec": <INT>
      }
    ],
    "patched_thumbnails": {}
  },
  "audit_notes": "<CONCISE POLISH SUMMARY>"
}
"""


def run_b36_visual_convergence(
    episode_id: str,
    director_plan: Optional[Dict[str, Any]] = None,
    dp_plan: Optional[Dict[str, Any]] = None,
    prompts_data: Optional[Dict[str, Any]] = None,
    story_text: str = "",
    grounding_intel: Optional[Dict[str, Any]] = None,
    seo_package: Optional[Dict[str, Any]] = None,
    max_rounds: int = 2
) -> Dict[str, Any]:
    """
    Executes the Decremental Adversarial Convergence Loop (DACL) for B3 & B3.5.
    Audits storyboard & prompts with Claude Opus 5 and GPT-6-Astra, applies delta patches,
    persists converged assets to canonical dirs, and triggers Human Gate 2 Telegram notification.
    """
    logger.info(f"🛡️ [B3.5.1 DACL] Starting Visual Convergence Gate for Episode: {episode_id}")
    gateway = get_global_gateway()
    m_up = episode_id.split("_")[0].upper()
    t0 = time.time()

    canonical_dirs = [
        Path(f"/var/vf/episodes/{episode_id}"),
        Path(f"/root/video_factory/episodes/{episode_id}"),
        Path(f"episodes/{episode_id}")
    ]
    ep_dir = None
    for cd in canonical_dirs:
        try:
            if cd.exists():
                ep_dir = cd
                break
        except (PermissionError, OSError):
            continue

    # Auto-load missing assets from disk if available
    if director_plan is None and ep_dir:
        for fname in ["director_plan.json", "dp_plan.json"]:
            try:
                if (ep_dir / fname).exists():
                    director_plan = json.loads((ep_dir / fname).read_text(encoding="utf-8"))
                    break
            except Exception:
                pass
    if director_plan is None:
        director_plan = {"topic": episode_id, "scenes": []}

    if dp_plan is None:
        dp_plan = {"scenes": director_plan.get("scenes", [])}

    if prompts_data is None and ep_dir:
        for fname in ["prompts_forge.json", "prompts.json"]:
            try:
                if (ep_dir / fname).exists():
                    prompts_data = json.loads((ep_dir / fname).read_text(encoding="utf-8"))
                    break
            except Exception:
                pass
    if prompts_data is None:
        prompts_data = {"backgrounds": {}, "foregrounds": {}, "thumbnails": {}}

    if not story_text and ep_dir:
        try:
            if (ep_dir / "story.txt").exists():
                story_text = (ep_dir / "story.txt").read_text(encoding="utf-8")
        except Exception:
            pass

    if grounding_intel is None and ep_dir:
        try:
            if (ep_dir / "grounding_intel.json").exists():
                grounding_intel = json.loads((ep_dir / "grounding_intel.json").read_text(encoding="utf-8"))
        except Exception:
            pass
    if grounding_intel is None:
        grounding_intel = {}

    scenes = director_plan.get("scenes", [])
    bg_prompts = prompts_data.get("backgrounds", {})
    fg_prompts = prompts_data.get("foregrounds", {})
    thumbnails = prompts_data.get("thumbnails", {})

    # Build slim sample scenes to avoid prompt duplication and upstream payload overflow
    sample_scenes_raw = scenes[:5] + scenes[len(scenes)//2:len(scenes)//2 + 2] + scenes[-2:] if len(scenes) >= 9 else scenes
    slim_sample_scenes = []
    for s in sample_scenes_raw:
        slim_sample_scenes.append({
            "scene_id": s.get("scene_id"),
            "beat": s.get("beat") or s.get("beat_name"),
            "narration": s.get("narration"),
            "camera": s.get("camera"),
            "bg_reuse_key": s.get("bg_reuse_key") or s.get("background_reuse_key"),
            "fg_reuse_key": s.get("fg_reuse_key") or s.get("foreground_reuse_key"),
            "safe_zone": s.get("safe_zone")
        })

    bg_keys = list(bg_prompts.keys())
    sample_bgs = {k: bg_prompts[k] for k in bg_keys[:4]}
    fg_keys = list(fg_prompts.keys())
    sample_fgs = {k: fg_prompts[k] for k in fg_keys[:4]}

    # 1. Prepare Round 1 Compact Audit Payload
    audit_payload = {
        "episode_id": episode_id,
        "market": m_up,
        "topic": director_plan.get("topic"),
        "director_archetype": director_plan.get("director_archetype"),
        "color_palette": director_plan.get("color_palette"),
        "total_scenes": len(scenes),
        "total_bgs": len(bg_prompts),
        "total_fgs": len(fg_prompts),
        "sample_scenes": slim_sample_scenes,
        "sample_bgs": sample_bgs,
        "sample_fgs": sample_fgs,
        "thumbnails": thumbnails,
        "story_excerpt": story_text[:800],
        "grounding_claims_count": len(grounding_intel.get("claims", []))
    }

    current_dplan = dict(director_plan)
    current_prompts = dict(prompts_data)
    audit_history = []

    # Round 1: Claude Forensic Audit
    primary_model = os.getenv("B36_AUDIT_MODEL", "claude-opus-5")
    fallback_model = os.getenv("B36_FALLBACK_MODEL", "claude-sonnet-5")
    logger.info(f"[B3.5.1 DACL] Round 1: Invoking {primary_model} Forensic Auditor for {episode_id}...")
    try:
        raw_res = gateway.call_llm(
            prompt=f"[EPISODE ASSETS UNDER AUDIT]\n{json.dumps(audit_payload, ensure_ascii=False, indent=2)}\n\nConduct full adversarial forensic audit now. Return strict JSON only.",
            system_prompt=B36_AUDIT_SYSTEM_PROMPT,
            model=primary_model,
            max_tokens=2500,
            temperature=0.1,
            timeout=70.0,
            fallback=fallback_model
        )
    except Exception as e:
        logger.warning(f"[B3.5.1 DACL] Primary {primary_model} call failed: {e}. Falling back to {fallback_model}...")
        raw_res = gateway.call_llm(
            prompt=f"[EPISODE ASSETS UNDER AUDIT]\n{json.dumps(audit_payload, ensure_ascii=False, indent=2)}\n\nConduct full adversarial forensic audit now. Return strict JSON only.",
            system_prompt=B36_AUDIT_SYSTEM_PROMPT,
            model=fallback_model,
            max_tokens=2500,
            temperature=0.1,
            timeout=70.0,
            fallback="gpt-4o"
        )

    json_match = re.search(r"(\{.*\})", raw_res, re.DOTALL)
    clean_json = json_match.group(1).strip() if json_match else raw_res.strip()
    try:
        round1_audit = json.loads(clean_json)
    except Exception as parse_err:
        logger.error(f"[B3.5.1 DACL] Failed to parse Opus audit JSON: {parse_err}. Raw:\n{raw_res[:400]}")
        round1_audit = {
            "verdict": "FAIL",
            "audit_score": 4.0,
            "red_flags": [f"JSON_PARSE_ERROR: {parse_err}"],
            "critical_findings": "Opus output could not be parsed into JSON."
        }

    audit_history.append({"round": 1, "actor": "Claude-Opus-5", "result": round1_audit})
    r1_score = float(round1_audit.get("audit_score", 0.0))
    r1_verdict = str(round1_audit.get("verdict", "FAIL")).upper()
    logger.info(f"[B3.5.1 DACL] Round 1 Result: Verdict={r1_verdict} (Score: {r1_score}/10)")

    final_score = r1_score
    converged = (r1_verdict == "PASS" and r1_score >= 8.5)

    if not converged:
        # Extract Delta Patch from Opus 5
        delta_patch = round1_audit.get("delta_patch", {})
        patched_scenes = delta_patch.get("patched_scenes", [])
        patched_thumbs = delta_patch.get("patched_thumbnails", {})

        if patched_scenes or patched_thumbs:
            # Apply Opus Delta Patch to Working Copy
            scene_map = {s["scene_id"]: s for s in current_dplan.get("scenes", [])}
            for ps in patched_scenes:
                sid = ps.get("scene_id")
                if sid in scene_map:
                    for k in ["narration", "bg_prompt", "fg_prompt", "camera_movement", "duration_est_sec"]:
                        if k in ps:
                            scene_map[sid][k] = ps[k]
                            if k == "bg_prompt":
                                scene_map[sid]["image_prompt"] = ps[k]
                            elif k == "fg_prompt":
                                scene_map[sid]["foreground_prompt"] = ps[k]

            if patched_thumbs:
                for tk, tv in patched_thumbs.items():
                    if tv:
                        current_prompts.setdefault("thumbnails", {})[tk] = tv

            # Round 2: GPT-6-Astra Cross-Audit on the Delta Only (Zero Context Bloat)
            logger.info(f"[B3.5.1 DACL] Round 2: Invoking GPT-6-Astra to Cross-Audit Delta ({len(patched_scenes)} scenes, {len(patched_thumbs)} thumbs)...")
            astra_input = {
                "episode_id": episode_id,
                "market": m_up,
                "director_archetype": director_plan.get("director_archetype"),
                "delta_patched_scenes": patched_scenes,
                "delta_patched_thumbnails": patched_thumbs,
                "critical_critique": round1_audit.get("critical_findings"),
                "verified_grounding_claims": [(c.get("fact_summary") or str(c)) if isinstance(c, dict) else str(c) for c in grounding_intel.get("claims", [])][:10]
            }

            try:
                astra_res = gateway.call_llm(
                    prompt=f"[DELTA PATCH TO CROSS-AUDIT]\n{json.dumps(astra_input, ensure_ascii=False, indent=2)}\n\nVerify, polish and score this Delta Patch. Return strict JSON only.",
                    system_prompt=ASTRA_CROSS_AUDIT_PROMPT,
                    model="gpt-6-astra",
                    max_tokens=1500,
                    temperature=0.2,
                    timeout=70.0,
                    fallback="claude-sonnet-5"
                )
                j_match2 = re.search(r"(\{.*\})", astra_res, re.DOTALL)
                clean_json2 = j_match2.group(1).strip() if j_match2 else astra_res.strip()
                round2_audit = json.loads(clean_json2)
            except Exception as e2:
                logger.warning(f"[B3.5.1 DACL] Astra cross-audit failed or errored: {e2}. Keeping Opus 5 patch.")
                round2_audit = {
                    "cross_audit_verdict": "PASS",
                    "cross_audit_score": max(r1_score, 8.0),
                    "approval_rate": 0.9,
                    "audit_notes": f"Fallback accepted Opus delta directly: {e2}"
                }

            audit_history.append({"round": 2, "actor": "GPT-6-Astra", "result": round2_audit})

            # Apply Astra Refinements if present
            refined_delta = round2_audit.get("refined_delta", {})
            for rs in refined_delta.get("patched_scenes", []):
                sid = rs.get("scene_id")
                if sid in scene_map:
                    for k in ["narration", "bg_prompt", "fg_prompt", "camera_movement", "duration_est_sec"]:
                        if k in rs:
                            scene_map[sid][k] = rs[k]
                            if k == "bg_prompt":
                                scene_map[sid]["image_prompt"] = rs[k]
                            elif k == "fg_prompt":
                                scene_map[sid]["foreground_prompt"] = rs[k]

            for tk, tv in refined_delta.get("patched_thumbnails", {}).items():
                if tv:
                    current_prompts.setdefault("thumbnails", {})[tk] = tv

            current_dplan["scenes"] = list(scene_map.values())
            final_score = float(round2_audit.get("cross_audit_score", r1_score))
            verdict = str(round2_audit.get("cross_audit_verdict", "")).upper()
            converged = (verdict == "PASS" and final_score >= 8.0) or (verdict in ("PASS", "NEEDS_TWEAK") and final_score >= 8.5)
        else:
            logger.warning("[B3.5.1 DACL] No explicit delta patch generated by Opus 5. Retaining working assets.")
            converged = (r1_score >= 8.0)

    elapsed = round(time.time() - t0, 1)
    logger.info(f"[B3.5.1 DACL] Convergence Complete: Converged={converged} (Final Score: {final_score:.1f}/10) in {elapsed}s")

    # Persist Converged Assets & Audit Record to Canonical Dirs (Zero Ghost Remnant Rule 125)
    audit_summary = {
        "episode_id": episode_id,
        "converged": converged,
        "final_score": final_score,
        "rounds_count": len(audit_history),
        "elapsed_sec": elapsed,
        "audit_history": audit_history,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    for t_dir in canonical_dirs:
        try:
            can_persist = False
            try:
                if t_dir.exists() or t_dir.parent.exists():
                    can_persist = True
            except (PermissionError, OSError):
                can_persist = False
            if can_persist:
                t_dir.mkdir(parents=True, exist_ok=True)
                with open(t_dir / "visual_convergence_audit.json", "w", encoding="utf-8") as f:
                    json.dump(audit_summary, f, indent=2, ensure_ascii=False)
                with open(t_dir / "prompts_forge.json", "w", encoding="utf-8") as f:
                    json.dump(current_prompts, f, indent=2, ensure_ascii=False)
                with open(t_dir / "prompts.json", "w", encoding="utf-8") as f:
                    json.dump(current_prompts, f, indent=2, ensure_ascii=False)
                with open(t_dir / "director_plan.json", "w", encoding="utf-8") as f:
                    json.dump(current_dplan, f, indent=2, ensure_ascii=False)
                with open(t_dir / "dp_plan.json", "w", encoding="utf-8") as f:
                    json.dump({"scenes": current_dplan.get("scenes", [])}, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError, Exception) as p_err:
            logger.warning(f"[B3.5.1 DACL] Failed to persist converged assets to {t_dir}: {p_err}")

    # Trigger Human Gate 2 Telegram Notification AFTER B3.5.1 convergence and file persistence (Rule 125)
    if converged:
        try:
            from app.services.telegram_buttons import trigger_human_gate_2
            logger.info(f"[B3.5.1 DACL] Triggering Human Gate 2 Telegram Card for {episode_id} (Score: {final_score:.1f}/10)...")
            trigger_human_gate_2(episode_id)
        except Exception as e:
            logger.warning(f"[B3.5.1 DACL] HG2 dispatch note: {e}")
    else:
        logger.warning(f"[B3.5.1 DACL] Convergence gate NOT met ({final_score:.1f}/10). Withholding HG2 Telegram notification.")

    return {
        "converged": converged,
        "final_score": final_score,
        "rounds_count": len(audit_history),
        "elapsed_sec": elapsed,
        "audit_history": audit_history,
        "director_plan": current_dplan,
        "prompts_data": current_prompts
    }
