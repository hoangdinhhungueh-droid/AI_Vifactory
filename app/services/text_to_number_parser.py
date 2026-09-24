# app/services/text_to_number_parser.py
"""Multi-Language Spoken & Symbolic Number Parser for Remotion Stat Cards & Kinetic Counters.

Rule 118 (Zero-Mock Data) & Rule 128 (Zero-Semantic-Bias):
Parses natural spoken numbers ("ten million", "five hundred thirty-eight thousand"),
standard alphanumeric currencies ("$10M", "500,000"), percentages ("52%"), and
multi-market currencies (KRW, JPY, VND, USD) without hardcoded fallbacks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ParsedMetric:
    raw_value: float
    display_value: float
    unit: str
    prefix: str
    suffix: str
    formatted: str
    metric_type: str  # "currency", "percentage", "scale"
    trend: str        # "up", "down", "neutral"


# English word-to-number vocabulary
_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}
_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000
}


def _words_to_number(words_str: str) -> Optional[float]:
    """Convert an English phrase like 'five hundred thirty-eight' or 'ten' into a float.
    Handles 'one-point-two' or 'one point two' as decimals.
    """
    cleaned = words_str.lower().replace("-", " ").strip()
    tokens = cleaned.split()
    if not tokens:
        return None

    # Check for "point" decimal: e.g. "one point two"
    if "point" in tokens:
        idx = tokens.index("point")
        integer_part = tokens[:idx]
        decimal_part = tokens[idx + 1:]
        int_val = _words_to_number(" ".join(integer_part)) if integer_part else 0.0
        if int_val is None:
            return None
        dec_digits = []
        for t in decimal_part:
            if t in _UNITS:
                dec_digits.append(str(_UNITS[t]))
            elif t.isdigit():
                dec_digits.append(t)
            else:
                break
        if dec_digits:
            dec_str = "0." + "".join(dec_digits)
            return int_val + float(dec_str)
        return int_val

    total = 0.0
    current = 0.0
    matched = False

    for token in tokens:
        if token in _UNITS:
            current += _UNITS[token]
            matched = True
        elif token in _TENS:
            current += _TENS[token]
            matched = True
        elif token == "hundred":
            current = (current if current > 0 else 1) * 100
            matched = True
        elif token in _SCALES:
            mult = _SCALES[token]
            current = (current if current > 0 else 1) * mult
            total += current
            current = 0.0
            matched = True
        elif token.isdigit():
            current += float(token)
            matched = True
        else:
            # Non-number word
            pass

    total += current
    return total if matched and total > 0 else None


def _kanji_to_int(k_str: str) -> Optional[int]:
    """Convert Japanese kanji numeral string to integer."""
    k_map = {'〇': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    unit_map = {'十': 10, '百': 100, '千': 1000}
    total = 0
    current = 0
    matched = False
    for char in k_str:
        if char in k_map:
            current = k_map[char]
            matched = True
        elif char in unit_map:
            unit = unit_map[char]
            total += (current if current > 0 else 1) * unit
            current = 0
            matched = True
        else:
            return None
    total += current
    return total if matched else None


def _parse_kanji_or_arabic(val_str: str) -> Optional[int]:
    """Parse integer from either Arabic digits or Japanese Kanji numerals."""
    if not val_str:
        return None
    cleaned = val_str.strip().replace(",", "")
    if cleaned.isdigit():
        return int(cleaned)
    return _kanji_to_int(cleaned)


def _hangul_to_int(h_str: str) -> Optional[int]:
    """Convert Sino-Korean numeral string to integer (e.g. '이백이십오' -> 225, '구십이' -> 92)."""
    h_map = {'영': 0, '공': 0, '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5, '육': 6, '칠': 7, '팔': 8, '구': 9}
    unit_map = {'십': 10, '백': 100, '천': 1000}
    total = 0
    current = 0
    matched = False
    for char in h_str:
        if char in h_map:
            current = h_map[char]
            matched = True
        elif char in unit_map:
            unit = unit_map[char]
            total += (current if current > 0 else 1) * unit
            current = 0
            matched = True
        else:
            return None
    total += current
    return total if matched else None


def parse_spoken_number(text: str) -> Optional[ParsedMetric]:
    """Parse numerical metrics from narration text (spoken words or alphanumeric).
    Returns ParsedMetric or None if no numerical metric found.
    """
    if not text:
        return None

    t_lower = text.lower()

    # Determine trend heuristic (multi-lingual forensic keywords)
    down_words = [
        "loss", "lost", "fell", "dropped", "collapse", "decline", "diverted", "vanished", "deficit",
        "sụt giảm", "thất thoát", "bốc hơi", "하락", "폭락", "손실",
        "부적절", "부정", "조작", "위반", "은폐", "허위", "위조",
        "不適切", "不正", "改ざん", "改竄", "捏造", "虚偽", "隠蔽", "違反", "偽装", "損失"
    ]
    trend = "down" if any(k in text for k in down_words) or any(k in t_lower for k in down_words) else "up"

    # 1. Check Korean Currencies & Scales: 350만 원, 5000억 원, 10조 원, 14,000명
    kr_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(만|억|조)?\s*(원|명|건|곳)', text)
    if kr_match:
        base = float(kr_match.group(1).replace(",", ""))
        unit = kr_match.group(2) or ""
        suffix = " " + kr_match.group(3)
        mult = 1.0
        if unit == "만":
            mult = 10_000.0
        elif unit == "억":
            mult = 100_000_000.0
        elif unit == "조":
            mult = 1_000_000_000_000.0
        raw_val = base * mult
        return ParsedMetric(
            raw_value=raw_val,
            display_value=base,
            unit=unit,
            prefix="",
            suffix=suffix,
            formatted=f"{base:g}{unit}{suffix}",
            metric_type="currency" if "원" in suffix else "scale",
            trend=trend
        )

    # 1.1 Check Korean Spoken Percentages: 구십이 퍼센트, 92퍼센트, 15프로
    kr_pct_hangul = re.search(r'([일이삼사오육칠팔구십백]+)\s*(?:퍼센트|프로|%)', text)
    if kr_pct_hangul:
        h_val = _hangul_to_int(kr_pct_hangul.group(1))
        if h_val is not None:
            return ParsedMetric(
                raw_value=float(h_val),
                display_value=float(h_val),
                unit="%",
                prefix="",
                suffix="",
                formatted=f"{h_val}%",
                metric_type="percentage",
                trend=trend
            )

    # 1.2 Check Korean Spoken Units & Scales: 이백이십오 건, 225건
    kr_hangul_unit = re.search(r'([일이삼사오육칠팔구십백천]+)\s*(건|명|원|곳|개|만|억)', text)
    if kr_hangul_unit:
        h_val = _hangul_to_int(kr_hangul_unit.group(1))
        u = kr_hangul_unit.group(2)
        if h_val is not None:
            mult = 100_000_000.0 if u == "억" else (10_000.0 if u == "만" else 1.0)
            return ParsedMetric(
                raw_value=float(h_val) * mult,
                display_value=float(h_val),
                unit=u,
                prefix="",
                suffix="",
                formatted=f"{h_val}{u}",
                metric_type="currency" if u in ("억", "만", "원") else "scale",
                trend=trend
            )

    # 2. Check Vietnamese Currencies: 500 tỷ đồng, 10 triệu đồng, 300 tỷ
    vn_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(tỷ|triệu|nghìn)\s*(đ(?:ồng)?)?', text, re.IGNORECASE)
    if vn_match:
        base = float(vn_match.group(1).replace(",", ""))
        unit = vn_match.group(2).lower()
        suffix = " ĐỒNG" if vn_match.group(3) else ""
        mult = 1.0
        if unit == "tỷ":
            mult = 1_000_000_000.0
        elif unit == "triệu":
            mult = 1_000_000.0
        elif unit == "nghìn":
            mult = 1_000.0
        raw_val = base * mult
        return ParsedMetric(
            raw_value=raw_val,
            display_value=base,
            unit=unit.upper(),
            prefix="",
            suffix=suffix,
            formatted=f"{base:g} {unit.upper()}{suffix}",
            metric_type="currency",
            trend=trend
        )

    # 2.3. Check Japanese Ratio / Comparative Audit Metrics:
    # e.g., "二百二十五件のうち、二百八件、実に九十二パーセントが不適切" or "225件中208件"
    jp_ratio = re.search(
        r'([一二三四五六七八九十百千\d]+)\s*(?:件|点|基|箇所|人)?\s*(?:のうち|中)[、\s]*([一二三四五六七八九十百千\d]+)\s*(件|点|基|箇所|人)',
        text
    )
    if jp_ratio:
        total_val = _parse_kanji_or_arabic(jp_ratio.group(1))
        target_val = _parse_kanji_or_arabic(jp_ratio.group(2))
        u = jp_ratio.group(3)
        if total_val and target_val:
            pct_m = re.search(r'([一二三四五六七八九十百千\d]+)\s*(?:パーセント|％)', text)
            pct_str = ""
            if pct_m:
                p_val = _parse_kanji_or_arabic(pct_m.group(1))
                if p_val:
                    pct_str = f" ({p_val}%)"
            elif total_val > 0:
                calc_pct = round((target_val / total_val) * 100, 1)
                pct_str = f" ({calc_pct:g}%)"

            suffix_str = f" / {total_val}{u}{pct_str}"
            return ParsedMetric(
                raw_value=float(target_val),
                display_value=float(target_val),
                unit=u,
                prefix="",
                suffix=suffix_str,
                formatted=f"{target_val}{u}{suffix_str}",
                metric_type="scale",
                trend=trend
            )

    # 2.5. Check Japanese Currencies, Units & Kanji Numbers: 二百八件, 208件, 92%, 100億円
    jp_pct_kanji = re.search(r'([一二三四五六七八九十百]+)\s*(?:パーセント|％)', text)
    if jp_pct_kanji:
        k_val = _kanji_to_int(jp_pct_kanji.group(1))
        if k_val is not None:
            return ParsedMetric(
                raw_value=float(k_val),
                display_value=float(k_val),
                unit="%",
                prefix="",
                suffix="",
                formatted=f"{k_val}%",
                metric_type="percentage",
                trend=trend
            )

    jp_kanji_unit = re.search(r'([一二三四五六七八九十百千]+)\s*(件|人|ヶ所|基|箇所|億|万)', text)
    if jp_kanji_unit:
        k_val = _kanji_to_int(jp_kanji_unit.group(1))
        u = jp_kanji_unit.group(2)
        if k_val is not None:
            mult = 100_000_000.0 if u == "億" else (10_000.0 if u == "万" else 1.0)
            return ParsedMetric(
                raw_value=float(k_val) * mult,
                display_value=float(k_val),
                unit=u,
                prefix="",
                suffix="",
                formatted=f"{k_val}{u}",
                metric_type="currency" if u in ("億", "万") else "scale",
                trend=trend
            )

    jp_digit_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(万|億|兆)?\s*(円|件|人|名|ヶ所|箇所|基|倍|トン|m|km|点|本|台|棟)?', text)
    if jp_digit_match and (jp_digit_match.group(2) or jp_digit_match.group(3)):
        base = float(jp_digit_match.group(1).replace(",", ""))
        unit = jp_digit_match.group(2) or ""
        suffix = jp_digit_match.group(3) or ""
        mult = 100_000_000.0 if unit == "億" else (10_000.0 if unit == "万" else (1_000_000_000_000.0 if unit == "兆" else 1.0))
        return ParsedMetric(
            raw_value=base * mult,
            display_value=base,
            unit=f"{unit}{suffix}",
            prefix="",
            suffix="",
            formatted=f"{base:g}{unit}{suffix}",
            metric_type="currency" if "円" in suffix else "scale",
            trend=trend
        )

    # 3. Check Percentages: 52%, -38%, +15.4%, 92パーセント
    pct_match = re.search(r'([+-]?\d+(?:\.\d+)?)\s*(?:%|パーセント|％)', text)
    if pct_match:
        val = float(pct_match.group(1))
        return ParsedMetric(
            raw_value=val,
            display_value=abs(val),
            unit="%",
            prefix="+" if val > 0 and "+" in pct_match.group(0) else ("-" if val < 0 else ""),
            suffix="",
            formatted=f"{val:g}%",
            metric_type="percentage",
            trend="down" if val < 0 or trend == "down" else "up"
        )

    # 4. Check Alphanumeric Dollar / Currency: $10M, $1.2B, $538K, 40 billion dollar, $300,000, $10 million
    alpha_dollar = re.search(r'(\$)?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|trillion|thousand|b|m|k)?\s*(dollars?|usd)?', text, re.IGNORECASE)
    if alpha_dollar and (alpha_dollar.group(1) or alpha_dollar.group(3) or alpha_dollar.group(4)):
        base = float(alpha_dollar.group(2).replace(",", ""))
        unit_str = (alpha_dollar.group(3) or "").upper()
        has_dollar = bool(alpha_dollar.group(1) or alpha_dollar.group(4) or any(k in t_lower for k in ["dollar", "stock", "capital", "fund", "loss"]))
        prefix = "$" if has_dollar else ""
        if unit_str in ["BILLION", "B"]:
            unit = "B"
            raw_val = base * 1_000_000_000.0
            display_val = base
        elif unit_str in ["MILLION", "M"]:
            unit = "M"
            raw_val = base * 1_000_000.0
            display_val = base
        elif unit_str in ["THOUSAND", "K"]:
            unit = "K"
            raw_val = base * 1_000.0
            display_val = base
        else:
            # Raw number without scale, e.g. $300,000 or $500
            raw_val = base
            if raw_val >= 1_000_000_000:
                display_val = raw_val / 1_000_000_000.0
                unit = "B"
            elif raw_val >= 1_000_000:
                display_val = raw_val / 1_000_000.0
                unit = "M"
            elif raw_val >= 1_000:
                display_val = raw_val / 1_000.0
                unit = "K"
            else:
                display_val = raw_val
                unit = ""
        return ParsedMetric(
            raw_value=raw_val,
            display_value=display_val,
            unit=unit,
            prefix=prefix,
            suffix="",
            formatted=f"{prefix}{display_val:g}{unit}",
            metric_type="currency" if prefix == "$" else "scale",
            trend=trend
        )

    # 5. Check Spoken English Numbers:
    # Patterns like: "ten million [dollars]", "five hundred thirty-eight thousand [dollars]",
    # "one-point-two million [dollars]", "three hundred thousand [dollars]"
    scale_pattern = r'\b((?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|point|-|\s)+)\s*(million|billion|thousand|trillion)\s*(?:taxpayer\s+)?(?:dollars)?'
    spoken_m = re.search(scale_pattern, text, re.IGNORECASE)
    if spoken_m:
        number_words = spoken_m.group(1).strip()
        scale_word = spoken_m.group(2).lower()
        base_num = _words_to_number(number_words)
        if base_num is not None and base_num > 0:
            mult = _SCALES.get(scale_word, 1.0)
            raw_val = base_num * mult
            unit = "M" if scale_word == "million" else ("B" if scale_word == "billion" else "K")
            is_dollar = any(k in t_lower for k in ["dollar", "taxpayer", "claim", "reimbursement", "fund", "payment", "fine", "loss", "subsidy", "subsidies"])
            prefix = "$" if is_dollar else ""
            return ParsedMetric(
                raw_value=raw_val,
                display_value=base_num,
                unit=unit,
                prefix=prefix,
                suffix="",
                formatted=f"{prefix}{base_num:g}{unit}",
                metric_type="currency" if prefix == "$" else "scale",
                trend=trend
            )

    # 6. Check standalone spoken dollar amount: "five hundred thousand dollars"
    spoken_dollar_simple = re.search(r'\b((?:[a-z\-]+(?:\s+[a-z\-]+)*))\s+dollars\b', text, re.IGNORECASE)
    if spoken_dollar_simple:
        cand = spoken_dollar_simple.group(1).strip()
        val = _words_to_number(cand)
        if val is not None and val > 0:
            if val >= 1_000_000_000:
                display_val = val / 1_000_000_000.0
                unit = "B"
            elif val >= 1_000_000:
                display_val = val / 1_000_000.0
                unit = "M"
            elif val >= 1_000:
                display_val = val / 1_000.0
                unit = "K"
            else:
                display_val = val
                unit = ""
            return ParsedMetric(
                raw_value=val,
                display_value=display_val,
                unit=unit,
                prefix="$",
                suffix="",
                formatted=f"${display_val:g}{unit}",
                metric_type="currency",
                trend=trend
            )

    return None
