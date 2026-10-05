# app/audit/image_audit.py - Image Quality Audit (Hybrid: Claude Sonnet 5.5 Vision + Rule-based)
# Rule 100 & Rule 122: D1 (Prompt Adherence x0.4) + D2 (Object Accuracy x0.35) + D3 (Visual Logic x0.25)
# Gating: resolution, black_frame, reuse_key_valid (auto-reject if any fail)
# Vision audit: 1 API call/image via HHTech API (claude-sonnet-5-5)

import logging
import os
import json
import re

logger = logging.getLogger(__name__)

MIN_WIDTH = 1024
MIN_HEIGHT = 576
BLACK_LUMINANCE_THRESHOLD = 10
BLACK_FRAME_RATIO = 0.95
REUSE_KEY_PATTERN = r'^[a-z]+-[a-z]+-ep\d+_(bg|fg)_[a-z0-9]+_.+$'

def _check_resolution(image_path):
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            w, h = img.size
            if w >= MIN_WIDTH and h >= MIN_HEIGHT:
                return True, f"OK: {w}x{h}"
            return False, f"FAIL: {w}x{h} < {MIN_WIDTH}x{MIN_HEIGHT}"
    except Exception as e:
        return False, f"ERROR: {e}"

def _check_black_frame(image_path):
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img = img.convert("L")
            pixels = list(img.getdata())
            black_count = sum(1 for p in pixels if p < BLACK_LUMINANCE_THRESHOLD)
            ratio = black_count / len(pixels) if pixels else 1.0
            if ratio >= BLACK_FRAME_RATIO:
                return False, f"FAIL: {ratio:.1%} black pixels"
            return True, f"OK: {ratio:.1%} black pixels"
    except Exception as e:
        return False, f"ERROR: {e}"

def _check_reuse_key(reuse_key):
    if not reuse_key:
        return False, "FAIL: empty reuse key"
    if re.match(REUSE_KEY_PATTERN, reuse_key):
        return True, f"OK: {reuse_key}"
    if "_bg_" in reuse_key or "_fg_" in reuse_key:
        return True, f"OK (relaxed): {reuse_key}"
    return False, f"FAIL: {reuse_key} doesn't match convention"

def _call_vision_audit(image_path, prompt_text):
    try:
        from app.services.image_audit import audit_image_hhtech
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        res = audit_image_hhtech(image_bytes, prompt_text)
        return {
            "d1_score": float(res.get("d1", 5.0)),
            "d1_issues": "; ".join(res.get("issues", [])),
            "d2_score": float(res.get("d2", 5.0)),
            "d2_issues": "",
            "d3_score": float(res.get("d3", 5.0)),
            "d3_issues": "",
            "confidence": float(res.get("confidence", 0.0)),
            "overall_notes": str(res.get("notes", ""))
        }
    except Exception as e:
        logger.warning(f"Claude Sonnet 5.5 vision audit via HHTech failed: {e}")
        return None

def audit_image(content, llm_caller=None):
    image_path = content.get("image_path", "")
    prompt_text = content.get("prompt", "")
    reuse_key = content.get("reuse_key", "")
    axis_scores = {}
    issues = []
    recommendations = []
    llm_used = "rule_only"
    gating_failed = False

    if image_path and os.path.exists(image_path):
        ok, msg = _check_resolution(image_path)
        if not ok:
            gating_failed = True
            issues.append({"severity": "high", "axis": "resolution", "message": f"Resolution failed: {msg}", "fix": "Regenerate at min 1024x576"})
    else:
        issues.append({"severity": "medium", "axis": "resolution", "message": f"Image not found: {image_path}", "fix": "Verify path"})

    if image_path and os.path.exists(image_path):
        ok, msg = _check_black_frame(image_path)
        if not ok:
            gating_failed = True
            issues.append({"severity": "critical", "axis": "black_frame", "message": f"Black frame: {msg}", "fix": "Regenerate - generation failure"})

    ok, msg = _check_reuse_key(reuse_key)
    if not ok:
        issues.append({"severity": "low", "axis": "reuse_key_valid", "message": f"Reuse key invalid: {msg}", "fix": "Follow convention"})

    if gating_failed:
        axis_scores["d1_prompt_adherence"] = 0.0
        axis_scores["d2_object_accuracy"] = 0.0
        axis_scores["d3_visual_logic"] = 0.0
        return axis_scores, issues, recommendations, llm_used

    if image_path and os.path.exists(image_path) and prompt_text:
        vision_result = _call_vision_audit(image_path, prompt_text)
        if vision_result:
            llm_used = "claude_sonnet_5_5_vision"
            d1_score = float(vision_result.get("d1_score", 5.0))
            axis_scores["d1_prompt_adherence"] = d1_score
            if d1_score < 7.0:
                issues.append({"severity": "high" if d1_score < 5.0 else "medium", "axis": "d1_prompt_adherence", "message": f"D1: {d1_score}/10 - {vision_result.get('d1_issues', 'none')}", "fix": "Revise prompt"})
            d2_score = float(vision_result.get("d2_score", 5.0))
            axis_scores["d2_object_accuracy"] = d2_score
            if d2_score < 7.0:
                issues.append({"severity": "high" if d2_score < 5.0 else "medium", "axis": "d2_object_accuracy", "message": f"D2: {d2_score}/10 - {vision_result.get('d2_issues', 'none')}", "fix": "More specific object descriptions"})
            d3_score = float(vision_result.get("d3_score", 5.0))
            axis_scores["d3_visual_logic"] = d3_score
            if d3_score < 7.0:
                issues.append({"severity": "medium", "axis": "d3_visual_logic", "message": f"D3: {d3_score}/10 - {vision_result.get('d3_issues', 'none')}", "fix": "Review prompt logic"})
            confidence = float(vision_result.get("confidence", 0.0))
            if confidence < 0.7:
                issues.append({"severity": "medium", "axis": "confidence", "message": f"Low confidence ({confidence:.2f}) - human gate", "fix": "Manual review in Image Asset Library"})
                recommendations.append({"skill": "/video:prompt", "update": f"Human gate: confidence {confidence:.2f} < 0.7", "priority": "medium", "axis": "confidence"})
            overall_notes = vision_result.get("overall_notes", "")
            if overall_notes:
                recommendations.append({"skill": "/video:prompt", "update": f"Vision notes: {overall_notes}", "priority": "low", "axis": "overall"})
        else:
            llm_used = "rule_only_vision_failed"
            axis_scores["d1_prompt_adherence"] = 5.0
            axis_scores["d2_object_accuracy"] = 5.0
            axis_scores["d3_visual_logic"] = 5.0
            issues.append({"severity": "medium", "axis": "vision", "message": "Claude Sonnet vision failed - manual review needed", "fix": "Check API key/network"})
            recommendations.append({"skill": "/video:prompt", "update": "Claude Sonnet vision failed - manual review", "priority": "medium", "axis": "vision"})
    else:
        axis_scores["d1_prompt_adherence"] = 5.0
        axis_scores["d2_object_accuracy"] = 5.0
        axis_scores["d3_visual_logic"] = 5.0
        if not prompt_text:
            issues.append({"severity": "low", "axis": "vision", "message": "No prompt - vision skipped", "fix": "Provide prompt"})

    return axis_scores, issues, recommendations, llm_used
