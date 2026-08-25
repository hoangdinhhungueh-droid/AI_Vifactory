# app/audit/story_audit.py — Story quality audit (8 axes)
# Rule-based checks first (0 cost), LLM only for subjective axes
import re
import logging

logger = logging.getLogger(__name__)

# ============================================================
# ANTI-AI WRITING RULES (14 rules from /video:anti-ai-writing skill)
# ============================================================
ANTI_AI_PATTERNS = [
    (r'\b(in conclusion|to conclude|in summary|to summarize)\b', 'Cliché transition phrase'),
    (r'\b(it is important to note that|it should be noted that)\b', 'Filler phrase'),
    (r'\b(delve into|navigate the complexities|tapestry of)\b', 'Overused metaphor'),
    (r'\b(underscore|underscored by)\b', 'AI-favorite verb'),
    (r'\b(a testament to\b)', 'AI-favorite phrase'),
    (r'\b(in the realm of|in the world of)\b', 'Vague opener'),
    (r'\b(landscape|paradigm|synergy|leverage)\b', 'Corporate jargon'),
    (r'\b(moreover|furthermore|additionally)\b', 'Stiff transition'),
    (r'\b(myriad|plethora|multitude of)\b', 'Overworn quantity word'),
    (r'\b(nuanced|nuance\b)', 'AI-favorite adjective'),
    (r'\b(unprecedented\b)', 'Overworn superlative'),
    (r'\b(embark|embarking)\b', 'AI-favorite verb'),
    (r'\b(foster|fostering)\b', 'AI-favorite verb'),
    (r'\b(seamless|seamlessly)\b', 'AI-favorite adjective'),
]


def _check_anti_ai(text: str) -> tuple:
    """Check 14 anti-AI writing rules. Returns (score, issues)."""
    violations = []
    text_lower = text.lower()
    for pattern, description in ANTI_AI_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            violations.append({
                "severity": "medium",
                "axis": "anti_ai_voice",
                "message": f"AI pattern detected: '{matches[0]}' — {description}",
                "fix": f"Replace '{matches[0]}' with more natural phrasing",
            })
    # Score: start at 10, deduct 0.5 per violation (max 3 points total)
    score = max(5.0, 10.0 - min(len(violations) * 0.5, 3.0))
    if len(violations) == 0:
        score = 10.0
    return score, violations


def _check_hook(text: str) -> tuple:
    """Check first 3 seconds hook quality. Returns (score, issues)."""
    issues = []
    first_500 = text[:500] if len(text) > 500 else text
    # Check for question hook
    has_question = '?' in first_500
    # Check for bold statement
    has_statement = any(w in first_500.lower() for w in ['never', 'always', 'nobody', 'everyone', 'imagine'])
    # Check for specific detail (numbers, names)
    has_specific = bool(re.search(r'\d{4}|\$\d+|\d+%', first_500))
    # Check length (not too long before first paragraph break)
    first_para = first_500.split('\n')[0] if '\n' in first_500 else first_500
    
    score = 5.0
    if has_question: score += 2.0
    if has_statement: score += 1.5
    if has_specific: score += 1.5
    if len(first_para) < 200: score += 1.0  # Concise hook
    
    if score < 7.0:
        issues.append({
            "severity": "high",
            "axis": "hook",
            "message": f"Weak hook: no question, bold statement, or specific detail in first 500 chars",
            "fix": "Start with a question, bold claim, or specific number/name to grab attention",
        })
    return min(score, 10.0), issues


def _check_structure(text: str) -> tuple:
    """Check narrative structure. Returns (score, issues)."""
    issues = []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    score = 7.0  # Base score
    
    if len(paragraphs) < 3:
        score -= 2.0
        issues.append({"severity": "high", "axis": "structure", "message": "Too few paragraphs — structure may be flat", "fix": "Ensure story has clear setup, rising action, climax, resolution"})
    if len(paragraphs) > 30:
        score -= 1.0
        issues.append({"severity": "medium", "axis": "structure", "message": "Too many paragraphs — may be fragmented", "fix": "Consolidate into fewer, more impactful paragraphs"})
    
    # Check for resolution/closure in last paragraph(s)
    last_paras = ' '.join(paragraphs[-2:]).lower() if len(paragraphs) >= 2 else (paragraphs[-1].lower() if paragraphs else "")
    has_closure = any(w in last_paras for w in ['but', 'however', 'ultimately', 'in the end', 'years later', 'what happened', 'legacy', 'lesson', 'left behind', 'reminder', 'warning', 'moral', 'the truth', 'the real', 'never forget', 'the answer', 'the question'])
    if has_closure:
        score += 1.5
    else:
        issues.append({"severity": "medium", "axis": "structure", "message": "No clear closure in final paragraph", "fix": "End with resolution or reflection"})
    
    return min(score, 10.0), issues


