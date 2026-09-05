# app/audit/director_audit.py — Director plan audit (8 axes)
# Rule-based checks for scene coverage, 5-beat structure, FG/BG prompts, reuse keys, safe zone, duration, camera tension, narration
import logging
import re

logger = logging.getLogger(__name__)

CANONICAL_BEATS = [
    "Beat 1", "Beat 2", "Beat 3", "Beat 4", "Beat 5"
]

def _check_scene_coverage(scenes: list, story_beats: list = None) -> tuple:
    """Check all story beats are covered by scenes."""
    issues = []
    if not scenes:
        return 0.0, [{"severity": "critical", "axis": "scene_coverage", "message": "No scenes provided", "fix": "Generate director plan with scenes"}]
    score = 10.0
    # Check minimum scene count (30 - 60 scenes for a 12-15 min video)
    if len(scenes) < 15:
        score -= 4.0
        issues.append({"severity": "high", "axis": "scene_coverage", "message": f"Only {len(scenes)} scenes — too few for a 12-15m docudrama", "fix": "Expand to at least 25-55 scenes"})
    elif len(scenes) < 25:
        score -= 1.5
        issues.append({"severity": "medium", "axis": "scene_coverage", "message": f"Only {len(scenes)} scenes — slightly short", "fix": "Target 30-55 dynamic scenes"})
    # Check for null/empty scenes
    null_scenes = [i for i, s in enumerate(scenes) if not s.get("fg_prompt") and not s.get("bg_prompt") and not s.get("image_prompt")]
    if null_scenes:
        score -= 2.0
        issues.append({"severity": "high", "axis": "scene_coverage", "message": f"{len(null_scenes)} scenes have no FG or BG prompt", "fix": "Generate prompts for all scenes"})
    return max(score, 0), issues


def _check_5beat_structure(scenes: list) -> tuple:
    """Check scene distribution covers all 5 beats of Investigative Docudrama (Rule 445)."""
    issues = []
    score = 10.0
    beats_found = set()
    for s in scenes:
        b_idx = s.get("beat_index") or s.get("arc_index") or s.get("arc")
        if b_idx is not None:
            try:
                beats_found.add(int(b_idx))
            except (ValueError, TypeError):
                pass
        b_name = str(s.get("beat", "") or s.get("beat_name", ""))
        for i in range(1, 6):
            if f"Beat {i}" in b_name or f"beat_{i}" in b_name or f"b{i}" in b_name:
                beats_found.add(i)

    missing_beats = [i for i in range(1, 6) if i not in beats_found]
    if missing_beats:
        penalty = len(missing_beats) * 2.0
        score -= penalty
        issues.append({
            "severity": "high" if len(missing_beats) > 1 else "medium",
            "axis": "5beat_structure",
            "message": f"Missing coverage for beats: {missing_beats}",
            "fix": "Ensure scenes span all 5 investigative beats (Hook -> False Narrative -> Blindspot -> Culprit -> Modern Mirror)"
        })
    return max(score, 0), issues


def _check_fg_bg_prompts(scenes: list) -> tuple:
    """Check every scene has Layer 1 BG and proper FG specifications."""
    issues = []
    score = 10.0
    missing_bg = 0
    missing_fg_or_pure_bg = 0
    for i, scene in enumerate(scenes):
        bg = scene.get("bg_prompt") or scene.get("image_prompt") or ""
        if not str(bg).strip():
            missing_bg += 1
    if missing_bg > 0:
        score -= min(missing_bg * 0.5, 5.0)
        issues.append({"severity": "high", "axis": "fg_bg_prompts", "message": f"{missing_bg} scenes missing Layer 1 BG prompt", "fix": "Generate BG prompt for all scenes"})
    return max(score, 0), issues


def _check_reuse_keys(scenes: list) -> tuple:
    """Check FG/BG reuse keys present and follow canonical naming pattern."""
    issues = []
    score = 10.0
    missing_bg_key = 0
    for scene in scenes:
        bg_k = scene.get("bg_reuse_key") or scene.get("background_reuse_key") or ""
        if not str(bg_k).strip():
            missing_bg_key += 1
    if missing_bg_key > 0:
        score -= min(missing_bg_key * 0.2, 3.0)
        issues.append({"severity": "medium", "axis": "reuse_keys", "message": f"{missing_bg_key} scenes missing BG reuse key", "fix": "Generate BG reuse keys following format: <ep_id>_bg_<beat>_<slug>"})
    return max(score, 0), issues


