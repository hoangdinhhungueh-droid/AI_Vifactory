"""Story Brain gate (outline stage) - measurable 12/12 check (v4), no network.

v4 upgrade 07/08/2026 per Phase 3 (Hand-off Viec 2 checklist A+B code-hoa):
v3's nine rules PLUS three new checks:
    10_banned_phrases   - expanded anti-AI-tone banned-phrase list (checklist A)
    11_according_to_cap - max 2 paragraphs opening with "According to X..." (checklist A)
    12_pattern_interrupt - at least 1 short sentence (<=6 words) in Mechanism (checklist B)

v3 upgrade 05/08/2026 per Hand-off Viec 2 decision: v2's six rules PLUS
narrative-arc and segmentation checks (ported from scripts/story_gate_v3.py)
now run inline at S3.6, so a flat wall of text with no dramatic structure can
no longer score max on the deterministic gate. Added after EP004 feedback:
"chua co hook, cac hoi ... khong phan biet duoc doan nao ra doan nao".

New checks vs v2:
    7_arc_five_acts  - the five acts (hook-shock / build / knot / resolution /
                       denouement) must each show their own cue vocabulary in
                       the correct fifth of the script.
    8_segmentation   - the story must be broken into paragraphs of a readable
                       size, so S2 can map beat -> scene cleanly.
    9_hook_shock     - the opening must land a concrete shock (number or
                       superlative) within the first 60 words, not just a
                       question.

Public API:
    score_story(story_text) -> dict with checks/score/max_score/verdict/fixes
    gate_mode() -> "off" | "warn" | "block"   (env VF_STORY_GATE)
"""
from __future__ import annotations

import math
import os
import re

WPM = 152.0

LOOP_OPEN = [
    r"\?",
    r"？",
    r"(?i)but (?:nobody|no one|almost no one|what)",
    r"(?i)what (?:nobody|no one|almost nobody) (?:knew|saw|noticed)",
    r"(?i)that number would",
    r"(?i)not yet",
    r"(?i)keep that (?:number|figure|date) in mind",
    r"(?i)we will come back to",
    r"(?i) but (?:nobody|no one|almost no one|what) ",
    r"(?i) what (?:nobody|no one|almost nobody) (?:knew|saw|noticed) ",
    r"(?i) that number would ",
    r"(?i) not yet ",
    r"(?i) keep that (?:number|figure|date) in mind ",
    r"(?i) we will come back to ",
    r"(?i) for now ",
    r"LOOP_OPEN",
    r"과연", r"의문", r"어째서", r"하지만 아무도", r"기억해야", r"알려지지 않은", r"진짜 이유는", r"진짜 질문은", r"수 있을까요", r"수 있을까",
    r"果たして", r"疑問", r"なぜ", r"しかし誰も", r"本当の理由は", r"だろうか",
]
LOOP_CLOSE = [
    r"(?i)\bthat is (?:why|how|when)\b",
    r"(?i)\bwhich is (?:why|how)\b",
    r"(?i)\bhere is (?:why|what happened|the answer)\b",
    r"(?i)\bremember (?:that|the)\b",
    r"(?i)\bthe answer\b",
    r"(?i)\bso when\b",
    r"(?i)\bin the end\b",
    r"LOOP_CLOSE",
    r"그 이유는", r"결국", r"답은", r"이처럼", r"드러난 사실은", r"비로소", r"그것이 바로", r"핵심은", r"필요합니다",
    r"その理由は", r"結局", r"答えは", r"こうして", r"明らかになったのは", r"まさに",
]
SOURCE = [
    r"(?i)according to",
    r"(?i)filing",
    r"(?i)report(?:ed|s)?",
    r"(?i)balance sheet",
    r"(?i)examiner",
    r"(?i)court",
    r"(?i)testimony",
    r"보고서", r"통계", r"조사", r"발표", r"기록", r"정부", r"기관", r"WHO", r"유엔", r"시스템", r"자료", r"세계보건기구", r"환경개선", r"농촌진흥청", r"국립농업과학원",
    r"報告", r"統計", r"調査", r"発表", r"記録", r"政府", r"機関", r"資料",
]
NUM = r"(?:\$\s?\d[\d,\.]*\s?(?:billion|million|trillion|B|M|T)?|[₩¥￥]\s?\d[\d,\.]*|\b\d[\d,\.]*\s?(?:%|percent|billion|million|trillion|years|employees|days|만|억|조|회|건|명|년|일|월|개|배|원|엔)\b|\b(?:1[89]|20)\d{2}\b)"