def _check_open_loops(text: str) -> tuple:
    """Check for open loops and cliffhangers. Returns (score, issues)."""
    issues = []
    score = 6.0
    # Check for questions throughout
    questions = text.count('?')
    if questions >= 3:
        score += 2.0
    elif questions >= 1:
        score += 1.0
    else:
        issues.append({"severity": "medium", "axis": "open_loops", "message": "No questions found — missing open loops", "fix": "Add rhetorical questions to create curiosity gaps"})
    
    # Check for cliffhanger words
    cliffhanger_words = ['but then', 'what happened next', 'what nobody knew', 'what they didn\'t know', 'little did they know']
    has_cliffhanger = any(w in text.lower() for w in cliffhanger_words)
    if has_cliffhanger:
        score += 2.0
    
    return min(score, 10.0), issues


def _check_sources(text: str) -> tuple:
    """Check source attribution. Returns (score, issues)."""
    issues = []
    score = 10.0  # Default to full score — sources are optional in creative writing
    # Check for source references
    source_patterns = [r'source:', r'according to', r'reported by', r'documented in', r'records show']
    has_text_sources = any(re.search(p, text.lower()) for p in source_patterns)
    # Markdown link sources: [text](https://...) - detects inline source citations
    has_markdown_links = bool(re.search(r'\[.+?\]\(https?://.+?\)', text))
    # Bare URL sources: https://... - detects raw URL citations
    has_urls = bool(re.search(r'https?://\S+', text))
    # Government/educational/institutional domains in URLs
    has_gov_domains = bool(re.search(r'https?://[^\s]*\.(gov|edu|mil|org)(/|\b)', text.lower()))
    has_sources = has_text_sources or has_markdown_links or has_urls or has_gov_domains
    if not has_sources and len(text) > 2000:
        # For longer factual content, sources are expected
        score = 7.0
        issues.append({"severity": "low", "axis": "sources", "message": "No source attribution found for factual content", "fix": "Add source references for factual claims"})
    return score, issues


def _llm_score_axis(llm_call, prompt_text: str, axis_name: str, description: str) -> tuple:
    """Use LLM to score a subjective axis. Returns (score, issues)."""
    issues = []
    system = f"You are a story quality auditor. Score the {axis_name} axis from 0-10. Return ONLY a number."
    full_prompt = f"Rate this story's {description} (0-10, integer only):\n\n{prompt_text[:2000]}"
    result = llm_call(full_prompt, system)
    if result:
        try:
            # Extract number from response
            import re
            nums = re.findall(r'\d+', result.strip())
            if nums:
                score = min(max(int(nums[0]), 0), 10)
                if score < 6:
                    issues.append({"severity": "high", "axis": axis_name, "message": f"LLM scored {axis_name} as {score}/10", "fix": f"Review and improve {description}"})
                return float(score), issues
        except:
            pass
    # Fallback: neutral score
    return 7.0, [{"severity": "low", "axis": axis_name, "message": f"LLM unavailable for {axis_name} — using default score", "fix": ""}]


def audit_story(content: dict, llm_call) -> tuple:
    """
    Run full story audit. Returns (axis_scores, issues, recommendations, llm_used).
    """
    story_text = content.get("story_text", content.get("text", ""))
    if not story_text:
        return ({}, [{"severity": "critical", "axis": "system", "message": "No story text provided", "fix": "Provide story_text in content"}], [], "rule_only")
    
    axis_scores = {}
    all_issues = []
    recommendations = []
    llm_used = "rule_only"
    
    # === RULE-BASED CHECKS (0 LLM cost) ===
    # Anti-AI writing (14 rules)
    score, issues = _check_anti_ai(story_text)
    axis_scores["anti_ai_voice"] = score
    all_issues.extend(issues)
    
    # Hook (first 3 seconds)
    score, issues = _check_hook(story_text)
    axis_scores["hook"] = score
    all_issues.extend(issues)
    
    # Structure
    score, issues = _check_structure(story_text)
    axis_scores["structure"] = score
    all_issues.extend(issues)
    
    # Open loops
    score, issues = _check_open_loops(story_text)
    axis_scores["open_loops"] = score
    all_issues.extend(issues)
    
    # Sources
    score, issues = _check_sources(story_text)
    axis_scores["sources"] = score
    all_issues.extend(issues)
    
    # === LLM-BASED CHECKS (Groq free tier) ===
    llm_axes = [("pacing", "pacing and rhythm of information delivery"),
                ("editorial", "editorial quality: word choice, sentence variety, tone"),
                ("retention", "predicted viewer retention: will viewers keep watching?")]
    
    for axis_name, description in llm_axes:
        score, issues = _llm_score_axis(llm_call, story_text, axis_name, description)
        axis_scores[axis_name] = score
        all_issues.extend(issues)
        if issues and issues[0].get("message", "").startswith("LLM unavailable"):
            pass  # LLM was unavailable, using default
        else:
            llm_used = "groq"
    
    # Generate recommendations from issues
    for issue in all_issues:
        if issue.get("severity") in ("high", "critical"):
            recommendations.append({
                "skill": "/video:story",
                "update": issue.get("fix", ""),
                "priority": issue.get("severity", "medium"),
                "axis": issue.get("axis", ""),
            })
    
    return axis_scores, all_issues, recommendations, llm_used
