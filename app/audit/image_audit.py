# app/audit/image_audit.py - Image Quality Audit (Hybrid: Gemini Flash-Lite Vision + Rule-based)
# Rule 100: D1 (Prompt Adherence x0.4) + D2 (Object Accuracy x0.35) + D3 (Visual Logic x0.25)
# Gating: resolution, black_frame, reuse_key_valid (auto-reject if any fail)
# Gemini Flash-Lite vision: 1 API call/image, ~1s, 0 RAM, free tier 1,500 RPD

import logging
import os
import json
import re

logger = logging.getLogger(__name__)

_GEMINI_MODEL = "claude-sonnet-5-5"
_GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent"
_GEMINI_TIMEOUT = 15
_GEMINI_FAILURE_COUNT = 0
_GEMINI_FAILURE_THRESHOLD = 3

MIN_WIDTH = 1024
MIN_HEIGHT = 576
BLACK_LUMINANCE_THRESHOLD = 10
BLACK_FRAME_RATIO = 0.95
REUSE_KEY_PATTERN = r'^[a-z]+-[a-z]+-ep\d+_(bg|fg)_[a-z0-9]+_.+$'

def _get_gemini_key():
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
        val = os.environ.get(var, "")
        if val:
            return val
    return ""

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

def _call_gemini_vision(image_path, prompt_text, api_key):
    global _GEMINI_FAILURE_COUNT
    if _GEMINI_FAILURE_COUNT >= _GEMINI_FAILURE_THRESHOLD:
        logger.warning("Gemini vision circuit breaker open")
        return None
    try:
        import requests
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")
        audit_prompt = f"""You are an image quality auditor for AI-generated images.
Analyze this image against the prompt that was used to generate it.

PROMPT USED:
{prompt_text}

Score each dimension 0-10:
- D1 (Prompt Adherence): Does the image match the prompt? Are all described elements present? Is the composition/layout correct?
- D2 (Object Accuracy): Are objects complete (no missing parts)? Is the identity correct? No broken/missing details?
- D3 (Visual Logic): Does the scene make sense functionally? Do objects interact logically? Is perspective/proportions correct?

Also rate your confidence 0.0-1.0.

Respond ONLY with this JSON:
{{"d1_score": 0, "d1_issues": "", "d2_score": 0, "d2_issues": "", "d3_score": 0, "d3_issues": "", "confidence": 0.0, "overall_notes": ""}}"""
        url = f"{_GEMINI_API_URL}?key={api_key}"
        payload = {"contents": [{"parts": [{"text": audit_prompt}, {"inline_data": {"mime_type": mime_type, "data": image_data}}]}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500, "responseMimeType": "application/json"}}
        resp = requests.post(url, json=payload, timeout=_GEMINI_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if text:
                result = json.loads(text)
                _GEMINI_FAILURE_COUNT = 0
                return result
            else:
                _GEMINI_FAILURE_COUNT += 1
                return None
        else:
            _GEMINI_FAILURE_COUNT += 1
            logger.warning(f"Gemini vision API error: {resp.status_code}")
            return None
    except json.JSONDecodeError as e:
        _GEMINI_FAILURE_COUNT += 1
        logger.warning(f"Gemini vision JSON parse error: {e}")
        return None
    except Exception as e:
        _GEMINI_FAILURE_COUNT += 1
        logger.warning(f"Gemini vision error: {e}")
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

    gemini_key = _get_gemini_key()

    if image_path and os.path.exists(image_path) and prompt_text and gemini_key:
        vision_result = _call_gemini_vision(image_path, prompt_text, gemini_key)
        if vision_result:
            llm_used = "gemini_flash_lite_vision"
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
            llm_used = "rule_only_gemini_failed"
            axis_scores["d1_prompt_adherence"] = 5.0
            axis_scores["d2_object_accuracy"] = 5.0
            axis_scores["d3_visual_logic"] = 5.0
            issues.append({"severity": "medium", "axis": "vision", "message": "Gemini vision failed - manual review needed", "fix": "Check API key/quota"})
            recommendations.append({"skill": "/video:prompt", "update": "Gemini vision failed - manual review", "priority": "medium", "axis": "vision"})
    else:
        axis_scores["d1_prompt_adherence"] = 5.0
        axis_scores["d2_object_accuracy"] = 5.0
        axis_scores["d3_visual_logic"] = 5.0
        if not gemini_key:
            issues.append({"severity": "low", "axis": "vision", "message": "GEMINI_API_KEY not set - vision skipped", "fix": "Set GEMINI_API_KEY"})
        elif not prompt_text:
            issues.append({"severity": "low", "axis": "vision", "message": "No prompt - vision skipped", "fix": "Provide prompt"})

    return axis_scores, issues, recommendations, llm_used
