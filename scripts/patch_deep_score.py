import os

filepath = "/root/video_factory/app/services/virality_score.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# Add a helper function for deep autocomplete scoring
new_helper = '''def _score_autocomplete(suggestions, subject):
    if not suggestions:
        return 0.0
    
    trending_matches = _trending_count(suggestions, subject)
    
    # Specificity: how many suggestions have >= 3 words? (Long-tail indicator)
    long_tail_count = sum(1 for s in suggestions if len(s.split()) >= 3)
    
    # Mix trending intent (weight 0.6) and long-tail specificity (weight 0.4)
    # Assume 4 trending matches is excellent (1.0 * 0.6 = 0.6)
    trend_score = min(trending_matches / 4.0, 1.0) * 0.6
    
    # Assume 6 long-tail suggestions is excellent (1.0 * 0.4 = 0.4)
    long_tail_score = min(long_tail_count / 6.0, 1.0) * 0.4
    
    return round(trend_score + long_tail_score, 3)

def score_subject'''

code = code.replace('def score_subject', new_helper)

# Replace the naive scoring logic
old_logic = '''    g_score = 1.0 if len(g) >= 5 else 0.5 if g else 0.0
    y_score = 1.0 if len(y) >= 5 else 0.5 if y else 0.0
    doc_score = 1.0 if len(doc_terms) >= 2 else 0.5 if doc_terms else 0.0'''

new_logic = '''    # DEEP REASONING SCORING (Replaced naive len() check)
    g_score = _score_autocomplete(g, subject)
    y_score = _score_autocomplete(y, subject)
    doc_score = min(len(doc_terms) / 3.0, 1.0)'''

code = code.replace(old_logic, new_logic)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)
print("virality_score.py patched with deep autocomplete logic.")
