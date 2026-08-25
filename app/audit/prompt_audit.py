# app/audit/prompt_audit.py — Prompt quality audit (8 axes)
# Rule-based checks for style lock, chroma key, safe zone, aspect ratio, char limits
import logging
import re
import os

logger = logging.getLogger(__name__)

# Style lock keywords that should appear in prompts
# Style lock keywords - distinctive terms from our actual style lock block
# Override via env: AUDIT_STYLE_LOCK_KEYWORDS="term1|term2|term3"
DEFAULT_STYLE_LOCK_KEYWORDS = [
    "flat vector illustration",
    "bold clean black outline",
    "vector-poster",
    "editorial-infographic",
    "cel-shading",
    "muted desaturated",
    "business-editorial",
]
_env_kws = os.environ.get("AUDIT_STYLE_LOCK_KEYWORDS", "")
STYLE_LOCK_KEYWORDS = _env_kws.split("|") if _env_kws else DEFAULT_STYLE_LOCK_KEYWORDS
CHROMA_KEY_INDICATORS = ["solid background", "green screen", "chroma key", "isolated", "transparent background"]
SAFE_ZONES = ["center", "top-third", "bottom-third", "left-third", "right-third"]
ASPECT_RATIOS = ["16:9", "1920x1080", "1080x1920", "1024x1024"]


def _check_style_lock(prompts: list) -> tuple:
    """Check style lock keywords present in prompts."""
    issues = []
    score = 10.0
    missing_count = 0
    for i, p in enumerate(prompts):
        text = (p.get("fg_prompt", "") + " " + p.get("bg_prompt", "")).lower()
        has_style = any(kw in text for kw in STYLE_LOCK_KEYWORDS)
        if not has_style:
            missing_count += 1
    if missing_count > 0:
        score -= min(missing_count * 0.3, 5.0)
        issues.append({"severity": "medium", "axis": "style_lock", "message": f"{missing_count} prompts missing style lock keywords", "fix": f"Add style keywords: {', '.join(STYLE_LOCK_KEYWORDS[:2])}"})
    return max(score, 0), issues


def _check_chroma_key(prompts: list) -> tuple:
    """Check chroma-key friendly FG prompts."""
    issues = []
    score = 10.0
    missing_count = 0
    for p in prompts:
        fg = (p.get("fg_prompt") or "").lower()
        has_chroma = any(kw in fg for kw in CHROMA_KEY_INDICATORS)
        if not has_chroma and fg:
            missing_count += 1
    if missing_count > 0:
        score -= min(missing_count * 0.2, 3.0)
        issues.append({"severity": "low", "axis": "chroma_key", "message": f"{missing_count} FG prompts missing chroma-key indicators", "fix": "Add 'solid background' or 'isolated' to FG prompts"})
    return max(score, 0), issues


def _check_safe_zone(prompts: list) -> tuple:
    """Check safe zone specified and consistent."""
    issues = []
    score = 10.0
    missing_count = 0
    for p in prompts:
        sz = p.get("safe_zone", "")
        if not sz or sz.strip() == "":
            missing_count += 1
    if missing_count > 0:
        score -= min(missing_count * 0.3, 4.0)
        issues.append({"severity": "medium", "axis": "safe_zone", "message": f"{missing_count} prompts missing safe zone", "fix": f"Set safe zone: {', '.join(SAFE_ZONES[:3])}"})
    return max(score, 0), issues


def _check_aspect_ratio(prompts: list) -> tuple:
    """Check 16:9 aspect ratio specified."""
    issues = []
    score = 10.0
    missing_count = 0
    for p in prompts:
        text = (p.get("fg_prompt", "") + " " + p.get("bg_prompt", "")).lower()
        has_ratio = any(ar.lower() in text for ar in ASPECT_RATIOS)
        if not has_ratio:
            missing_count += 1
    if missing_count > 0:
        score -= min(missing_count * 0.2, 3.0)
        issues.append({"severity": "low", "axis": "aspect_ratio", "message": f"{missing_count} prompts missing aspect ratio", "fix": "Add '16:9' to prompts"})
    return max(score, 0), issues


def _check_char_limit(prompts: list) -> tuple:
    """Check FG prompt under 1700 chars, BG under 1000 chars."""
    issues = []
    score = 10.0
    fg_over = 0
    bg_over = 0
    for p in prompts:
        fg = p.get("fg_prompt", "") or ""
        bg = p.get("bg_prompt", "") or ""
        if len(fg) > 1700:
            fg_over += 1
        if len(bg) > 1000:
            bg_over += 1
    if fg_over > 0:
        score -= min(fg_over * 0.5, 5.0)
        issues.append({"severity": "high", "axis": "char_limit", "message": f"{fg_over} FG prompts exceed 1700 chars", "fix": "Shorten FG prompts to under 1700 chars"})
    if bg_over > 0:
        score -= min(bg_over * 0.3, 3.0)
        issues.append({"severity": "medium", "axis": "char_limit", "message": f"{bg_over} BG prompts exceed 1000 chars", "fix": "Shorten BG prompts to under 1000 chars"})
    return max(score, 0), issues


