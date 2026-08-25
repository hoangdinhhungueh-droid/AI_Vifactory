# app/audit/rubrics.py - Scoring rubrics for each audit type

STORY_RUBRIC = {
    "name": "Story Quality Audit",
    "axes": {
        "structure":       {"weight": 0.15, "method": "rule+llm", "description": "Narrative structure"},
        "hook":            {"weight": 0.15, "method": "rule",     "description": "First 3 seconds hook"},
        "open_loops":      {"weight": 0.10, "method": "rule+llm", "description": "Open loops and cliffhangers"},
        "anti_ai_voice":   {"weight": 0.15, "method": "rule",     "description": "Anti-AI writing check (14 rules)"},
        "sources":         {"weight": 0.10, "method": "rule",     "description": "Source attribution and factual accuracy"},
        "pacing":          {"weight": 0.10, "method": "llm",      "description": "Pacing and rhythm"},
        "editorial":       {"weight": 0.15, "method": "llm",      "description": "Editorial quality"},
        "retention":       {"weight": 0.10, "method": "llm",      "description": "Predicted retention"},
    },
    "thresholds": {"approved": 8.0, "review": 6.0, "rejected": 0.0},
}

DIRECTOR_RUBRIC = {
    "name": "Director Plan Audit",
    "axes": {
        "scene_coverage":   {"weight": 0.20, "method": "rule",     "description": "All story beats covered"},
        "fg_bg_prompts":    {"weight": 0.15, "method": "rule",     "description": "Every scene has FG + BG prompts"},
        "reuse_keys":       {"weight": 0.15, "method": "rule",     "description": "FG/BG reuse keys follow arc pattern"},
        "safe_zone":        {"weight": 0.10, "method": "rule",     "description": "Safe zone consistency"},
        "duration":         {"weight": 0.10, "method": "rule",     "description": "Scene durations reasonable (3-15s)"},
        "arc_structure":   {"weight": 0.15, "method": "rule+llm", "description": "Scene arcs match story"},
        "narration":        {"weight": 0.15, "method": "rule",     "description": "Narration segments present"},
    },
    "thresholds": {"approved": 8.0, "review": 6.0, "rejected": 0.0},
}

PROMPT_RUBRIC = {
    "name": "Prompt Quality Audit",
    "axes": {
        "style_lock":       {"weight": 0.15, "method": "rule",     "description": "Style lock keywords present"},
        "chroma_key":       {"weight": 0.10, "method": "rule",     "description": "Chroma-key friendly FG"},
        "safe_zone":        {"weight": 0.10, "method": "rule",     "description": "Safe zone specified"},
        "aspect_ratio":     {"weight": 0.10, "method": "rule",     "description": "16:9 aspect ratio specified"},
        "char_limit":       {"weight": 0.15, "method": "rule",     "description": "FG under 1700 chars, BG under 1000"},
        "fg_clarity":       {"weight": 0.15, "method": "llm",      "description": "FG subject clear"},
        "bg_reuse":         {"weight": 0.10, "method": "rule",     "description": "BG reuse keys follow arc pattern"},
        "scene_match":      {"weight": 0.15, "method": "llm",      "description": "Prompt matches scene"},
    },
    "thresholds": {"approved": 8.0, "review": 6.0, "rejected": 0.0},
}

# IMAGE AUDIT RUBRIC (3 vision dimensions) - Rule 100
# D1 (Prompt Adherence x0.4) + D2 (Object Accuracy x0.35) + D3 (Visual Logic x0.25)
# min_axis_for_approved: all D1/D2/D3 must be >=7.0 for APPROVED
IMAGE_RUBRIC = {
    "name": "Image Quality Audit (Hybrid Vision)",
    "axes": {
        "d1_prompt_adherence": {"weight": 0.40, "method": "llm", "description": "D1: Prompt Adherence"},
        "d2_object_accuracy":  {"weight": 0.35, "method": "llm", "description": "D2: Object Accuracy"},
        "d3_visual_logic":     {"weight": 0.25, "method": "llm", "description": "D3: Visual Logic"},
    },
    "thresholds": {"approved": 8.0, "review": 5.0, "rejected": 0.0},
    "min_axis_for_approved": 7.0,
}

def get_rubric(audit_type: str) -> dict:
    rubrics = {"story": STORY_RUBRIC, "director": DIRECTOR_RUBRIC, "prompt": PROMPT_RUBRIC, "image": IMAGE_RUBRIC}
    return rubrics.get(audit_type, {})

def calculate_composite_score(axis_scores: dict, rubric: dict) -> float:
    total = 0.0
    total_weight = 0.0
    for axis, score in axis_scores.items():
        weight = rubric.get("axes", {}).get(axis, {}).get("weight", 0)
        total += score * weight
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return round(total / total_weight, 2)

def get_verdict(score: float, rubric: dict, axis_scores: dict = None) -> str:
    thresholds = rubric.get("thresholds", {})
    if score >= thresholds.get("approved", 8.0):
        min_for_approved = rubric.get("min_axis_for_approved")
        if min_for_approved is not None and axis_scores:
            for ax_name, ax_score in axis_scores.items():
                if ax_score < min_for_approved:
                    return "REVIEW"
        return "APPROVED"
    elif score >= thresholds.get("review", 6.0):
        return "REVIEW"
    else:
        return "REJECTED"

def get_axes_by_method(rubric: dict, method: str) -> list:
    axes = []
    for axis_name, axis_config in rubric.get("axes", {}).items():
        if method in axis_config.get("method", ""):
            axes.append(axis_name)
    return axes