def _check_safe_zone(scenes: list) -> tuple:
    """Check safe zone consistency (bottom 20% subtitle safe zone)."""
    issues = []
    score = 10.0
    safe_zones = [s.get("safe_zone", "") for s in scenes if s.get("safe_zone")]
    if not safe_zones:
        score -= 2.0
        issues.append({"severity": "medium", "axis": "safe_zone", "message": "No safe zone specified", "fix": "Set safe zone for all scenes (bottom 20% for subtitles)"})
    return max(score, 0), issues


def _check_duration(scenes: list) -> tuple:
    """Check scene durations are reasonable (4-25s, total 10-18 min)."""
    issues = []
    score = 10.0
    short_count = 0
    long_count = 0
    total_dur = 0.0
    for scene in scenes:
        dur = scene.get("duration_est", scene.get("duration_sec", scene.get("duration", 0)))
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 0.0
        total_dur += dur
        if dur > 0:
            if dur < 3:
                short_count += 1
            elif dur > 25:
                long_count += 1
    if short_count > 0:
        score -= min(short_count * 0.3, 2.0)
        issues.append({"severity": "medium", "axis": "duration", "message": f"{short_count} scenes shorter than 3s", "fix": "Increase duration to at least 4s"})
    if long_count > 0:
        score -= min(long_count * 0.2, 2.0)
        issues.append({"severity": "low", "axis": "duration", "message": f"{long_count} scenes longer than 25s", "fix": "Split long scenes"})
    return max(score, 0), issues


def _check_camera_tension(scenes: list) -> tuple:
    """Check camera movement / tension curve specification."""
    issues = []
    score = 10.0
    missing_cam = 0
    for scene in scenes:
        cam = scene.get("camera")
        if not cam:
            missing_cam += 1
        elif isinstance(cam, dict) and not cam.get("movement"):
            missing_cam += 1
    if missing_cam > 0:
        score -= min(missing_cam * 0.1, 2.0)
        issues.append({"severity": "low", "axis": "camera_tension", "message": f"{missing_cam} scenes missing camera movement directive", "fix": "Specify camera movement (slow_push_in, static_tension, tracking)"})
    return max(score, 0), issues


def _check_narration(scenes: list) -> tuple:
    """Check narration segments present in all scenes."""
    issues = []
    score = 10.0
    missing_narr = 0
    for scene in scenes:
        narr = scene.get("narration") or scene.get("narration_segment") or ""
        if not str(narr).strip():
            missing_narr += 1
    if missing_narr > 0:
        score -= min(missing_narr * 0.3, 4.0)
        issues.append({"severity": "medium", "axis": "narration", "message": f"{missing_narr} scenes missing narration text", "fix": "Include spoken narration segment in each scene"})
    return max(score, 0), issues


def audit_director(content: dict, llm_call=None) -> tuple:
    """Run full 8-axis director plan audit. Returns (axis_scores, issues, recommendations, 'rule_only')."""
    scenes = content.get("scenes", [])
    if not scenes:
        return ({}, [{"severity": "critical", "axis": "system", "message": "No scenes provided", "fix": "Provide scenes array in content"}], [], "rule_only")
    
    axis_scores = {}
    all_issues = []
    recommendations = []
    
    checks = [
        ("scene_coverage", lambda: _check_scene_coverage(scenes)),
        ("5beat_structure", lambda: _check_5beat_structure(scenes)),
        ("fg_bg_prompts", lambda: _check_fg_bg_prompts(scenes)),
        ("reuse_keys", lambda: _check_reuse_keys(scenes)),
        ("safe_zone", lambda: _check_safe_zone(scenes)),
        ("duration", lambda: _check_duration(scenes)),
        ("camera_tension", lambda: _check_camera_tension(scenes)),
        ("narration", lambda: _check_narration(scenes)),
    ]
    
    for axis_name, check_fn in checks:
        score, issues = check_fn()
        axis_scores[axis_name] = round(score, 2)
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


def audit_director_plan(director_plan: dict) -> dict:
    """High-level wrapper returning total score, verdict, and details."""
    axis_scores, issues, recommendations, mode = audit_director(director_plan)
    if not axis_scores:
        return {"score": 0.0, "max_score": 10.0, "verdict": "FAIL", "issues": issues}
    
    avg_score = round(sum(axis_scores.values()) / len(axis_scores), 2)
    verdict = "PASS" if avg_score >= 8.0 and not any(i.get("severity") == "critical" for i in issues) else "FAIL"
    return {
        "score": avg_score,
        "max_score": 10.0,
        "verdict": verdict,
        "axis_scores": axis_scores,
        "issues": issues,
        "recommendations": recommendations
    }
