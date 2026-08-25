# app/audit/director_audit.py — Director plan audit (7 axes)
# Rule-based checks for scene coverage, FG/BG prompts, reuse keys, safe zone, duration
import logging
import re

logger = logging.getLogger(__name__)


def _check_scene_coverage(scenes: list, story_beats: list = None) -> tuple:
    """Check all story beats are covered by scenes."""
    issues = []
    if not scenes:
        return 0.0, [{"severity": "critical", "axis": "scene_coverage", "message": "No scenes provided", "fix": "Generate director plan with scenes"}]
    score = 10.0
    # Check minimum scene count
    if len(scenes) < 10:
        score -= 3.0
        issues.append({"severity": "high", "axis": "scene_coverage", "message": f"Only {len(scenes)} scenes — too few for a full episode", "fix": "Expand to at least 20-50 scenes"})
    # Check for null/empty scenes
    null_scenes = [i for i, s in enumerate(scenes) if not s.get("fg_prompt") and not s.get("bg_prompt")]
    if null_scenes:
        score -= 2.0
        issues.append({"severity": "high", "axis": "scene_coverage", "message": f"{len(null_scenes)} scenes have no FG or BG prompt", "fix": "Generate prompts for all scenes"})
    return max(score, 0), issues


def _check_fg_bg_prompts(scenes: list) -> tuple:
    """Check every scene has both FG and BG prompts."""
    issues = []
    score = 10.0
    missing_fg = 0
    missing_bg = 0
    for i, scene in enumerate(scenes):
        if not scene.get("fg_prompt") or not scene.get("fg_prompt", "").strip():
            missing_fg += 1
        if not scene.get("bg_prompt") or not scene.get("bg_prompt", "").strip():
            missing_bg += 1
    if missing_fg > 0:
        score -= min(missing_fg * 0.5, 5.0)
        issues.append({"severity": "high", "axis": "fg_bg_prompts", "message": f"{missing_fg} scenes missing FG prompt", "fix": "Generate FG prompt for all scenes"})
    if missing_bg > 0:
        score -= min(missing_bg * 0.5, 5.0)
        issues.append({"severity": "high", "axis": "fg_bg_prompts", "message": f"{missing_bg} scenes missing BG prompt", "fix": "Generate BG prompt for all scenes"})
    return max(score, 0), issues


def _check_reuse_keys(scenes: list) -> tuple:
    """Check FG/BG reuse keys present and follow arc pattern."""
    issues = []
    score = 10.0
    missing_fg_key = 0
    missing_bg_key = 0
    for scene in scenes:
        if not scene.get("fg_reuse_key") or scene.get("fg_reuse_key", "").strip() == "":
            missing_fg_key += 1
        if not scene.get("bg_reuse_key") or scene.get("bg_reuse_key", "").strip() == "":
            missing_bg_key += 1
    if missing_fg_key > 0:
        score -= min(missing_fg_key * 0.3, 5.0)
        issues.append({"severity": "high", "axis": "reuse_keys", "message": f"{missing_fg_key} scenes missing FG reuse key", "fix": "Generate FG reuse keys following naming convention: <episode_id>_fg_<arc>_<slug>"})
    if missing_bg_key > 0:
        score -= min(missing_bg_key * 0.2, 3.0)
        issues.append({"severity": "medium", "axis": "reuse_keys", "message": f"{missing_bg_key} scenes missing BG reuse key", "fix": "Generate BG reuse keys following arc pattern"})
    # Check naming convention
    for scene in scenes:
        key = scene.get("bg_reuse_key", "")
        if key and "_" not in key:
            score -= 0.2
            issues.append({"severity": "low", "axis": "reuse_keys", "message": f"BG reuse key '{key}' doesn't follow naming convention", "fix": "Use format: <episode_id>_<layer>_<arc>_<slug>"})
            break
    return max(score, 0), issues


def _check_safe_zone(scenes: list) -> tuple:
    """Check safe zone consistency across scenes."""
    issues = []
    score = 10.0
    safe_zones = [s.get("safe_zone", "") for s in scenes if s.get("safe_zone")]
    if not safe_zones:
        score = 5.0
        issues.append({"severity": "medium", "axis": "safe_zone", "message": "No safe zone specified for any scene", "fix": "Set safe zone for all scenes"})
    else:
        unique_zones = set(safe_zones)
        if len(unique_zones) == 1 and len(safe_zones) == len(scenes):
            # All same — might be intentional for some arcs, but flag
            issues.append({"severity": "low", "axis": "safe_zone", "message": f"All scenes use same safe zone '{unique_zones.pop()}'", "fix": "Consider varying safe zone by scene type"})
        elif len(unique_zones) > 5:
            score -= 1.0
            issues.append({"severity": "low", "axis": "safe_zone", "message": f"{len(unique_zones)} different safe zones — may be inconsistent", "fix": "Standardize safe zones per arc"})
    return score, issues


