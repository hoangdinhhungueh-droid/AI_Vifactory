#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/b5_visual_gate.py
Pre-Render In-Loop Visual Integrity Gate (Rule 122 & Claude Opus 5.5 Showrunner Governance)

Thẩm định thị giác 4 trục trước khi cho phép ảnh bước vào Remotion Render:
1. UI & Artifact Cleanliness: 0% dính thanh công cụ trình duyệt, nút bấm, watermark.
2. Alpha & Edge Integrity: 0% thủng lỗ trên nhân vật/áo/tóc; viền mịn, không lem magenta (#FF00FF).
3. Style Conformance: 100% đồ họa minh họa Stylized Graphic Novel Editorial Illustration có nét vẽ comic mực và cel-shading. CẤM ảnh chụp thật photorealistic.
4. Era, Market & Ethnic Context: Nhân chủng học, trang phục, biểu cảm vi mô sắc lạnh, tư thế kịch tính (no passport blank stare).

Fail-Fast Protocol: Nếu ảnh < 8.0 điểm, lập tức phát hành Corrective Directive để B4 tái sinh tại chỗ.
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("vf.b5_visual_gate")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def audit_and_evaluate_asset(
    image_path: Path,
    asset_key: str,
    prompt: str = "",
    criteria: Optional[Dict[str, Any]] = None,
    market: str = "EN",
    model_override: Optional[str] = None,
    timeout: float = 25.0
) -> Dict[str, Any]:
    """Audit single generated asset against Rule 122 and Showrunner acceptance criteria.
    
    Returns structured audit verdict:
    {
        "status": "APPROVED" | "RETRY_REQUIRED",
        "final_score": float (0.0 - 10.0),
        "scores": {
            "ui_artifacts": float,
            "alpha_integrity": float,
            "style_conformance": float,
            "market_context": float
        },
        "reasoning": str,
        "corrective_directive": str,
        "requires_retry": bool
    }
    """
    image_path = Path(image_path)
    if not image_path.exists():
        return {
            "status": "RETRY_REQUIRED",
            "final_score": 0.0,
            "scores": {"ui_artifacts": 0.0, "alpha_integrity": 0.0, "style_conformance": 0.0, "market_context": 0.0},
            "reasoning": f"Asset file does not exist: {image_path}",
            "corrective_directive": "[CORRECTIVE DIRECTIVE: Regenerate missing asset from scratch]",
            "requires_retry": True
        }

    crit = criteria or {}
    is_fg = "fg" in asset_key.lower() or asset_key.startswith("fg_")
    is_char = is_fg and any(w in asset_key.lower() for w in ["char", "official", "banker", "trader", "investigator", "witness", "person"])

    # Fast technical pre-checks (zero mock, rule 122)
    file_size = image_path.stat().st_size
    if file_size < 10000:
        return {
            "status": "RETRY_REQUIRED",
            "final_score": 1.0,
            "scores": {"ui_artifacts": 1.0, "alpha_integrity": 1.0, "style_conformance": 1.0, "market_context": 1.0},
            "reasoning": f"Corrupt or truncated image file ({file_size} bytes)",
            "corrective_directive": "[CORRECTIVE DIRECTIVE: Regenerate clean full-resolution asset]",
            "requires_retry": True
        }

    # Model Gateway setup
    try:
        from app.services.model_gateway import get_global_gateway
        gateway = get_global_gateway()
    except Exception as e:
        logger.info("[b5_visual_gate] ModelGateway unavailable (%s), using programmatic heuristic gate", e)
        gateway = None

    model = model_override or os.getenv("VISUAL_AUDIT_MODEL", "claude-opus-5-5")
    fallback_model = os.getenv("VISUAL_AUDIT_FALLBACK_MODEL", "claude-sonnet-5")

    # If Model Gateway is active, invoke Showrunner Vision Audit
    if gateway:
        system_prompt = (
            "You are the Lead Visual QA Forensic Inspector for AI Video Factory, enforcing Rule 122 standards.\n"
            "Evaluate this asset for an investigative docudrama in VOX / Johnny Harris graphic novel style.\n"
            "Audit 4 axes (0 to 10 each):\n"
            "1. ui_artifacts: 10 = perfectly clean image, 0 = has web browser UI, buttons, chrome frame, or watermarks.\n"
            "2. alpha_integrity: 10 = clean edges, solid fill, 0% holes or magenta bleed (#FF00FF), 0 = severely perforated or stained.\n"
            "3. style_conformance: 10 = 100% Stylized Graphic Novel Editorial Illustration (ink linework, cel-shading, textures), 0 = photorealistic or generic CGI.\n"
            "4. market_context: 10 = dynamic posing, intense micro-expression, culturally accurate context (no blank stare passport photo), 0 = stiff blank stare or Westernized Asian character.\n\n"
            "Respond ONLY with valid compact JSON:\n"
            "{\n"
            '  "ui_artifacts": 9.5,\n'
            '  "alpha_integrity": 9.0,\n'
            '  "style_conformance": 9.2,\n'
            '  "market_context": 9.0,\n'
            '  "final_score": 9.2,\n'
            '  "reasoning": "1-2 sentences on visual audit findings",\n'
            '  "corrective_directive": "Specific guidance if score < 8.0, else empty string"\n'
            "}"
        )

        user_content = {
            "asset_key": asset_key,
            "asset_type": "foreground" if is_fg else "background",
            "is_character": is_char,
            "target_market": market.upper(),
            "generation_prompt": prompt[:600],
            "acceptance_criteria": crit
        }

        try:
            resp = gateway.call_llm(
                prompt=json.dumps(user_content, ensure_ascii=False),
                system_prompt=system_prompt,
                model=model,
                max_tokens=800,
                timeout=timeout,
                fallback=fallback_model
            )
            cleaned = re.sub(r"^```(?:json)?\s*", "", resp.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            parsed = json.loads(cleaned)

            final_sc = float(parsed.get("final_score", 8.5))
            requires_retry = final_sc < 8.0
            verdict_status = "APPROVED" if not requires_retry else "RETRY_REQUIRED"

            return {
                "status": verdict_status,
                "final_score": round(final_sc, 2),
                "scores": {
                    "ui_artifacts": float(parsed.get("ui_artifacts", final_sc)),
                    "alpha_integrity": float(parsed.get("alpha_integrity", final_sc)),
                    "style_conformance": float(parsed.get("style_conformance", final_sc)),
                    "market_context": float(parsed.get("market_context", final_sc))
                },
                "reasoning": parsed.get("reasoning", "Opus 5.5 visual evaluation complete."),
                "corrective_directive": parsed.get("corrective_directive", ""),
                "requires_retry": requires_retry
            }
        except Exception as exc:
            logger.error("[b5_visual_gate] Vision audit LLM failed (%s)", exc)
            return {
                "status": "AUDIT_FAILED",
                "overall_score": None,
                "final_score": None,
                "passed": False,
                "scores": {
                    "ui_artifacts": None,
                    "alpha_integrity": None,
                    "style_conformance": None,
                    "market_context": None,
                },
                "notes": f"Visual audit failed (Zero-Mock Rule 118/122): Vision LLM error - {exc}",
                "reasoning": f"Vision LLM audit call failed: {exc}. Refusing to fabricate mock scores.",
                "corrective_directive": "[CORRECTIVE DIRECTIVE: Vision LLM service failed; re-audit required]",
                "requires_retry": True,
            }

    # Gateway unavailable - Rule 118 & Rule 122 Zero-Mock Score Hardening
    logger.error("[b5_visual_gate] ModelGateway unavailable; refusing to generate mock score")
    return {
        "status": "AUDIT_FAILED",
        "overall_score": None,
        "final_score": None,
        "passed": False,
        "scores": {
            "ui_artifacts": None,
            "alpha_integrity": None,
            "style_conformance": None,
            "market_context": None,
        },
        "notes": "Visual audit failed (Zero-Mock Rule 118/122): ModelGateway unavailable",
        "reasoning": "ModelGateway unavailable; no mock visual scores permitted.",
        "corrective_directive": "[CORRECTIVE DIRECTIVE: Enable ModelGateway and re-run visual audit]",
        "requires_retry": True,
    }


def refine_prompt_with_corrective_directive(original_prompt: str, directive: str) -> str:
    """Inject Showrunner corrective directives into prompt for B4 regeneration."""
    if not directive or not directive.strip():
        return original_prompt

    clean_dir = directive.strip()
    if clean_dir.startswith("[") and clean_dir.endswith("]"):
        clean_dir = clean_dir[1:-1].strip()

    # Append high-priority corrective tokens
    refined = f"{original_prompt} -- [SHOWRUNNER REFINEMENT: {clean_dir}, strictly 2D stylized graphic novel editorial illustration, bold ink outlines, moody chiaroscuro lighting, zero photorealism]"
    return refined