def _check_fg_clarity(prompts: list, llm_call) -> tuple:
    """Check FG subject clear and unambiguous (LLM-based)."""
    issues = []
    scores = []
    for p in prompts[:10]:  # Sample first 10
        fg = p.get("fg_prompt", "")
        if not fg:
            scores.append(5.0)
            continue
        result = llm_call(f"Rate this image prompt's subject clarity 0-10 (integer only):\n{fg[:500]}", "You are a prompt quality auditor.")
        if result:
            try:
                nums = re.findall(r'\d+', result.strip())
                if nums:
                    scores.append(min(max(int(nums[0]), 0), 10))
                    continue
            except:
                pass
        scores.append(7.0)  # Fallback
    avg = sum(scores) / max(len(scores), 1) if scores else 7.0
    if avg < 7:
        issues.append({"severity": "medium", "axis": "fg_clarity", "message": f"FG prompt clarity avg {avg:.1f}/10", "fix": "Make FG subject more specific and unambiguous"})
    return avg, issues


def _check_bg_reuse(prompts: list) -> tuple:
    """Check BG reuse keys follow arc pattern."""
    issues = []
    score = 10.0
    missing = 0
    for p in prompts:
        key = p.get("bg_reuse_key", "")
        if not key or key.strip() == "":
            missing += 1
    if missing > 0:
        score -= min(missing * 0.2, 3.0)
        issues.append({"severity": "medium", "axis": "bg_reuse", "message": f"{missing} prompts missing BG reuse key", "fix": "Generate BG reuse keys following arc pattern"})
    return max(score, 0), issues


def _check_scene_match(prompts: list, llm_call) -> tuple:
    """Check prompt matches scene description (LLM-based)."""
    issues = []
    scores = []
    for p in prompts[:10]:  # Sample first 10
        fg = p.get("fg_prompt", "")
        beat = p.get("beat", p.get("scene_description", ""))
        if not fg or not beat:
            scores.append(7.0)
            continue
        result = llm_call(f"Rate how well this prompt matches the scene description 0-10 (integer only):\nPrompt: {fg[:300]}\nScene: {beat[:300]}", "You are a prompt quality auditor.")
        if result:
            try:
                nums = re.findall(r'\d+', result.strip())
                if nums:
                    scores.append(min(max(int(nums[0]), 0), 10))
                    continue
            except:
                pass
        scores.append(7.0)
    avg = sum(scores) / max(len(scores), 1) if scores else 7.0
    if avg < 7:
        issues.append({"severity": "medium", "axis": "scene_match", "message": f"Prompt-scene match avg {avg:.1f}/10", "fix": "Ensure prompts match scene descriptions"})
    return avg, issues


def audit_prompt(content: dict, llm_call) -> tuple:
    """Run full prompt audit. Returns (axis_scores, issues, recommendations, llm_used)."""
    prompts = content.get("prompts", content.get("scenes", []))
    if not prompts:
        return ({}, [{"severity": "critical", "axis": "system", "message": "No prompts provided", "fix": "Provide prompts array in content"}], [], "rule_only")
    
    axis_scores = {}
    all_issues = []
    recommendations = []
    llm_used = "rule_only"
    
    # Rule-based checks (0 LLM cost)
    rule_checks = [
        ("style_lock", lambda: _check_style_lock(prompts)),
        ("chroma_key", lambda: _check_chroma_key(prompts)),
        ("safe_zone", lambda: _check_safe_zone(prompts)),
        ("aspect_ratio", lambda: _check_aspect_ratio(prompts)),
        ("char_limit", lambda: _check_char_limit(prompts)),
        ("bg_reuse", lambda: _check_bg_reuse(prompts)),
    ]
    for axis_name, check_fn in rule_checks:
        score, issues = check_fn()
        axis_scores[axis_name] = score
        all_issues.extend(issues)
    
    # LLM-based checks (Groq free tier)
    for axis_name, check_fn in [("fg_clarity", lambda: _check_fg_clarity(prompts, llm_call)),
                                 ("scene_match", lambda: _check_scene_match(prompts, llm_call))]:
        score, issues = check_fn()
        axis_scores[axis_name] = score
        all_issues.extend(issues)
        if not any("LLM unavailable" in i.get("message", "") for i in issues):
            llm_used = "groq"
    
    for issue in all_issues:
        if issue.get("severity") in ("high", "critical"):
            recommendations.append({
                "skill": "/video:prompt",
                "update": issue.get("fix", ""),
                "priority": issue.get("severity", "medium"),
                "axis": issue.get("axis", ""),
            })
    
    return axis_scores, all_issues, recommendations, llm_used