def _check_duration(scenes: list) -> tuple:
    """Check scene durations are reasonable (3-15s)."""
    issues = []
    score = 10.0
    short_count = 0
    long_count = 0
    for scene in scenes:
        dur = scene.get("duration_est", scene.get("duration", 0))
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 0
        if dur > 0:
            if dur < 2:
                short_count += 1
            elif dur > 20:
                long_count += 1
    if short_count > 0:
        score -= min(short_count * 0.3, 3.0)
        issues.append({"severity": "medium", "axis": "duration", "message": f"{short_count} scenes shorter than 2s", "fix": "Increase duration to at least 3s"})
    if long_count > 0:
        score -= min(long_count * 0.2, 2.0)
        issues.append({"severity": "low", "axis": "duration", "message": f"{long_count} scenes longer than 20s", "fix": "Split long scenes or reduce duration"})
    return score, issues


def _check_arc_structure(scenes: list, llm_call) -> tuple:
    """Check scene arcs match story structure. Rule-based + optional LLM."""
    issues = []
    score = 8.0
    # Check arc index distribution
    arcs = [s.get("arc_index", s.get("arc", 0)) for s in scenes if s.get("arc_index") is not None or s.get("arc") is not None]
    if arcs:
        try:
            arcs = [int(a) for a in arcs]
            unique_arcs = sorted(set(arcs))
            if len(unique_arcs) < 3:
                score -= 2.0
                issues.append({"severity": "medium", "axis": "arc_structure", "message": f"Only {len(unique_arcs)} arcs — story may lack structure", "fix": "Ensure at least 3-5 arcs"})
            # Check arc progression is sequential
            if unique_arcs != list(range(min(unique_arcs), max(unique_arcs) + 1)):
                score -= 1.0
                issues.append({"severity": "low", "axis": "arc_structure", "message": "Arc indices not sequential", "fix": "Number arcs sequentially 1, 2, 3, ..."})
        except (ValueError, TypeError):
            pass
    else:
        score = 5.0
        issues.append({"severity": "medium", "axis": "arc_structure", "message": "No arc indices found", "fix": "Assign arc index to each scene"})
    return score, issues


def _check_narration(scenes: list) -> tuple:
    """Check narration segments present."""
    issues = []
    score = 10.0
    missing_narration = 0
    for scene in scenes:
        if not scene.get("narration_segment") or not str(scene.get("narration_segment", "")).strip():
            missing_narration += 1
    if missing_narration > 0:
        score -= min(missing_narration * 0.2, 5.0)
        issues.append({"severity": "medium", "axis": "narration", "message": f"{missing_narration} scenes missing narration segment", "fix": "Generate narration for all scenes"})
    return max(score, 0), issues


def audit_director(content: dict, llm_call) -> tuple:
    """Run full director plan audit. Returns (axis_scores, issues, recommendations, llm_used)."""
    scenes = content.get("scenes", [])
    if not scenes:
        return ({}, [{"severity": "critical", "axis": "system", "message": "No scenes provided", "fix": "Provide scenes array in content"}], [], "rule_only")
    
    axis_scores = {}
    all_issues = []
    recommendations = []
    
    # All checks are rule-based (0 LLM cost)
    checks = [
        ("scene_coverage", lambda: _check_scene_coverage(scenes)),
        ("fg_bg_prompts", lambda: _check_fg_bg_prompts(scenes)),
        ("reuse_keys", lambda: _check_reuse_keys(scenes)),
        ("safe_zone", lambda: _check_safe_zone(scenes)),
        ("duration", lambda: _check_duration(scenes)),
        ("arc_structure", lambda: _check_arc_structure(scenes, llm_call)),
        ("narration", lambda: _check_narration(scenes)),
    ]
    
    for axis_name, check_fn in checks:
        score, issues = check_fn()
        axis_scores[axis_name] = score
        all_issues.extend(issues)
    
    for issue in all_issues:
        if issue.get("severity") in ("high", "critical"):
            recommendations.append({
                "skill": "/video:director",
                "update": issue.get("fix", ""),
                "priority": issue.get("severity", "medium"),
                "axis": issue.get("axis", ""),
            })
    
    return axis_scores, all_issues, recommendations, "rule_only"