# --- act cue vocabularies (v3: each act must speak its own language) --------
ACT_CUES = {
    "act1_hook_shock": [
        r"(?i)(?:vanish|disappear|collapse[sd]?|gone|wiped out|shock|nobody|no one)",
        r"(?i)(?:largest|biggest|worst|first|only|never)",
        r"\?",
        r"？",
        r"충격", r"의문", r"붕괴", r"위험", r"shock", r"hook", r"조회수", r"질문", r"오염", r"추측",
        r"衝撃", r"崩壊", r"消失", r"最初", r"最悪", r"なぜ", r"危機",
    ],
    "act2_build": [
        r"(?i)narrative", r"(?i)headline", r"(?i)myth", r"(?i)believed", r"(?i)claimed", r"(?i)official story", r"(?i)misdirection", r"(?i)red herring", r"(?i)surface", r"truyền thông", r"lầm tưởng", r"giả thuyết", r"ngộ nhận", r"겉모습", r"보도", r"언론", r"오해", r"통념", r"オフィシャル", r"報道", r"誤解", r"神話",
        r"(?i) (?:founded|opened|grew|expanded|built|became|launched|rose|boom(?:ed|ing)?|empire) ",
        r"(?i) (?:by \d{4}|store[s]?|market share|dominat(?:ed|ing)) ",
        r"(?i) (?:originally|genesis|years earlier|years before|months earlier|origins?|root cause|initial deal|earliest|decades ago|dating back) ",
        r"시작", r"설립", r"성장", r"확장", r"등장", r"배경", r"역사", r"구축", r"증가", r"시스템", r"등록", r"제품", r"정보", r"농약",
        r"거슬러", r"당시", r"과거", r"발단", r"초기", r"체결", r"기원", r"이전", r"출발점", r"뿌리",
        r"創業", r"設立", r"成長", r"拡大", r"誕生", r"背景", r"歴史", r"急増", r"システム",
        r"遡る", r"当時", r"過去", r"発端", r"初期", r"起源", r"以前", r"原点",
    ],
    "act3_knot": [
        r"(?i)audit", r"(?i)leak", r"(?i)memo", r"(?i)email", r"(?i)paper trail", r"(?i)whistleblower", r"(?i)blindspot", r"(?i)vacuum", r"(?i)loophole", r"(?i)forensic", r"manh mối", r"tài liệu", r"rò rỉ", r"kẽ hở", r"điểm mù", r"내부", r"문건", r"유출", r"사각지대", r"맹점", r"비리", r"内部告発", r"流出", r"死角", r"不正",
        r"(?i) (?:but|however|then|instead|trap|debt|leverage[d]?|loan[s]?|interest|deal|buyout|pressure) ",
        r"(?i) (?:began to|started to|could not|couldn't|no longer) ",
        r"(?i) (?:escalat(?:e|ed|ing|ion)|unnoticed|behind closed doors|gradually|over time|brewing|warning sign|cracks?|mutation) ",
        r"그러나", r"하지만", r"문제", r"위기", r"압박", r"갈등", r"오염", r"의혹", r"맹점", r"한계", r"사각지대", r"재사용", r"용기",
        r"누적", r"서서히", r"물밑", r"균열", r"변질", r"간과", r"조짐", r"암운",
        r"しかし", r"だが", r"問題", r"危機", r"圧力", r"葛藤", r"亀裂", r"疑惑", r"落とし穴",
        r"蓄積", r"徐々に", r"水面下", r"変質", r"見過ご", r"兆候", r"暗雲",
    ],
    "act4_resolution": [
        r"(?i)smoking gun", r"(?i)culprit", r"(?i)profited", r"(?i)beneficiary", r"(?i)exposed", r"(?i)unmasked", r"(?i)climax", r"(?i)fatal", r"(?i)undone", r"(?i)crackdown", r"vạch trần", r"thủ phạm", r"bằng chứng", r"chuông báo tử", r"스모킹건", r"진범", r"폭로", r"결정적", r"증거", r"決定打", r"黒幕", r"暴露", r"証拠",
        r"(?i) (?:filed|bankrupt(?:cy)?|chapter 11|liquidat(?:e|ed|ion)|clos(?:ed|ing)|shut|court|creditors?|failed) ",
        r"조사", r"단속", r"판결", r"결과", r"조치", r"회수", r"폐기", r"수사", r"법원", r"실패", r"전환점", r"대응", r"검사", r"관리", r"책임",
        r"調査", r"処分", r"判決", r"自主回収", r"責任", r"停止", r"破綻", r"改革",
    ],
    "act5_denouement": [
        r"(?i)mirror", r"(?i)warning", r"(?i)modern", r"(?i)today", r"(?i)echo", r"(?i)repeat", r"(?i)lesson", r"(?i)verdict", r"soi chiếu", r"cảnh tỉnh", r"cảnh báo", r"bản án", r"gương soi", r"경고", r"거울", r"현대", r"되풀이", r"판결", r"現代", r"警告", r"教訓", r"判決",
        r"(?i)(?:today|years later|since then|legacy|remains?|lesson|aftermath|what happened to|left behind|still)",
        r"오늘날", r"현재", r"교훈", r"유산", r"결론", r"미래", r"과제", r"신뢰", r"남겨진", r"결국", r"식탁", r"제도", r"안전", r"회복",
        r"今日", r"現在", r"教訓", r"遺産", r"未来", r"信頼", r"課題", r"結論",
    ],
}
ACT_ORDER = ["act1_hook_shock", "act2_build", "act3_knot",
             "act4_resolution", "act5_denouement"]

