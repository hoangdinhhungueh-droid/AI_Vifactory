# /root/video_factory/app/utils/llm_guard.py
import re
import logging

logger = logging.getLogger(__name__)

GARBAGE_PATTERNS = [
    r'[\u4e00-\u9fff].*[\uac00-\ud7af].*[\u0600-\u06ff]',  # 3+ scripts mixed
    r'(?:[A-Za-z]{2,}\s){20,}',  # 20+ random words no structure
]

def is_garbage_output(text: str) -> bool:
    """Detect corrupted/garbage LLM output."""
    if not text or len(text.strip()) < 3:
        return True
    
    # Detect quá nhiều script ngôn ngữ khác nhau lẫn lộn
    scripts = {
        'cjk': bool(re.search(r'[\u4e00-\u9fff]', text)),
        'korean': bool(re.search(r'[\uac00-\ud7af]', text)),
        'arabic': bool(re.search(r'[\u0600-\u06ff]', text)),
        'cyrillic': bool(re.search(r'[\u0400-\u04ff]', text)),
        'latin': bool(re.search(r'[a-zA-Z]', text)),
    }
    active_scripts = sum(scripts.values())
    
    if active_scripts >= 4:
        logger.warning(f"[LLM_GUARD] Garbage detected: {active_scripts} scripts mixed")
        return True
    
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, text):
            return True
    
    return False

def validate_json_output(text: str) -> bool:
    """Kiểm tra output có phải JSON hợp lệ không."""
    import json
    try:
        json.loads(text)
        return True
    except:
        return False
