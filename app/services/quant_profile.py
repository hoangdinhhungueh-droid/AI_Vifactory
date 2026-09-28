"""
app/services/quant_profile.py — DYNAMIC QUANTITATIVE PROFILE EXTRACTOR
Rule 128 (Anti-Semantic Bias) & Rule 132 (Pure Transmission Pipe).

Architecture:
  - Multilingual numeric & ratio parsing for EN, JP, KR, VN.
  - Slices Grounding Intel (grounding_table, claims, key_figures) into clean QuantitativeProfile.
  - ZERO episode-specific literals or mock fallbacks.
  - Returns status INSUFFICIENT_DATA if no data is found, allowing callers to handle cleanly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Iterable, Optional


class ValueKind(str, Enum):
    MEASUREMENT = "measurement"   # mg/kg, ppm, mSv, etc.
    MULTIPLIER = "multiplier"     # "24倍", "15 times", "162x"
    PERCENT = "percent"           # "75%", "20 percent"
    CURRENCY = "currency"         # "$5 billion", "50억원", "3億円"


class ProfileStatus(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"                 # Has ratio or values, but some metadata unknown
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class ParsedNumber:
    value: float
    kind: ValueKind
    unit: Optional[str]
    raw: str
    span: tuple[int, int]


@dataclass
class QuantitativeProfile:
    status: ProfileStatus
    market: str
    parameter: Optional[str] = None
    unit: Optional[str] = None
    value_kind: Optional[ValueKind] = None
    detected_value: Optional[float] = None
    baseline_value: Optional[float] = None
    standard_name: Optional[str] = None
    secondary_baseline_value: Optional[float] = None
    secondary_standard_name: Optional[str] = None
    ratio: Optional[float] = None
    secondary_ratio: Optional[float] = None
    source_citation: Optional[str] = None
    provenance: str = "none"            # grounding_table | claims | narration
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["value_kind"] = self.value_kind.value if self.value_kind else None
        return d


# ---------------------------------------------------------------------------
# Multilingual number & scale lexicon (Language semantics only, NOT episode data)
# ---------------------------------------------------------------------------
_SCALE_WORDS: dict[str, float] = {
    # EN
    "thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "billion": 1e9, "bn": 1e9, "trillion": 1e12,
    # JP / CJK
    "千": 1e3, "万": 1e4, "億": 1e8, "兆": 1e12,
    # KR
    "천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12,
    # VN
    "nghìn": 1e3, "ngàn": 1e3, "triệu": 1e6, "tỷ": 1e9, "tỉ": 1e9,
}

_CURRENCY_TOKENS: dict[str, str] = {
    "$": "USD", "usd": "USD", "dollars": "USD", "dollar": "USD",
    "円": "JPY", "¥": "JPY", "yen": "JPY",
    "원": "KRW", "₩": "KRW", "won": "KRW",
    "đồng": "VND", "vnd": "VND", "₫": "VND", "đ": "VND",
    "€": "EUR", "eur": "EUR",
}

_NUM = r"(?P<num>\d{1,3}(?:[,\.\s]\d{3})+(?:[\.,]\d+)?|\d+(?:[\.,]\d+)?)"
_SCALE = r"(?P<scale>" + "|".join(sorted(map(re.escape, _SCALE_WORDS), key=len, reverse=True)) + r")?"

_PATTERNS: list[tuple[ValueKind, re.Pattern[str]]] = [
    # Multiplier: "24倍", "24배", "gấp 24 lần", "15 times", "15x", "24.3×", "162.0x"
    (ValueKind.MULTIPLIER, re.compile(
        rf"(?:gấp\s*)?{_NUM}\s*(?:倍|배|lần|times|fold|[x×])(?![a-zA-Z])", re.IGNORECASE)),
    # Percent: "75%", "75 percent", "75 phần trăm", "75퍼센트", "75パーセント"
    (ValueKind.PERCENT, re.compile(
        rf"{_NUM}\s*(?:%|％|percent|per cent|phần trăm|퍼센트|パーセント)", re.IGNORECASE)),
    # Currency suffix: "50억원", "500 tỷ đồng", "3億円", "2.5 billion dollars"
    (ValueKind.CURRENCY, re.compile(
        rf"{_NUM}\s*{_SCALE}\s*(?P<cur>원|円|đồng|vnd|₫|won|yen|dollars?|usd|eur)", re.IGNORECASE)),
    # Currency prefix: "$5 billion", "¥300万", "₩50억"
    (ValueKind.CURRENCY, re.compile(
        rf"(?P<cur>\$|¥|₩|€)\s*{_NUM}\s*{_SCALE}", re.IGNORECASE)),
    # Measurement: "4,860 mg/kg", "0.2 ppm", "30 mg/kg"
    (ValueKind.MEASUREMENT, re.compile(
        rf"{_NUM}\s*(?P<unit>mg/kg|g/kg|µg/kg|μg/kg|mg/l|ppm|ppb|mg|kg|g|ml|l|msv|µsv)(?![a-zA-Z0-9])", re.IGNORECASE)),
]


def _to_float(raw: str) -> Optional[float]:
    if not raw:
        return None
    s = raw.strip().replace(" ", "")
    # Differentiate "1,234.5" (EN/US/JP) and "1.234,5" (VN/EU)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = s.replace(",", "") if len(tail) == 3 else f"{head.replace(',', '')}.{tail}"
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(Decimal(s))
    except (InvalidOperation, ValueError):
        return None


def parse_numbers(text: str) -> list[ParsedNumber]:
    """Parse all semantic numbers in multilingual text without overlapping spans."""
    results: list[ParsedNumber] = []
    taken: list[tuple[int, int]] = []

    for kind, pat in _PATTERNS:
        for m in pat.finditer(text or ""):
            span = m.span()
            if any(span[0] < e and s < span[1] for s, e in taken):
                continue
            value = _to_float(m.group("num"))
            if value is None:
                continue
            gd = m.groupdict()
            unit: Optional[str] = None
            if kind is ValueKind.CURRENCY:
                scale = gd.get("scale")
                if scale:
                    value *= _SCALE_WORDS.get(scale.lower(), _SCALE_WORDS.get(scale, 1.0))
                cur_raw = gd.get("cur") or ""
                unit = _CURRENCY_TOKENS.get(cur_raw.lower(), cur_raw)
            elif kind is ValueKind.MEASUREMENT:
                unit = gd.get("unit")
            elif kind is ValueKind.PERCENT:
                unit = "%"
            elif kind is ValueKind.MULTIPLIER:
                unit = "x"
            results.append(ParsedNumber(value, kind, unit, m.group(0), span))
            taken.append(span)

    return sorted(results, key=lambda p: p.span[0])


# ---------------------------------------------------------------------------
# Structured extraction from Grounding Intel (grounding_table / claims)
# ---------------------------------------------------------------------------
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "parameter": ("parameter", "substance", "metric", "item", "name", "claim_id"),
    "detected_value": ("detected_value", "detected", "measured", "actual", "value", "metric_value"),
    "baseline_value": ("baseline_value", "baseline", "limit", "standard_value", "threshold", "legal_limit"),
    "unit": ("unit", "units"),
    "standard_name": ("standard_name", "standard", "regulation", "law", "rule"),
    "secondary_baseline_value": ("secondary_baseline_value", "secondary_limit", "secondary_baseline"),
    "secondary_standard_name": ("secondary_standard_name", "secondary_standard", "destination_standard"),
    "source_citation": ("source_citation", "source", "citation", "reference", "url"),
}


def _pick(row: dict[str, Any], key: str) -> Any:
    for alias in _FIELD_ALIASES[key]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return None


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    parsed = parse_numbers(str(v))
    return parsed[0].value if parsed else _to_float(str(v))


def _safe_ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return round(float(a) / float(b), 4)


def _score_row(row: dict[str, Any]) -> int:
    score = 100 if row.get("is_primary") else 0
    score += 10 if _num(_pick(row, "detected_value")) is not None else 0
    score += 10 if _num(_pick(row, "baseline_value")) is not None else 0
    score += 3 if _pick(row, "standard_name") else 0
    score += 1 if _pick(row, "source_citation") else 0
    return score


def _from_rows(rows: Iterable[dict[str, Any]], market: str, provenance: str) -> Optional[QuantitativeProfile]:
    valid_rows = [r for r in rows if isinstance(r, dict)]
    if not valid_rows:
        return None
    row = max(valid_rows, key=_score_row)
    detected = _num(_pick(row, "detected_value"))
    baseline = _num(_pick(row, "baseline_value"))
    if detected is None and baseline is None:
        return None

    sec_base = _num(_pick(row, "secondary_baseline_value"))
    unit = _pick(row, "unit")
    kind = ValueKind.CURRENCY if unit and str(unit).upper() in set(_CURRENCY_TOKENS.values()) \
        else ValueKind.PERCENT if unit == "%" else ValueKind.MEASUREMENT

    p = QuantitativeProfile(
        status=ProfileStatus.OK if (detected is not None and baseline is not None) else ProfileStatus.PARTIAL,
        market=market,
        parameter=_pick(row, "parameter"),
        unit=unit,
        value_kind=kind,
        detected_value=detected,
        baseline_value=baseline,
        standard_name=_pick(row, "standard_name"),
        secondary_baseline_value=sec_base,
        secondary_standard_name=_pick(row, "secondary_standard_name"),
        ratio=_safe_ratio(detected, baseline),
        secondary_ratio=_safe_ratio(detected, sec_base),
        source_citation=_pick(row, "source_citation"),
        provenance=provenance,
    )
    if p.secondary_standard_name and p.secondary_ratio is None:
        p.warnings.append("secondary_standard_name present without secondary baseline; two-stage disabled")
        p.secondary_standard_name = None
    return p


def _from_narration(text: str, market: str) -> QuantitativeProfile:
    nums = parse_numbers(text)
    if not nums:
        return QuantitativeProfile(status=ProfileStatus.INSUFFICIENT_DATA, market=market,
                                   warnings=["no quantitative tokens in narration"])

    multipliers = [n for n in nums if n.kind is ValueKind.MULTIPLIER]
    if multipliers:
        primary = multipliers[0]
        secondary = next((m for m in multipliers[1:] if m.value > primary.value), None)
        return QuantitativeProfile(
            status=ProfileStatus.PARTIAL,
            market=market,
            value_kind=ValueKind.MULTIPLIER,
            unit="x",
            ratio=primary.value,
            secondary_ratio=secondary.value if secondary else None,
            provenance="narration",
            warnings=["ratio parsed from narration; baseline/standard unknown"],
        )

    for kind in (ValueKind.MEASUREMENT, ValueKind.CURRENCY, ValueKind.PERCENT):
        same = [n for n in nums if n.kind is kind]
        if len(same) >= 2 and same[0].unit == same[1].unit:
            hi = max(same[:2], key=lambda n: n.value)
            lo = min(same[:2], key=lambda n: n.value)
            return QuantitativeProfile(
                status=ProfileStatus.PARTIAL,
                market=market,
                value_kind=kind,
                unit=hi.unit,
                detected_value=hi.value,
                baseline_value=lo.value,
                ratio=_safe_ratio(hi.value, lo.value),
                provenance="narration",
                warnings=["detected/baseline inferred by magnitude; verify against grounding"],
            )
        if same:
            return QuantitativeProfile(
                status=ProfileStatus.PARTIAL,
                market=market,
                value_kind=kind,
                unit=same[0].unit,
                detected_value=same[0].value,
                provenance="narration",
                warnings=["single value only; no ratio computable"],
            )

    return QuantitativeProfile(status=ProfileStatus.INSUFFICIENT_DATA, market=market)


def extract_episode_quantitative_profile(
    grounding_intel: Optional[dict[str, Any]] = None,
    narration_text: Optional[str] = None,
    market: str = "EN",
) -> QuantitativeProfile:
    """Extract quantitative profile prioritizing structured grounding data over narration.
    Rule 128: ZERO hardcoded fallbacks to specific episode numbers.
    """
    intel = grounding_intel or {}
    for key in ("grounding_table", "claims", "key_figures"):
        items = intel.get(key)
        if items and isinstance(items, list):
            profile = _from_rows(items, market, key)
            if profile is not None:
                return profile
    return _from_narration(narration_text or "", market)