SHOCK = r"(?:\$\s?\d[\d,\.]*\s?(?:billion|million|trillion|hundred|thousand)?|[₩¥￥]\s?\d[\d,\.]*|\b\d[\d,\.]*\s?(?:%|percent|만|억|조|회|건|명)|\b(?:largest|biggest|worst|deadliest|first|never|nobody|no one|collapse|bankrupt|stole|fraud|scandal|crash|tragedy|executed|shock|최대|최악|사망|붕괴|사기|스캔들|파산|충격|처음|비극|위험|검출|오염|독성|경고|最大|最悪|死亡|崩壊|詐欺|事件|破綻|衝撃)\b)"

MAX_PARA_WORDS = 160
MIN_PARAS = 15

# --- Checklist A: anti-AI-tone banned phrases (v4) ---------------------------
BANNED_PHRASES_GATE = [
    r"(?i)\blet'?s dive in\b",
    r"(?i)\bit'?s worth noting\b",
    r"(?i)\bunleash(?:d|es|ing)?\b",
    r"(?i)\bboundless\b",
    r"(?i)\bat the end of the day\b",
    r"(?i)\blittle did they know\b",
    r"(?i)\bthe truth is\b",
    r"(?i)\bunravel(?:ed|ing|s)?\b",
    r"(?i)\bunderscore(?:d|s|ing)?\b",
    # Sensitive Crime Safety Guardrail: Zero Graphic Gore (User Rule 05/09/2026)
    r"(?i)\bblood splatter(?:ed)?\b",
    r"(?i)\bmutilat(?:ed|ing|ion)\b",
    r"(?i)\bdecapitat(?:ed|ing|ion)\b",
    r"(?i)\bgruesome crime scene\b",
    r"(?i)\bphanh thây\b",
    r"(?i)\bvết máu be bét\b",
    r"(?i)\bman rợ\b",
    r"(?i)\bバラバラ殺人\b",
]

# --- Checklist A: "According to X..." opener cap (v4) ------------------------
ACCORDING_TO_RE = re.compile(r"(?im)^\s*according to\b")
MAX_ACCORDING_TO = 2

# --- Checklist B: pattern interrupt — short sentence in Mechanism (v4) -------
PATTERN_INTERRUPT_MAX_WORDS = 6


def _count(pats, text):
    return sum(len(re.findall(p, text)) for p in pats)


