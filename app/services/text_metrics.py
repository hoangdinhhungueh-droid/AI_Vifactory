"""app/services/text_metrics.py - Multi-Lingual Text & Pacing Metric Standard.

Standardizes length measurement, unit counting, and narration pacing estimation
across all target markets in the AI Video Factory pipeline (EN, JP, KR, ZH, VI):
1. Latin / Spaced Languages (EN, VI):
   - Unit = Words (whitespace / regex delimited).
   - Speed = ~140-150 words per minute (WPM).
2. Japanese (JP):
   - Unit = Characters (no whitespace separation).
   - Speed = ~350-400 characters per minute (CPM).
3. Korean (KR):
   - Unit = Hangul Syllables / Characters & Eo-jeol (word blocks).
   - Speed = ~245-280 syllables per minute, ~100-120 eo-jeols per minute.
4. Chinese (ZH):
   - Unit = Characters.
   - Speed = ~280-320 characters per minute (CPM).
"""

import re
from typing import Dict, Any, Tuple, Optional

# Unicode ranges
CJK_REGEX = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]')
JP_KANA_REGEX = re.compile(r'[\u3040-\u30ff]')
KR_HANGUL_REGEX = re.compile(r'[\uac00-\ud7af]')
ZH_KANJI_REGEX = re.compile(r'[\u4e00-\u9fff]')


def is_cjk_market(market: str) -> bool:
    """Checks if the market code corresponds to a CJK language."""
    if not market:
        return False
    m = market.strip().upper()
    return m in ("JP", "JA", "KR", "KO", "ZH", "CN", "TW")


def detect_language(text: str, market: Optional[str] = None) -> str:
    """Detects language flavor based on market code and character distribution.
    Returns: 'JP', 'KR', 'ZH', 'EN', or 'VI'.
    """
    m_up = (market or "").strip().upper()
    if m_up in ("JP", "JA"):
        return "JP"
    if m_up in ("KR", "KO"):
        return "KR"
    if m_up in ("ZH", "CN", "TW"):
        return "ZH"
    if m_up == "VI":
        return "VI"

    # Fallback to character analysis if market is ambiguous or EN
    sample = text[:1500] if text else ""
    kr_count = len(KR_HANGUL_REGEX.findall(sample))
    jp_count = len(JP_KANA_REGEX.findall(sample))
    cjk_count = len(CJK_REGEX.findall(sample))
    latin_count = len(re.findall(r'[a-zA-Z0-9_\-]+', sample))

    if cjk_count > latin_count:
        if kr_count > cjk_count * 0.4:
            return "KR"
        if jp_count > 0:
            return "JP"
        return "ZH"

    return "EN"


def get_clean_character_count(text: str) -> int:
    """Counts non-whitespace characters (standard for CJK texts)."""
    if not text:
        return 0
    return len(re.sub(r'\s+', '', text))


def get_word_count(text: str) -> int:
    """Counts whitespace-separated words / eo-jeols."""
    if not text:
        return 0
    return len(text.strip().split())


def get_script_units(text: str, market: str = "EN") -> int:
    """Returns canonical units according to the target language:
    - JP, ZH: Number of characters (ignoring whitespace).
    - KR: Number of Hangul syllables / characters.
    - EN, VI: Number of whitespace-separated words.
    """
    if not text:
        return 0
    lang = detect_language(text, market)
    if lang in ("JP", "ZH"):
        return get_clean_character_count(text)
    elif lang == "KR":
        hangul_chars = len(KR_HANGUL_REGEX.findall(text))
        return hangul_chars if hangul_chars > 0 else get_clean_character_count(text)
    else:
        return get_word_count(text)


def get_unit_name(market: str = "EN", text: Optional[str] = None) -> str:
    """Returns human-readable unit label: 'chars' for CJK, 'words' for Latin."""
    lang = detect_language(text or "", market)
    return "chars" if lang in ("JP", "KR", "ZH") else "words"


def validate_script_length(
    text: str,
    market: str = "EN",
    min_en_words: int = 1200,
    min_cjk_chars: int = 2500,
    min_kr_syllables: int = 2200,
    min_kr_words: int = 750
) -> Dict[str, Any]:
    """Validates if script meets minimum length threshold for 10-15 minute docudrama.
    Avoids false rejections caused by raw .split() on Japanese or Korean.
    """
    if not text:
        return {
            "valid": False,
            "units": 0,
            "unit_name": "words",
            "required_min": min_en_words,
            "market": market,
            "message": "Script is empty"
        }

    lang = detect_language(text, market)
    char_count = get_clean_character_count(text)
    word_count = get_word_count(text)

    if lang in ("JP", "ZH"):
        units = char_count
        required_min = min_cjk_chars
        unit_name = "chars"
        valid = units >= required_min
    elif lang == "KR":
        hangul_chars = len(KR_HANGUL_REGEX.findall(text))
        units = hangul_chars if hangul_chars > 0 else char_count
        required_min = min_kr_syllables
        unit_name = "syllables"
        valid = (units >= min_kr_syllables) or (word_count >= min_kr_words)
    else:
        units = word_count
        required_min = min_en_words
        unit_name = "words"
        valid = units >= required_min

    return {
        "valid": valid,
        "units": units,
        "unit_name": unit_name,
        "required_min": required_min,
        "char_count": char_count,
        "word_count": word_count,
        "market": market,
        "language": lang,
        "message": f"{units}/{required_min} {unit_name} (valid={valid})"
    }


def estimate_narration_seconds(text: str, market: str = "EN") -> float:
    """Estimates audio narration duration in seconds based on language pacing:
    - EN: ~145 words/min (~2.4 words/sec)
    - JP: ~360 chars/min (~6.0 chars/sec)
    - KR: ~250 syllables/min (~4.17 syllables/sec)
    - ZH: ~300 chars/min (~5.0 chars/sec)
    """
    if not text:
        return 0.0

    lang = detect_language(text, market)
    if lang == "JP":
        chars = get_clean_character_count(text)
        return round(chars / 6.0, 2)
    elif lang == "KR":
        hangul_chars = len(KR_HANGUL_REGEX.findall(text))
        if hangul_chars > 0:
            return round(hangul_chars / 4.17, 2)
        words = get_word_count(text)
        return round(words / 1.8, 2)
    elif lang == "ZH":
        chars = get_clean_character_count(text)
        return round(chars / 5.0, 2)
    else:
        words = get_word_count(text)
        return round(words / 2.4, 2)