def _words(text: str) -> list[str]:
    if not text:
        return []
    # CJK-aware word segmentation for JP / KR support
    cjk_chars = re.findall(r'[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]', text)
    latin_words = re.findall(r'[a-zA-Z0-9_\-]+', text)
    
    if len(cjk_chars) > len(latin_words):
        korean_chars = re.findall(r'[\uac00-\ud7af]', text)
        if len(korean_chars) > len(cjk_chars) * 0.5:
            return text.split()
        else:
            # Japanese: chunk by punctuation and ~2.5 chars per word unit
            tokens = []
            cur = ""
            delims = set([' ', '\t', '\r', '\n', '、', '。', '！', '？', ',', '.', '!', '?'])
            for ch in text:
                if ch in delims:
                    if cur:
                        tokens.append(cur)
                        cur = ""
                else:
                    cur += ch
                    if len(cur) >= 3:
                        tokens.append(cur)
                        cur = ""
            if cur:
                tokens.append(cur)
            return tokens if tokens else text.split()

    return text.split()


def gate_mode() -> str:
    v = (os.getenv("VF_STORY_GATE", "block") or "block").strip().lower()  # default flipped 27/07/2026: pm2 does not carry launch env
    return v if v in ("off", "warn", "block") else "warn"


def score_story(story_text: str) -> dict:
    story = story_text or ""
    words = _words(story)
    nwords = len(words)

    # Multi-lingual pacing & duration calibration (Rule 128 & Rule 120)
    cjk_chars = re.findall(r'[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]', story)
    latin_words = re.findall(r'[a-zA-Z0-9_\-]+', story)
    is_cjk = len(cjk_chars) > len(latin_words)
    korean_chars = re.findall(r'[\uac00-\ud7af]', story)
    is_korean = len(korean_chars) > len(cjk_chars) * 0.5 if is_cjk else False

    if is_korean:
        # Korean narration speed: ~245 syllables/min in investigative docudrama
        minutes = len(korean_chars) / 245.0 if korean_chars else (nwords / WPM)
        min_len = 950
        max_len = 1650
    elif is_cjk:
        # Japanese/Chinese narration speed: ~275 characters/min
        minutes = len(cjk_chars) / 275.0 if cjk_chars else (nwords / WPM)
        min_len = 1000
        max_len = 1800
    else:
        minutes = nwords / WPM if nwords else 0.0
        min_len = 1700
        max_len = 2500

    sents = [s for s in re.split(r"(?<=[.!?])\s+", story) if s.strip()]
    hook = " ".join(sents[:8] if len(sents) >= 8 else sents)  # Expand to first 8 sents to capture multi-para opening questions
    first60 = " ".join(words[:60])

    nums = re.findall(NUM, story)
    loops_open = _count(LOOP_OPEN, story)
    loops_close = _count(LOOP_CLOSE, story)
    sources = _count(SOURCE, story)
    need_loops = max(1, math.ceil(minutes / 1.5)) if minutes else 1
    need_nums = max(1, math.ceil(minutes * 60 / 90)) if minutes else 1

    # --- arc (v3): split into five equal-word fifths, score each act's own cues
    fifth = max(1, nwords // 5)
    segments = [" ".join(words[i * fifth:(i + 1) * fifth]) for i in range(5)]
    if nwords > fifth * 5:
        segments[4] += " " + " ".join(words[fifth * 5:])
    arc_hits = {}
    for i, act in enumerate(ACT_ORDER):
        arc_hits[act] = _count(ACT_CUES[act], segments[i]) if i < len(segments) else 0
    acts_present = sum(1 for v in arc_hits.values() if v >= 2)

    # --- segmentation (v3) ----------------------------------------------------
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", story) if p.strip()]
    para_words = [len(_words(p)) for p in paras]
    oversized = [w for w in para_words if w > MAX_PARA_WORDS]
    longest_para = max(para_words) if para_words else nwords

    # --- Checklist A: anti-AI-tone (v4) ---------------------------------------
    banned_hits = []
    for pat in BANNED_PHRASES_GATE:
        m = re.search(pat, story)
        if m:
            banned_hits.append(m.group(0))
    according_to_count = len(ACCORDING_TO_RE.findall(story))

    # --- Checklist B: pattern interrupt (v4) ----------------------------------
    # Mechanism = 25%-70% of the script (Hoi 2)
    mech_start = int(nwords * 0.25)
    mech_end = int(nwords * 0.70)
    if mech_end > mech_start:
        mechanism_text = " ".join(words[mech_start:mech_end])
    else:
        mechanism_text = story
    mech_sents = [s for s in re.split(r"(?<=[.!?])\s+", mechanism_text) if s.strip()]
    short_sents = [s for s in mech_sents if 2 <= len(_words(s)) <= PATTERN_INTERRUPT_MAX_WORDS]

    checks = {
        "1_length_1700_2500_words": min_len <= nwords <= max_len,
        "2_hook_has_open_question": bool(re.search(r"\?", hook)) or _count(LOOP_OPEN[1:], hook) > 0,
        "3_open_loops_enough": loops_open >= need_loops,
        "4_loops_closed": loops_close >= max(1, math.ceil(need_loops * 0.5)),
        "5_sourced_numbers": len(nums) >= need_nums and sources >= 2,
        "6_pace_in_band": min_len <= nwords <= max_len,
        "7_arc_five_acts": acts_present == 5,
        "8_segmentation": len(paras) >= MIN_PARAS and not oversized,
        "9_hook_shock_in_first_60w": bool(re.search(SHOCK, first60)),
        "10_banned_phrases": len(banned_hits) == 0,
        "11_according_to_cap": according_to_count <= MAX_ACCORDING_TO,
        "12_pattern_interrupt": len(short_sents) >= 1,
    }
    failed = [k for k, v in checks.items() if not v]
    fixes = {
        "1_length_1700_2500_words": "Rewrite outline to land 1700-2500 words (12-16 min at 152 wpm).",
        "2_hook_has_open_question": "Open with an unanswered question in the first 15 seconds.",
        "3_open_loops_enough": "Plant one open loop every 60-90s (LOOP_OPEN vocabulary).",
        "4_loops_closed": "Every loop opened must be paid off (LOOP_CLOSE vocabulary).",
        "5_sourced_numbers": "At least one sourced number per 90s and >=2 named sources.",
        "6_pace_in_band": "Adjust script length so pace stays in the 145-160 wpm band (1700-2500 words).",
        "7_arc_five_acts": "Each fifth of the script must speak its own act's vocabulary (hook-shock/build/knot/resolution/denouement) at least twice.",
        "8_segmentation": "Break into >= " + str(MIN_PARAS) + " paragraphs, none longer than " + str(MAX_PARA_WORDS) + " words, so S2 can map beat to scene.",
        "9_hook_shock_in_first_60w": "Land a concrete shock (a number, %, or superlative) within the first 60 words.",
        "10_banned_phrases": "Remove banned AI-cliche phrases: " + ", ".join(banned_hits) if banned_hits else "No banned phrases found.",
        "11_according_to_cap": "Limit 'According to X...' openers to <= " + str(MAX_ACCORDING_TO) + " paragraphs (found " + str(according_to_count) + ").",
        "12_pattern_interrupt": "Add at least 1 very short sentence (<= " + str(PATTERN_INTERRUPT_MAX_WORDS) + " words) in the Mechanism section (25%-70%) to break rhythm.",
    }
    score = sum(1 for v in checks.values() if v)
    max_score = len(checks)
    return {
        "words": nwords,
        "est_minutes": round(minutes, 2),
        "paragraphs": len(paras),
        "longest_paragraph_words": longest_para,
        "oversized_paragraphs": len(oversized),
        "numbers_found": len(nums),
        "numbers_required": need_nums,
        "open_loop_markers": loops_open,
        "open_loops_required": need_loops,
        "close_markers": loops_close,
        "source_markers": sources,
        "arc_hits_per_act": arc_hits,
        "acts_present": acts_present,
        "hook_preview": hook[:220],
        "banned_phrases_found": banned_hits,
        "according_to_count": according_to_count,
        "pattern_interrupt_short_sents": len(short_sents),
        "checks": checks,
        "failed": failed,
        "fix_hints": [fixes[k] for k in failed],
        "score": score,
        "max_score": max_score,
        "pass_rate": round(score / max_score * 100, 1),
        "verdict": "PASS" if (score / max_score) >= 0.80 and len(banned_hits) == 0 else "FAIL",
    }
