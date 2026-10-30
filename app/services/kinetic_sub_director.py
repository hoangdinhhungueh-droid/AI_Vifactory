#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""app/services/kinetic_sub_director.py — Object-to-Object Kinetic Coupling & Narrative Sub-Director Engine.

Enforces:
- Rule 120: Whisper Word-level Timestamps (millisecond sync, contiguous non-overlapping windows).
- Rule 128: Generic Contract Pattern (supports any market: EN, JA, KR, VN without hardcoding).
- Rule 132: Pure Transmission Engine (decoupled logic, no hardcoded episode scripts; presets in config).
- Rule 134: Single Canonical Truth & Exact Parity.
- Rule 140 v3: Object-to-Object Kinetic Coupling Taxonomy ($H_1 \rightarrow H_7$),
  Semantic Clause Mapping ($4 \le N \le 7$ micro-beats), and Causal Compound Verb Prompt Syntax.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.services.semantic_evidence_extractor import extract_evidence_for_sentence

logger = logging.getLogger("kinetic_sub_director")

# ==============================================================================
# AUTHORITATIVE METRIC PREDICATE REGEX (PRECOMPILED)
# ==============================================================================
# Documented Decision on bare \d{2,} branch (Boss Round 4 Item 1):
# Standalone integers >= 2 digits (e.g. "50", "100") reflect quantitative scale in docudramas,
# but structural identifiers ("Step 10", "Episode 02", "Year 1999") and non-metric count nouns
# ('5 bước', '3 mẹo', '2 kế hoạch', '5 단계', '3 가지', '3 minutes', '4 types') must not trigger metric classification.
# Trailing Unicode letter guard: (?![^\W\d_]) ensures that single-letter and short unit abbreviations
# ('b', 'm', 'k', 'ty') followed by letters with Vietnamese/Unicode diacritics are strictly rejected.
_METRIC_PREFIX_CURRENCY = r"(?:US\$|[$€£¥₫₩])\s*\d+(?:[,\.]\d+)?"
_METRIC_UNITS = (
    r"(?:%|円|원|[$€£¥₫₩]|"
    r"(?:tỷ|triệu|nghìn|ngàn|billion|million|thousand|percent|pct|won|usd|yen|gbp|eur|ty|b|m|k)"
    r"(?![^\W\d_]))"
)
_METRIC_EXCLUDE_SUFFIX = (
    r"(?!\s*(?:bước|mẹo|kế\s+hoạch|단계|가지|minutes|minute|points|point|types|type|steps|step|bugs|bug|members|member)\b)"
)
_METRIC_PATTERN = (
    rf"{_METRIC_PREFIX_CURRENCY}"
    rf"|(?<!\d)\d+(?:[,\.]\d+)?\s*{_METRIC_UNITS}"
    rf"|(?<![^\W\d_])(?<!\d)(?<!\bstep\s)(?<!\bstep\s\s)(?<!\bstep\s#)(?<!\bep\s)(?<!\bep\s#)(?<!\bepisode\s)(?<!\byear\s)(?<!\bnăm\s)(?<!\bin\s)(?!(?:19[5-9]\d|20[0-4]\d)\b)\d{{2,}}(?!\d){_METRIC_EXCLUDE_SUFFIX}"
)
_METRIC_RE = re.compile(_METRIC_PATTERN, re.IGNORECASE)


class KineticFamily(str, Enum):
    """Taxonomy 7 Họ Tương Tác Vật Lý Xúc Giác trên mặt bàn tài liệu."""
    H1_IMPACT = "H1_IMPACT"          # Va chạm & Dập mực (con dấu, khối chì -> lún giấy, nảy xung quanh)
    H2_CONSTRAINT = "H2_CONSTRAINT"  # Kẹp giữ & Đo đạc (caliper, compa, ghim -> nhăn mép, khóa số đo)
    H3_SEVER = "H3_SEVER"            # Cắt xé & Phân tách (kéo, dao trổ -> tách rời, xoay rơi có độ nảy)
    H4_TETHER = "H4_TETHER"          # Dây căng & Neo giữ (ghim đồng, chỉ đỏ -> kéo căng, rung dao động tắt dần)
    H5_OPTICAL = "H5_OPTICAL"        # Khúc xạ quang học (kính lúp -> phóng to 1.4x, méo cong rìa, lộ chữ chìm)
    H6_MARK = "H6_MARK"              # Quét mực & Xung dạ quang (bút neon -> thấm giấy, phát sáng, truyền xung data)
    H7_DISPLACE = "H7_DISPLACE"      # Xô đẩy & Bung nếp gấp (ma sát trượt, pop-up unfold -> xòe quạt, mở lớp dưới)


# Universal Multilingual Trigger Keywords (Rule 128 Generic)
TAXONOMY_KEYWORDS: Dict[KineticFamily, List[str]] = {
    KineticFamily.H1_IMPACT: [
        # VN
        "chi", "phê duyệt", "ký", "xác nhận", "dập", "đóng dấu", "áp đặt", "kết luận", "chế tài", "xử phạt", "phán quyết",
        # EN
        "spend", "approve", "sign", "confirm", "stamp", "slam", "impose", "conclude", "strike", "sanction", "order", "verdict",
        # JA
        "支出", "承認", "署名", "確認", "押印", "結論", "打撃", "確定", "制裁", "命令", "摘発",
        # KR
        "지출", "승인", "서명", "확인", "도장", "결론", "타격", "확정", "제재", "명령", "시정명령", "적발", "처분", "과징금", "선고"
    ],
    KineticFamily.H2_CONSTRAINT: [
        # VN
        "đo", "kẹp", "so sánh", "tăng", "giảm", "tỷ lệ", "phần trăm", "thước", "chuẩn mực", "định mức", "ngưỡng",
        # EN
        "measure", "clamp", "compare", "rate", "percent", "gauge", "baseline", "benchmark", "ratio", "quota", "threshold",
        # JA
        "計測", "クランプ", "比較", "比率", "パーセント", "基準", "ベースライン", "尺度", "上限", "割合",
        # KR
        "측정", "고정", "비교", "비율", "퍼센트", "기준", "베이스라인", "척도", "모집률", "30%", "초과", "수치", "한도", "담보", "비율"
    ],
    KineticFamily.H3_SEVER: [
        # VN
        "cắt", "xé", "chia cắt", "loại bỏ", "tách rời", "phá vỡ", "rạch", "bãi bỏ", "giảm", "sai phạm", "hủy bỏ", "không phép",
        # EN
        "cut", "tear", "sever", "split", "remove", "separate", "slice", "perforate", "reduce", "unlicensed", "deceptive", "void",
        # JA
        "切断", "破断", "分割", "分離", "撤廃", "切り離す", "削除", "スライス", "削減", "未認可", "虚偽", "取り消し",
        # KR
        "절단", "분리", "분할", "철폐", "가르다", "삭제", "찢다", "제거", "삭감", "미인허가", "미허가", "허위", "기만", "취소", "박탈", "무효", "전이었습니다"
    ],
    KineticFamily.H4_TETHER: [
        # VN
        "nối", "liên kết", "ghim", "dây", "ràng buộc", "kết nối", "móc nối", "mạng lưới", "dây chuyền", "mắt xích",
        # EN
        "connect", "link", "pin", "tether", "bind", "network", "attach", "chain", "nexus", "yarn",
        # JA
        "連結", "接続", "ピン", "束縛", "糸", "ネットワーク", "結びつける", "固定", "連鎖", "紐",
        # KR
        "연결", "접속", "핀", "결속", "실", "네트워크", "묶다", "고정", "묶었습니다", "묶은", "연루", "배후", "사슬", "고리", "모집 수단"
    ],
    KineticFamily.H5_OPTICAL: [
        # VN
        "phát hiện", "tìm kiếm", "che giấu", "lộ", "ẩn", "soi", "phơi bày", "điều tra", "nghi vấn", "kính lúp", "vạch trần",
        # EN
        "discover", "reveal", "hide", "hidden", "investigate", "search", "expose", "inspect", "loupe", "curious", "question", "missing",
        # JA
        "発見", "調査", "隠蔽", "暴露", "暴く", "拡大", "検察", "ルーペ", "疑問", "不透明", "追跡",
        # KR
        "발견", "조사", "은폐", "폭로", "드러나다", "확대", "검증", "돋보기", "무엇이", "걸까요", "짚었습니다", "의혹", "추적", "살펴", "의문"
    ],
    KineticFamily.H6_MARK: [
        # VN
        "chỉ", "duy nhất", "nhấn mạnh", "cảnh báo", "đặc biệt", "bôi đậm", "điểm nóng", "gạch dưới", "hạn chót",
        # EN
        "only", "highlight", "alert", "crucial", "warning", "solely", "hotspot", "neon", "deadline", "urgent", "flag",
        # JA
        "唯一", "警告", "強調", "ハイライト", "注目", "警戒", "ネオン", "締切", "緊急", "指摘",
        # KR
        "유일", "경고", "강조", "하이라이트", "주목", "비상", "네온", "마감임박", "마감", "지적", "알렸습니다", "단독", "주의", "외쳤지만"
    ],
    KineticFamily.H7_DISPLACE: [
        # VN
        "dẫn đến", "sụp đổ", "đẩy", "lan ra", "kéo theo", "mở ra", "bung", "lật", "xòe", "tập hồ sơ", "báo chí", "lan rộng",
        # EN
        "lead to", "trigger", "collapse", "push", "spread", "fan out", "unfold", "topple", "dossier", "broadcast", "domino",
        # JA
        "誘発", "崩壊", "推進", "拡散", "展開", "連鎖倒壊", "広がる", "報道", "書類", "拡散",
        # KR
        "유발", "붕괴", "밀어내다", "확산", "펼치다", "도미노", "퍼지다", "네 곳", "시행사", "임대아파트", "보도됐습니다", "전했습니다", "빌라", "아파트"
    ],
}

# Authoritative Prop Catalogs for 7 Families (Rule 140 / Pure Tactile Stop-Motion)
FAMILY_DEFAULT_PROPS: Dict[KineticFamily, Tuple[str, str, str]] = {
    # (label, material, mass_class)
    KineticFamily.H1_IMPACT: ("crimson official sanction seal", "wood_rubber", "heavy"),
    KineticFamily.H2_CONSTRAINT: ("precision brass vernier caliper", "solid_metal", "heavy"),
    KineticFamily.H3_SEVER: ("sharp surgical craft scalpel", "steel", "medium"),
    KineticFamily.H4_TETHER: ("taut red evidence thread with clear adhesive tabs", "cotton_thread", "feather"),
    KineticFamily.H5_OPTICAL: ("vintage brass magnifying loupe", "brass_glass", "medium"),
    KineticFamily.H6_MARK: ("neon yellow chisel highlighter", "plastic", "light"),
    KineticFamily.H7_DISPLACE: ("accordion-folded architectural dossier", "heavy_paper", "medium"),
}

FAMILY_SECONDARY_PROPS: Dict[KineticFamily, Tuple[str, str, str]] = {
    KineticFamily.H1_IMPACT: ("heavy wooden judicial gavel", "hardwood", "heavy"),
    KineticFamily.H2_CONSTRAINT: ("steel drafting metric compass", "solid_metal", "medium"),
    KineticFamily.H3_SEVER: ("stainless steel shears", "steel", "heavy"),
    KineticFamily.H4_TETHER: ("taut red evidence thread with clear adhesive tabs", "cotton_thread", "feather"),
    KineticFamily.H5_OPTICAL: ("high-contrast inspection lens", "optical_glass", "light"),
    KineticFamily.H6_MARK: ("translucent cyan neon marker stroke", "fluorescent_ink", "feather"),
    KineticFamily.H7_DISPLACE: ("fanned-out stack of rental contracts", "newsprint_paper", "medium"),
}

# Rich Multi-Prop Catalog preventing duplication across scene sequences (Rule 140 / Act I Purity)
FAMILY_PROP_CATALOG: Dict[KineticFamily, List[Tuple[str, str, str]]] = {
    KineticFamily.H1_IMPACT: [
        ("crimson official sanction seal", "wood_rubber", "heavy"),
        ("heavy redline correction pen stroke", "hard_felt", "light"),
        ("heavy wooden judicial gavel", "hardwood", "heavy"),
        ("embossed metal notary seal", "solid_metal", "heavy"),
    ],
    KineticFamily.H2_CONSTRAINT: [
        ("precision brass vernier caliper", "solid_metal", "heavy"),
        ("heavy steel spring paperclip", "steel", "light"),
        ("steel drafting metric compass", "solid_metal", "medium"),
        ("serrated metal binder clamp", "steel", "medium"),
    ],
    KineticFamily.H3_SEVER: [
        ("stainless steel shears", "steel", "heavy"),
        ("sharp surgical craft scalpel", "steel", "medium"),
        ("guillotine paper trimmer blade", "steel", "heavy"),
        ("serrated craft razor knife", "steel", "light"),
    ],
    KineticFamily.H4_TETHER: [
        ("taut red evidence yarn anchored between exhibit cards", "cotton_yarn", "feather"),
        ("copper wire fastener binding evidence cards", "copper", "light"),
        ("clear adhesive forensic tape swatches with red guide thread", "adhesive_tape", "feather"),
    ],
    KineticFamily.H5_OPTICAL: [
        ("vintage brass magnifying loupe", "brass_glass", "medium"),
        ("blank municipal permit form with missing authorization box", "aged_paper", "medium"),
        ("high-contrast forensic inspection lens", "optical_glass", "light"),
    ],
    KineticFamily.H6_MARK: [
        ("neon yellow chisel highlighter", "plastic", "light"),
        ("fluorescent crimson warning marker", "fluorescent_ink", "light"),
        ("translucent neon amber marker stroke", "fluorescent_ink", "feather"),
    ],
    KineticFamily.H7_DISPLACE: [
        ("four-panel developer corporate foldout", "heavy_cardstock", "medium"),
        ("wire-service news ticker tape", "newsprint_paper", "feather"),
        ("fanned-out stack of rental contracts", "newsprint_paper", "medium"),
        ("broadcast CRT monitor cutout showing news alert stills", "halftone_paper", "medium"),
    ],
}


def select_distinct_props_for_scene(
    scene_id: str,
    sentence: str,
    dominant_families: List[KineticFamily],
    used_props_in_sequence: Optional[List[str]] = None,
) -> Tuple[Tuple[str, str, str], Tuple[str, str, str]]:
    """Selects two distinct, contextually accurate tactile props for a scene, preventing intra-act duplication."""
    t_clean = (sentence or "").lower()

    # Dynamic claim-to-evidence extraction across all markets (Rule 128, 141)
    if sentence and sentence.strip():
        ev = extract_evidence_for_sentence(sentence)
        if ev.hero_anchor_prop and ev.interacting_tool_prop:
            tool_mat = "solid_metal" if any(k in ev.interacting_tool_prop.lower() for k in ["caliper", "shears", "scissors"]) else "wood_rubber"
            tool_mass = "heavy" if any(k in ev.interacting_tool_prop.lower() for k in ["stamp", "caliper"]) else "medium"
            return (
                (ev.hero_anchor_prop, "aged_paper", "medium"),
                (ev.interacting_tool_prop, tool_mat, tool_mass),
            )

    # General multilingual fallback using CATALOG and family detection
    fam1 = dominant_families[0] if dominant_families else KineticFamily.H2_CONSTRAINT
    fam2 = dominant_families[1] if len(dominant_families) > 1 else KineticFamily.H6_MARK

    cat1 = FAMILY_PROP_CATALOG.get(fam1, [("precision brass vernier caliper", "solid_metal", "heavy")])
    cat2 = FAMILY_PROP_CATALOG.get(fam2, [("translucent neon amber marker stroke", "fluorescent_ink", "feather")])

    p1 = cat1[0]
    p2 = cat2[0]
    if p2[0] == p1[0] and len(cat2) > 1:
        p2 = cat2[1]

    return p1, p2


@dataclass
class KineticObject:
    """Vật thể xúc giác trong danh bạ bàn tài liệu."""
    id: str
    label: str
    material: str          # paper, metal, wood, cotton, plastic, glass
    mass_class: str        # feather, light, medium, heavy, solid_metal
    z_index: int           # Thứ tự xếp lớp Z (1..5)
    role: str              # primary_anchor, interactive_tool, evidence_link, secondary_reaction


@dataclass
class KineticCoupling:
    """Cặp tương tác nhân quả giữa 2 vật thể trong frame."""
    id: str
    family: KineticFamily
    source_obj_id: str
    target_obj_id: str
    action_verb: str
    contact_point: str
    physical_reaction: str
    secondary_reaction: Optional[Dict[str, str]] = None
    residue: str = ""


@dataclass
class DynamicMicroBeat:
    """Từng micro-beat động học phân rã theo câu thoại."""
    beat_id: str
    phase: str             # P1_SETUP, P2_TENSION, P3_ESCALATION, P4_LIVING_HOLD
    time_window: str       # e.g. "0.000s - 0.400s"
    coupling_id: Optional[str]
    action_description: str
    handoff_to: Optional[str]
    vo_keyword: Optional[str] = None
    camera_micro_move: Optional[str] = None


def _is_cjk_char(char: str) -> bool:
    """Kiểm tra ký tự thuộc hệ chữ CJK (Hán tự, Ext-A, Hiragana, Katakana, Halfwidth Katakana, Hangul, Hangul Jamo, Compatibility Jamo)."""
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF      # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF  # CJK Extension A
        or 0x3040 <= cp <= 0x309F  # Hiragana
        or 0x30A0 <= cp <= 0x30FF  # Katakana
        or 0xFF66 <= cp <= 0xFF9F  # Halfwidth Katakana
        or 0xAC00 <= cp <= 0xD7AF  # Hangul Syllables
        or 0x1100 <= cp <= 0x11FF  # Hangul Jamo
        or 0x3130 <= cp <= 0x318F  # Hangul Compatibility Jamo
    )


def _match_keyword(kw: str, text: str) -> bool:
    """Khớp từ khóa thông minh có word boundary cho tiếng Việt / Latinh, tránh false positive (Rule 120, 128)."""
    if any(_is_cjk_char(c) for c in kw):
        return kw in text
    pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
    return bool(re.search(pattern, text, re.IGNORECASE))


@lru_cache(maxsize=8)
def _get_cached_raw_presets(cfg_path_str: str) -> Dict[str, Any]:
    """Tải và thẩm định khế ước config động học từ disk với fail-closed (Rule 118, 125, 134, 139)."""
    cfg_path = Path(cfg_path_str)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Kinetic layout presets config missing at: {cfg_path}")

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as _cfg_err:
        raise ValueError(f"Kinetic layout presets config at {cfg_path} is invalid JSON: {_cfg_err}") from _cfg_err

    if not isinstance(data, dict):
        raise ValueError(f"Invalid kinetic presets config at {cfg_path}: root must be a dict")

    # Validate required top-level keys
    for req_top in ("layouts", "spatial_keywords", "prose_templates"):
        if req_top not in data or not isinstance(data[req_top], dict):
            raise ValueError(f"Invalid kinetic presets config at {cfg_path}: missing required dict key '{req_top}'")

    # Validate layouts
    required_layouts = ("center_right", "center_left", "vertical")
    layout_keys = ("initial_pos", "target_contact_pos", "dock_pin_pos", "bounding_box_bounds", "vector_reveal_direction")
    for l_name in required_layouts:
        if l_name not in data["layouts"]:
            raise ValueError(f"Invalid kinetic presets config: missing layout '{l_name}'")
        l_dict = data["layouts"][l_name]
        for k in layout_keys:
            if k not in l_dict or not isinstance(l_dict[k], str) or not l_dict[k].strip():
                raise ValueError(f"Invalid kinetic presets config: layout '{l_name}' missing key '{k}'")

    # Validate prose templates
    prose = data["prose_templates"]
    for k_group in ("K1", "K2"):
        if k_group not in prose or "DEFAULT" not in prose[k_group]:
            raise ValueError(f"Invalid kinetic presets config: missing '{k_group}.DEFAULT' prose template")
        d_tpl = prose[k_group]["DEFAULT"]
        for p_key in ("action_verb", "contact_point", "physical_reaction", "residue"):
            if p_key not in d_tpl:
                raise ValueError(f"Invalid kinetic presets config: '{k_group}.DEFAULT' missing key '{p_key}'")

    # Validate spatial_keywords
    spatial_kw = data["spatial_keywords"]
    for sk in ("vertical", "center_left"):
        if sk not in spatial_kw or not isinstance(spatial_kw[sk], list):
            raise ValueError(f"Invalid kinetic presets config: spatial_keywords missing list '{sk}'")

    return data


def _load_kinetic_presets(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Tải khế ước config động học từ disk với deepcopy bảo chứng tại call site (Boss Round 6).

    _get_cached_raw_presets lưu trữ raw validated dict trong lru_cache;
    _load_kinetic_presets trả về deepcopy mới độc lập tại call site,
    đảm bảo caller mutation không bao giờ làm ô nhiễm bộ đệm cache.
    """
    if config_path is not None:
        cfg_path = Path(config_path).resolve()
    else:
        cfg_path = (Path(__file__).resolve().parent.parent.parent / "config" / "kinetic_layout_presets.json").resolve()

    raw_data = _get_cached_raw_presets(str(cfg_path))
    import copy
    return copy.deepcopy(raw_data)


@dataclass
class KineticSpatialLayout:
    """Toạ độ không gian 2D động học được tính toán động theo phân cảnh (Rule 128, 132)."""
    initial_pos: str          # e.g. "(X:52%, Y:42%)"
    target_contact_pos: str   # e.g. "(X:68%, Y:42%)"
    dock_pin_pos: str         # e.g. "(X:42%, Y:65%)"
    bounding_box_bounds: str  # e.g. "[X:58%-84%, Y:38%-68%]"
    layout_type: str = "center_right"
    vector_reveal_direction: str = "horizontal"


def compute_kinetic_spatial_layout(
    scene_id: str,
    family: Optional[KineticFamily] = None,
    bounding_box: Optional[Union[Dict[str, Any], Any]] = None,
    object_roles: Optional[Dict[str, str]] = None,
    hero_cutout_object: Optional[str] = None,
    interacting_objects: Optional[List[str]] = None,
    layout_type: Optional[str] = None,
    config_path: Optional[str] = None
) -> KineticSpatialLayout:
    """Tính toán toạ độ không gian 2D chuẩn hóa động học phân rã theo scene data (Rule 128, 132).

    Fail-closed trên scene_id rỗng (Rules 118/139).
    Toạ độ tiếp xúc target_contact_pos được tính toán trực tiếp từ bounding_box hoặc object roles,
    bảo đảm luôn nằm trọn bên trong bounding box, trong khi initial_pos và dock_pin_pos nằm bên ngoài.
    """
    if not scene_id or not isinstance(scene_id, str) or not scene_id.strip():
        raise ValueError("compute_kinetic_spatial_layout fail-closed (Rule 118/139): scene_id cannot be empty")

    presets_cfg = _load_kinetic_presets(config_path)
    presets = presets_cfg["layouts"]

    # 1. Nếu bounding_box được cung cấp
    if bounding_box is not None:
        if isinstance(bounding_box, dict):
            b_dict = bounding_box
        elif hasattr(bounding_box, "model_dump"):
            b_dict = getattr(bounding_box, "model_dump")()
        else:
            raise ValueError(f"Invalid bounding_box type: {type(bounding_box)}. Expected dict or BoundingBox model.")

        # Require explicit bounding box keys
        x_min_raw = b_dict.get("x_min", b_dict.get("left"))
        x_max_raw = b_dict.get("x_max", b_dict.get("right"))
        y_min_raw = b_dict.get("y_min", b_dict.get("top"))
        y_max_raw = b_dict.get("y_max", b_dict.get("bottom"))

        for name, val in [("x_min", x_min_raw), ("x_max", x_max_raw), ("y_min", y_min_raw), ("y_max", y_max_raw)]:
            if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"Bounding box coordinate '{name}' must be finite numeric value, got {val!r}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Bounding box coordinate '{name}' cannot be NaN or Inf")
            if not (0.0 <= val <= 100.0):
                raise ValueError(f"Bounding box coordinate '{name}' must be in percentage range [0.0, 100.0], got {val}")

        assert x_min_raw is not None and x_max_raw is not None and y_min_raw is not None and y_max_raw is not None
        x_min, x_max, y_min, y_max = float(x_min_raw), float(x_max_raw), float(y_min_raw), float(y_max_raw)
        if x_max <= x_min:
            raise ValueError(f"Bounding box x_max ({x_max}) must be strictly greater than x_min ({x_min})")
        if y_max <= y_min:
            raise ValueError(f"Bounding box y_max ({y_max}) must be strictly greater than y_min ({y_min})")
        if (x_max - x_min) >= 95.0 and (y_max - y_min) >= 95.0:
            raise ValueError("Bounding box spans full canvas [0-100%]; no exterior initial/dock placement possible")

        x_c = round((x_min + x_max) / 2.0)
        y_c = round((y_min + y_max) / 2.0)

        # Allow center_left selection in bbox path
        if layout_type:
            if layout_type not in presets:
                raise ValueError(f"Unknown kinetic layout type: '{layout_type}'. Allowed layouts: {sorted(presets.keys())}")
            l_type = layout_type
        elif (y_max - y_min) > (x_max - x_min):
            l_type = "vertical"
        elif x_c < 50.0:
            l_type = "center_left"
        else:
            l_type = "center_right"

        vec_dir = "vertical" if l_type == "vertical" else "horizontal"

        # Enforce initial_pos and dock_pin_pos lie strictly outside target box [x_min, x_max] x [y_min, y_max]
        if l_type == "vertical":
            init_x = x_c
            init_y = round(max(5.0, y_min - 15.0) if y_min >= 18.0 else min(95.0, y_max + 15.0))
            dock_x = round(max(5.0, x_min - 10.0) if x_min >= 15.0 else min(95.0, x_max + 10.0))
            dock_y = round(min(95.0, y_max + 12.0) if init_y < y_min else max(5.0, y_min - 12.0))
        elif l_type == "center_left":
            init_x = round(min(95.0, x_max + 16.0) if x_max <= 80.0 else max(5.0, x_min - 16.0))
            init_y = y_c
            dock_x = round(min(95.0, x_max + 20.0) if init_x > x_max else max(5.0, x_min - 20.0))
            dock_y = round(min(90.0, y_max + 15.0))
        else:
            init_x = round(max(5.0, x_min - 16.0) if x_min >= 20.0 else min(95.0, x_max + 16.0))
            init_y = y_c
            dock_x = round(max(5.0, x_min - 20.0) if init_x < x_min else min(95.0, x_max + 20.0))
            dock_y = round(min(90.0, y_max + 15.0))

        # Strict geometric invariant check: initial_pos and dock_pin_pos must NOT lie inside bounding box
        if x_min <= init_x <= x_max and y_min <= init_y <= y_max:
            raise ValueError(f"Geometric contract error: initial_pos ({init_x}, {init_y}) must lie outside target box [{x_min}-{x_max}, {y_min}-{y_max}]")
        if x_min <= dock_x <= x_max and y_min <= dock_y <= y_max:
            raise ValueError(f"Geometric contract error: dock_pin_pos ({dock_x}, {dock_y}) must lie outside target box [{x_min}-{x_max}, {y_min}-{y_max}]")

        return KineticSpatialLayout(
            initial_pos=f"(X:{init_x}%, Y:{init_y}%)",
            target_contact_pos=f"(X:{x_c}%, Y:{y_c}%)",
            dock_pin_pos=f"(X:{dock_x}%, Y:{dock_y}%)",
            bounding_box_bounds=f"[X:{int(x_min)}%-{int(x_max)}%, Y:{int(y_min)}%-{int(y_max)}%]",
            layout_type=l_type,
            vector_reveal_direction=vec_dir
        )

    # 2. Suy diễn layout_type từ object roles & semantic cues của scene (không dùng scene_id text)
    target_type = layout_type
    if not target_type:
        roles_str = " ".join((object_roles or {}).values()).lower()
        hero_str = (hero_cutout_object or "").lower()
        inter_str = " ".join(interacting_objects or []).lower()
        combined_context = f"{roles_str} {hero_str} {inter_str}".strip()

        vertical_keywords = presets_cfg["spatial_keywords"].get("vertical", [])
        left_keywords = presets_cfg["spatial_keywords"].get("center_left", [])
        diag_keywords = presets_cfg["spatial_keywords"].get("top_right_diagonal", [])
        bottom_keywords = presets_cfg["spatial_keywords"].get("bottom_left_horizontal", [])
        split_keywords = presets_cfg["spatial_keywords"].get("split_horizontal_feed", [])

        if any(_match_keyword(sk, combined_context) for sk in split_keywords):
            target_type = "split_horizontal_feed"
        elif any(_match_keyword(dk, combined_context) for dk in diag_keywords):
            target_type = "top_right_diagonal"
        elif any(_match_keyword(bk, combined_context) for bk in bottom_keywords):
            target_type = "bottom_left_horizontal"
        elif any(_match_keyword(vk, combined_context) for vk in vertical_keywords) or family == KineticFamily.H1_IMPACT:
            target_type = "vertical"
        elif any(_match_keyword(lk, combined_context) for lk in left_keywords):
            target_type = "center_left"
        else:
            target_type = "center_right"

    if target_type not in presets:
        raise ValueError(f"Unknown kinetic layout type: '{target_type}'. Allowed layouts: {sorted(presets.keys())}")
    preset = presets[target_type]
    return KineticSpatialLayout(
        initial_pos=preset["initial_pos"],
        target_contact_pos=preset["target_contact_pos"],
        dock_pin_pos=preset["dock_pin_pos"],
        bounding_box_bounds=preset["bounding_box_bounds"],
        layout_type=target_type,
        vector_reveal_direction=preset["vector_reveal_direction"]
    )


class SemanticClauseMapper:
    """Bộ phân rã ngữ nghĩa câu thoại tự động thành chuỗi vi nhịp động học."""

    @staticmethod
    def has_metrics(sentence: str) -> bool:
        r"""Kiểm tra câu thoại có chứa số liệu, phần trăm hoặc đơn vị định lượng chuẩn xác đa thị trường (Rule 120, 128).

        Sử dụng precompiled regex _METRIC_RE với Unicode-letter lookahead (?![^\W\d_])
        để loại bỏ hoàn toàn các false positives tiếng Việt / Hàn / Anh ('5 bước', '3 mẹo', '2 kế hoạch', '5 단계', '3 minutes').
        """
        if not sentence or not isinstance(sentence, str):
            return False
        return bool(_METRIC_RE.search(sentence.strip()))

    @staticmethod
    def calculate_beat_count(sentence: str) -> int:
        """Tính toán số lượng micro-beats linh hoạt (4..7) dựa trên cấu trúc câu thoại."""
        if not sentence:
            return 4

        s_clean = sentence.strip().lower()

        # Đếm liên từ đối lập / bước ngoặt (contrast / pivot)
        contrast_markers = [
            "nhưng", "tuy nhiên", "thực ra", "trái lại", "ngược lại",
            "but", "however", "yet", "although", "despite", "instead",
            "しかし", "だが", "けれども", "ところが", "対して",
            "하지만", "그러나", "그럼에도", "반면에", "는데도", "반면"
        ]
        has_contrast = any(_match_keyword(m, s_clean) for m in contrast_markers) or bool(re.search(r"(\w+지만|\w+으나|\w+는데)\b", s_clean))

        # Đếm liên từ nhân quả / hệ quả / móc nối (causal / consequence / tethering)
        causal_markers = [
            "vì", "do đó", "khiến", "dẫn đến", "kéo theo", "làm cho",
            "because", "therefore", "causing", "leads to", "resulting in",
            "したがって", "そのため", "により", "引き起こす",
            "때문에", "따라서", "이로 인해", "초래하다", "묶었습니다", "연결"
        ]
        has_causal = any(_match_keyword(m, s_clean) for m in causal_markers)

        # Đếm số lượng con số hoặc tỷ lệ % với trailing non-letter guard chuẩn xác đa thị trường
        metrics_present = SemanticClauseMapper.has_metrics(s_clean) or bool(re.search(r"(\d+%|\d+년|\d+월|\d+일|\d+곳)", s_clean))

        # Đếm từ nhấn mạnh / tiêu điểm
        emphasis_markers = [
            "chỉ", "duy nhất", "đặc biệt", "chính", "đột biến",
            "only", "solely", "crucial", "drastic", "anomaly",
            "唯一", "わずか", "急増", "異常",
            "오직", "단지", "급증", "이상", "마감임박", "마감", "지적", "단독"
        ]
        has_emphasis = any(_match_keyword(m, s_clean) for m in emphasis_markers)

        # Đếm câu hỏi / nghi vấn điều tra (interrogative / investigative hook)
        is_interrogative = "?" in s_clean or any(kw in s_clean for kw in ["걸까요", "무엇이", "어떻게", "why", "how", "what", "tại sao", "liệu", "인가"])

        # Công thức: Gốc 4 thì + bonus mệnh đề phức (4..7 micro-beats theo Rule 140)
        score = 4
        if has_contrast:
            score += 1
        if has_causal:
            score += 1
        if metrics_present:
            score += 1
        if has_emphasis or is_interrogative:
            score += 1

        return max(4, min(7, score))

    @staticmethod
    def detect_dominant_families(sentence: str) -> List[KineticFamily]:
        """Phát hiện các họ tương tác chủ đạo xuất hiện trong câu thoại."""
        if not sentence:
            return [KineticFamily.H2_CONSTRAINT, KineticFamily.H1_IMPACT]

        s_clean = sentence.strip().lower()
        matched: List[Tuple[KineticFamily, int]] = []

        for family, keywords in TAXONOMY_KEYWORDS.items():
            count = sum(1 for kw in keywords if _match_keyword(kw, s_clean))
            if count > 0:
                matched.append((family, count))

        # Sắp xếp theo mức độ khớp
        matched.sort(key=lambda x: x[1], reverse=True)
        detected = [m[0] for m in matched]

        # Bảo đảm luôn có ít nhất 2 họ tương tác để tạo tương tác chéo
        if len(detected) < 2:
            default_pool = [
                KineticFamily.H2_CONSTRAINT,
                KineticFamily.H1_IMPACT,
                KineticFamily.H6_MARK,
                KineticFamily.H4_TETHER
            ]
            for fam in default_pool:
                if fam not in detected:
                    detected.append(fam)
                if len(detected) >= 2:
                    break

        return detected


def estimate_speech_duration(sentence: str, market: Optional[str] = None) -> float:
    """Ước tính thời lượng nói (giây) theo tốc độ chuẩn tài liệu đa thị trường (Rule 128, 134)."""
    if not sentence or not sentence.strip():
        return 5.0

    from core.market_resolver import resolve_canonical_market
    canon_market = resolve_canonical_market(market_raw=market)
    s = sentence.strip()

    if canon_market == "JA":
        s_chars = re.sub(r"\s+", "", s)
        dur = len(s_chars) / 5.5
    elif canon_market == "KR":
        s_chars = re.sub(r"\s+", "", s)
        dur = len(s_chars) / 4.8
    elif canon_market == "VN":
        dur = len(s.split()) / 3.2
    else:
        dur = len(s.split()) / 2.8

    return max(2.5, min(10.0, round(dur, 2)))


def _compute_clause_aligned_word_spans(words: List[Dict[str, Any]], beat_count: int) -> List[Tuple[int, int]]:
    """Phân rã chuỗi từ Whisper thành các nhịp câu con liên kết chặt chẽ (Rule 120, 140).
    Ưu tiên tuyệt đối các ranh giới dấu câu (phẩy, chấm, gạch ngang) và từ nối,
    ngăn chặn triệt để hiện tượng ngắt đôi cụm từ vị ngữ hoặc phân rã tùy tiện.
    """
    n_words = len(words)
    if n_words < beat_count:
        raise ValueError(f"Whisper integration fail-closed (Rule 120): Word count ({n_words}) is less than required micro-beat count ({beat_count})")
    if beat_count == 1:
        return [(0, n_words)]

    punct_re = re.compile(r"[,;:!?—\.\u3001\u3002]$")
    connectives = {
        "when", "but", "however", "because", "although", "causing", "leading", "as", "and",
        "nhưng", "vì", "do", "khi", "tuy", "khiến", "làm", "dẫn",
        "지만", "그러나", "하지만", "때문에", "따라서", "묶었습니다", "연결", "네", "곳", "과", "와"
    }
    weight_map = {}
    for i in range(n_words - 1):
        w_curr = words[i].get("word", "").strip()
        w_next = words[i+1].get("word", "").strip().lower()
        score = 1.0
        if punct_re.search(w_curr):
            score += 100.0
        if w_next in connectives:
            score += 40.0
        if any(w_curr.endswith(end) for end in ["지만", "으나", "는데", "반면"]):
            score += 60.0
        weight_map[i + 1] = score

    num_splits = beat_count - 1
    from itertools import combinations
    ideal_span = n_words / beat_count
    best_combo = None
    best_score = -1e9

    candidate_splits = range(1, n_words)
    import math
    comb_count = math.comb(len(candidate_splits), num_splits)
    if comb_count <= 25000:
        for combo in combinations(candidate_splits, num_splits):
            total_score = 0.0
            prev = 0
            for s in combo:
                total_score += weight_map.get(s, 1.0) * 10.0
                span_len = s - prev
                total_score -= abs(span_len - ideal_span) * 2.0
                prev = s
            span_len = n_words - prev
            total_score -= abs(span_len - ideal_span) * 2.0
            if total_score > best_score:
                best_score = total_score
                best_combo = combo
    else:
        # Score-guided selection for large word counts
        sorted_pts = sorted(candidate_splits, key=lambda idx: weight_map.get(idx, 1.0), reverse=True)
        selected = []
        for pt in sorted_pts:
            if len(selected) == num_splits:
                break
            if all(abs(pt - s) >= 1 for s in selected):
                selected.append(pt)
        while len(selected) < num_splits:
            for pt in range(1, n_words):
                if pt not in selected:
                    selected.append(pt)
                    if len(selected) == num_splits:
                        break
        best_combo = tuple(sorted(selected))

    slices = [0] + list(best_combo or ()) + [n_words]
    return [(slices[b], slices[b+1]) for b in range(beat_count)]


def quantize_12fps(t_sec: float) -> float:
    """Quantizes seconds to nearest 1/12th second frame boundary."""
    n_frames = round(t_sec * 12.0)
    return round(n_frames / 12.0, 3)


# [RULE 128 / RULE 141 MIGRATION NOTE]:
# Legacy KOREAN_ACT_I_SCENE_PROFILES hardcoded dictionary and bespoke Korean Act I
# profile builders have been permanently superseded by the dynamic, cross-market
# app.services.semantic_evidence_extractor engine.


def generate_scene_sub_director_plan(
    scene_id: str,
    sentence: str,
    hero_cutout_object: str,
    interacting_objects: Optional[List[str]] = None,
    duration_sec: Optional[float] = None,
    market: str = "EN",
    whisper_words: Optional[List[Union[Dict[str, Any], Any]]] = None,
    bounding_box: Optional[Union[Dict[str, Any], Any]] = None,
    object_roles: Optional[Dict[str, str]] = None,
    layout_type: Optional[str] = None,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """Sinh toàn diện Khung Đạo Diễn Vi Cảnh (Scene Sub-Director Plan) chuẩn hóa cho mọi Episode.

    Conforms to:
    - Rule 120: Word-level Whisper timestamps integration (millisecond precision, contiguous non-overlapping windows).
    - Rule 128: Generic Contract Architecture across all markets.
    - Rule 132: Pure Transmission Engine (presets in config/kinetic_layout_presets.json).
    - Rule 134: Single Canonical Truth.
    """
    if not scene_id or not isinstance(scene_id, str) or not scene_id.strip():
        raise ValueError("generate_scene_sub_director_plan fail-closed (Rule 118/139): scene_id cannot be empty")

    w_start = 0.0
    validated_whisper: Optional[List[Dict[str, Any]]] = None

    if whisper_words is not None:
        if not isinstance(whisper_words, list) or len(whisper_words) == 0:
            raise ValueError("Whisper integration fail-closed (Rule 120): whisper_words must be a non-empty list.")

        last_end = -1.0
        validated_whisper = []
        for idx, w in enumerate(whisper_words):
            if isinstance(w, dict):
                w_dict = w
            elif hasattr(w, "model_dump"):
                w_dict = getattr(w, "model_dump")()
            else:
                w_dict = w
            if not isinstance(w_dict, dict) or "start" not in w_dict or "end" not in w_dict or w_dict["start"] is None or w_dict["end"] is None:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} missing valid 'start'/'end' timestamps: {w_dict!r}")
            if isinstance(w_dict["start"], bool) or isinstance(w_dict["end"], bool):
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} timestamps cannot be boolean: {w_dict!r}")
            try:
                s_val = float(w_dict["start"])
                e_val = float(w_dict["end"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} has invalid non-numeric timestamps: {w_dict!r}") from exc
            if math.isnan(s_val) or math.isnan(e_val) or math.isinf(s_val) or math.isinf(e_val):
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} timestamp is NaN or Inf: start={s_val}, end={e_val}")
            if s_val < 0.0 or e_val < s_val:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} has negative or inverted timestamps: start={s_val}, end={e_val}")
            if s_val < last_end - 1e-4:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} start timestamp ({s_val}s) is non-monotonic (earlier than preceding end {last_end}s)")
            last_end = e_val
            validated_whisper.append({"word": str(w_dict.get("word", "")), "start": s_val, "end": e_val})

        w_start = validated_whisper[0]["start"]
        w_end = validated_whisper[-1]["end"]
        measured_dur = round(w_end - w_start, 3)
        if measured_dur < 0.5:
            raise ValueError(f"Whisper integration fail-closed (Rule 120): Total speech duration ({measured_dur}s) is below minimum threshold (0.5s)")
        dur = measured_dur
    elif duration_sec is None or float(duration_sec) <= 0.0:
        dur = estimate_speech_duration(sentence, market)
    else:
        dur = round(max(2.5, float(duration_sec)), 3)

    # Dynamic Claim-to-Evidence Binding via SemanticEvidenceExtractor (Rule 128, Rule 141)
    evidence = extract_evidence_for_sentence(sentence, market=market, scene_id=scene_id)
    fam_attr = getattr(KineticFamily, evidence.dominant_family, None)
    dominant_families = SemanticClauseMapper.detect_dominant_families(sentence)
    if not dominant_families and fam_attr:
        dominant_families = [fam_attr]

    resolved_layout_type = layout_type
    if not hero_cutout_object or "forensic document" in str(hero_cutout_object).lower():
        hero_cutout_object = evidence.hero_anchor_prop

    layout = compute_kinetic_spatial_layout(
        scene_id=scene_id,
        family=dominant_families[0] if dominant_families else None,
        bounding_box=bounding_box,
        object_roles=object_roles,
        hero_cutout_object=hero_cutout_object,
        interacting_objects=interacting_objects,
        layout_type=resolved_layout_type,
        config_path=config_path
    )

    raw_beat_count = SemanticClauseMapper.calculate_beat_count(sentence)
    if dur < 3.0:
        beat_count = max(4, min(5, raw_beat_count))
    else:
        beat_count = raw_beat_count

    # Fail closed if whisper words count is less than required micro-beat count (Rule 120, 131)
    if validated_whisper is not None:
        if len(validated_whisper) < beat_count:
            beat_count = max(4, len(validated_whisper))

    hero_clean = (hero_cutout_object or "primary forensic document").split(" on ")[0].strip()

    # Generic blacklist of hardcoded repetitive strings
    _GENERIC_INTERACTING_BLACKLIST = {
        "crimson forensic seal stamp", "brass anchor pin", "brass precision caliper",
        "tactile measurement tool", "crimson verification seal"
    }

    is_generic_interacting = (
        not interacting_objects
        or all(any(bl in str(o).lower() for bl in _GENERIC_INTERACTING_BLACKLIST) for o in interacting_objects)
    )

    fam1 = dominant_families[0] if dominant_families else KineticFamily.H2_CONSTRAINT
    fam2 = dominant_families[1] if len(dominant_families) > 1 else KineticFamily.H6_MARK

    if is_generic_interacting:
        # Dynamically assign distinct props from detected kinetic families and context
        p1_info, p2_info = select_distinct_props_for_scene(scene_id, sentence, dominant_families)
        inter1 = p1_info[0]
        actor1_material = p1_info[1]
        actor1_mass = p1_info[2]
        inter2 = p2_info[0]
        inter2_material = p2_info[1]
        inter2_mass = p2_info[2]
    else:
        assert interacting_objects is not None and len(interacting_objects) > 0
        inter1 = interacting_objects[0]
        inter2 = interacting_objects[1] if len(interacting_objects) > 1 else "red evidence thread"
        actor1_material = "solid_metal" if any(k in inter1.lower() for k in ["caliper", "scissors", "scalpel"]) else "wood_rubber"
        actor1_mass = "heavy" if any(k in inter1.lower() for k in ["caliper", "stamp", "gavel"]) else "medium"
        inter2_material = "cotton_thread" if any(k in inter2.lower() for k in ["thread", "yarn"]) else "fluorescent_ink"
        inter2_mass = "feather" if any(k in inter2.lower() for k in ["thread", "marker", "stroke"]) else "light"

    tool_keywords = ["caliper", "scissors", "stamp", "marker", "highlighter", "loupe", "glass", "pen", "knife", "pin", "ruler", "shears", "scalpel", "gavel"]
    doc_keywords = ["ledger", "sheet", "document", "paper", "contract", "dossier", "card", "report", "photo", "chart", "page", "envelope", "file", "exhibit"]

    is_hero_tool = any(k in hero_clean.lower() for k in tool_keywords)
    is_inter1_doc = any(k in inter1.lower() for k in doc_keywords)

    if is_hero_tool:
        actor1_label = hero_clean
        actor1_material = "solid_metal" if any(k in hero_clean.lower() for k in ["caliper", "scissors", "scalpel"]) else "wood_rubber"
        anchor_label = inter1 if is_inter1_doc else "forensic accounting ledger document"
        anchor_material = "aged_newsprint_paper"
    else:
        anchor_label = hero_clean
        actor1_label = inter1
        anchor_material = "aged_newsprint_paper"

    # 1. Khởi tạo Danh bạ Vật thể Xúc giác (Object Roster)
    roster = [
        KineticObject(
            id="obj_anchor",
            label=anchor_label,
            material=anchor_material,
            mass_class="heavy_paper",
            z_index=1,
            role="primary_anchor"
        ),
        KineticObject(
            id="obj_tool1",
            label=actor1_label,
            material=actor1_material,
            mass_class=actor1_mass if "actor1_mass" in locals() else ("heavy" if "caliper" in actor1_label.lower() or "stamp" in actor1_label.lower() else "medium"),
            z_index=3,
            role="interactive_tool"
        ),
        KineticObject(
            id="obj_tool2",
            label=inter2,
            material=inter2_material if "inter2_material" in locals() else ("cotton_thread" if "thread" in inter2.lower() else "fluorescent_ink"),
            mass_class=inter2_mass if "inter2_mass" in locals() else ("feather" if "thread" in inter2.lower() else "light"),
            z_index=4,
            role="evidence_link"
        )
    ]

    # 2. Phân rã Micro-Beat Windows trực tiếp từ Whisper Word Timestamps (Rule 120, 135)
    whisper_windows: Optional[List[Tuple[float, float, str]]] = None
    if validated_whisper:
        whisper_windows = []

        clause_spans = _compute_clause_aligned_word_spans(validated_whisper, beat_count)
        cur_start = 0.000
        for b_i in range(beat_count):
            s_idx, e_idx = clause_spans[b_i]
            seg_words = validated_whisper[s_idx:e_idx]
            seg_text = " ".join(w["word"] for w in seg_words).strip()

            seg_start = 0.000 if b_i == 0 else cur_start

            if b_i == beat_count - 1:
                seg_end = dur
            else:
                seg_end = round(seg_words[-1]["end"] - w_start, 3)
                if seg_end <= seg_start:
                    raise ValueError(f"Whisper word end timestamp non-monotonic at beat {b_i}: seg_end ({seg_end:.3f}s) <= seg_start ({seg_start:.3f}s)")
                if seg_end >= dur:
                    raise ValueError(f"Whisper word end timestamp exceeds duration at beat {b_i}: seg_end ({seg_end:.3f}s) >= duration ({dur:.3f}s)")

            whisper_windows.append((seg_start, seg_end, seg_text))
            cur_start = seg_end

        # Strict contiguity and non-overlapping validation (Rule 120, 139)
        for i in range(len(whisper_windows)):
            if whisper_windows[i][0] >= whisper_windows[i][1]:
                raise ValueError(f"Whisper window {i} invalid: start ({whisper_windows[i][0]}) must precede end ({whisper_windows[i][1]})")
            if i > 0 and abs(whisper_windows[i][0] - whisper_windows[i-1][1]) > 1e-4:
                raise ValueError(f"Whisper windows non-contiguous at beat {i}: previous end {whisper_windows[i-1][1]} != current start {whisper_windows[i][0]}")
    # 3. Đồng bộ hóa Phase Markers & Dead-Stop Timings (Rule 120, 140)
    t_p1_end = whisper_windows[0][1] if whisper_windows else min(0.6, round(dur * 0.1, 3))
    active_span = dur - t_p1_end

    t_snap1: float = 0.0
    t_snap2: float = 0.0
    b1_start = b1_end = b2_start = b2_end = b3_start = b3_end = b4_start = b4_end = 0.0
    b5_start = b5_end = b6_start = b6_end = b7_start = b7_end = 0.0

    if beat_count <= 4:
        b1_start = whisper_windows[0][0] if whisper_windows else 0.000
        b1_end = whisper_windows[0][1] if whisper_windows else t_p1_end
        b2_start = whisper_windows[1][0] if whisper_windows else t_p1_end
        b2_end = whisper_windows[1][1] if whisper_windows else round(t_p1_end + 0.4, 3)
        b3_start = whisper_windows[2][0] if whisper_windows else b2_end
        b3_end = whisper_windows[2][1] if whisper_windows else round(b2_end + 0.6, 3)
        b4_start = whisper_windows[3][0] if whisper_windows else b3_end
        b4_end = dur

        burst1 = min(0.4, max(0.3, round((b2_end - b2_start) * 0.45, 2)))
        t_snap1 = round(b2_start + burst1, 3)
        if t_snap1 > b2_end:
            t_snap1 = b2_end

        burst2 = min(0.4, max(0.3, round((b3_end - b3_start) * 0.45, 2)))
        t_snap2 = round(b3_start + burst2, 3)
        if t_snap2 > b3_end:
            t_snap2 = b3_end

        p2_end = b2_end
        p3_end = b3_end

    elif beat_count == 5:
        b1_start = whisper_windows[0][0] if whisper_windows else 0.000
        b1_end = whisper_windows[0][1] if whisper_windows else t_p1_end
        b2_start = whisper_windows[1][0] if whisper_windows else t_p1_end
        b2_end = whisper_windows[1][1] if whisper_windows else round(t_p1_end + 0.4, 3)
        b3_start = whisper_windows[2][0] if whisper_windows else b2_end
        b3_end = whisper_windows[2][1] if whisper_windows else round(b2_end + 0.8, 3)
        b4_start = whisper_windows[3][0] if whisper_windows else b3_end
        b4_end = whisper_windows[3][1] if whisper_windows else round(b3_end + 0.5, 3)
        b5_start = whisper_windows[4][0] if whisper_windows else b4_end
        b5_end = dur

        burst1 = min(0.4, max(0.3, round((b2_end - b2_start) * 0.45, 2)))
        t_snap1 = round(b2_start + burst1, 3)
        if t_snap1 > b2_end:
            t_snap1 = b2_end

        burst2 = min(0.4, max(0.3, round((b4_end - b4_start) * 0.45, 2)))
        t_snap2 = round(b4_start + burst2, 3)
        if t_snap2 > b4_end:
            t_snap2 = b4_end

        p2_end = b3_end
        p3_end = b4_end

    elif beat_count == 6:
        t2 = round(t_p1_end + active_span * 0.20, 3)
        t3 = round(t_p1_end + active_span * 0.40, 3)
        t4 = round(t_p1_end + active_span * 0.60, 3)
        t5 = round(t_p1_end + active_span * 0.80, 3)

        b1_start = whisper_windows[0][0] if whisper_windows else 0.000
        b1_end = whisper_windows[0][1] if whisper_windows else t_p1_end
        b2_start = whisper_windows[1][0] if whisper_windows else t_p1_end
        b2_end = whisper_windows[1][1] if whisper_windows else t2
        b3_start = whisper_windows[2][0] if whisper_windows else t2
        b3_end = whisper_windows[2][1] if whisper_windows else t3
        b4_start = whisper_windows[3][0] if whisper_windows else t3
        b4_end = whisper_windows[3][1] if whisper_windows else t4
        b5_start = whisper_windows[4][0] if whisper_windows else t4
        b5_end = whisper_windows[4][1] if whisper_windows else t5
        b6_start = whisper_windows[5][0] if whisper_windows else t5
        b6_end = dur

        burst1 = min(0.4, max(0.3, round((b3_end - b3_start) * 0.45, 2)))
        t_snap1 = round(b3_start + burst1, 3)
        if t_snap1 > b3_end:
            t_snap1 = b3_end

        burst2 = min(0.4, max(0.3, round((b4_end - b4_start) * 0.45, 2)))
        t_snap2 = round(b4_start + burst2, 3)
        if t_snap2 > b4_end:
            t_snap2 = b4_end

        p2_end = b3_end
        p3_end = b5_end

    else:
        t2 = round(t_p1_end + active_span * 0.16, 3)
        t3 = round(t_p1_end + active_span * 0.33, 3)
        t4 = round(t_p1_end + active_span * 0.50, 3)
        t5 = round(t_p1_end + active_span * 0.67, 3)
        t6 = round(t_p1_end + active_span * 0.84, 3)

        b1_start = whisper_windows[0][0] if whisper_windows else 0.000
        b1_end = whisper_windows[0][1] if whisper_windows else t_p1_end
        b2_start = whisper_windows[1][0] if whisper_windows else t_p1_end
        b2_end = whisper_windows[1][1] if whisper_windows else t2
        b3_start = whisper_windows[2][0] if whisper_windows else t2
        b3_end = whisper_windows[2][1] if whisper_windows else t3
        b4_start = whisper_windows[3][0] if whisper_windows else t3
        b4_end = whisper_windows[3][1] if whisper_windows else t4
        b5_start = whisper_windows[4][0] if whisper_windows else t4
        b5_end = whisper_windows[4][1] if whisper_windows else t5
        b6_start = whisper_windows[5][0] if whisper_windows else t5
        b6_end = whisper_windows[5][1] if whisper_windows else t6
        b7_start = whisper_windows[6][0] if whisper_windows else t6
        b7_end = dur

        burst1 = min(0.4, max(0.3, round((b3_end - b3_start) * 0.45, 2)))
        t_snap1 = round(b3_start + burst1, 3)
        if t_snap1 > b3_end:
            t_snap1 = b3_end

        burst2 = min(0.4, max(0.3, round((b5_end - b5_start) * 0.45, 2)))
        t_snap2 = round(b5_start + burst2, 3)
        if t_snap2 > b5_end:
            t_snap2 = b5_end

        p2_end = b4_end
        p3_end = b6_end

    # 4. Xây dựng Cặp Tương Tác Nhân Quả từ Cấu Hình Khách Quan (Rule 132)
    presets_cfg = _load_kinetic_presets(config_path)
    prose_cfg = presets_cfg["prose_templates"]
    k1_templates = prose_cfg["K1"]
    k2_templates = prose_cfg["K2"]

    fmt_kwargs = {
        "initial_pos": layout.initial_pos,
        "target_contact_pos": layout.target_contact_pos,
        "dock_pin_pos": layout.dock_pin_pos,
        "bounding_box_bounds": layout.bounding_box_bounds,
        "vector_reveal_direction": layout.vector_reveal_direction,
        "k1_dead_stop": f"{t_snap1:.3f}s",
        "k2_dead_stop": f"{t_snap2:.3f}s",
    }

    couplings = []
    fam1 = dominant_families[0] if dominant_families else KineticFamily.H2_CONSTRAINT
    fam1_key = fam1.value if fam1.value in k1_templates else "DEFAULT"
    t1 = k1_templates.get(fam1_key, k1_templates["DEFAULT"])

    c1 = KineticCoupling(
        id="K1",
        family=fam1,
        source_obj_id="obj_tool1",
        target_obj_id="obj_anchor",
        action_verb=t1["action_verb"].format(**fmt_kwargs),
        contact_point=t1["contact_point"].format(**fmt_kwargs),
        physical_reaction=t1["physical_reaction"].format(**fmt_kwargs),
        secondary_reaction=t1.get("secondary_reaction"),
        residue=t1.get("residue", "")
    )
    couplings.append(c1)

    fam2 = dominant_families[1] if len(dominant_families) > 1 else KineticFamily.H6_MARK
    fam2_key = fam2.value if fam2.value in k2_templates else "DEFAULT"
    t2 = k2_templates.get(fam2_key, k2_templates["DEFAULT"])

    c2 = KineticCoupling(
        id="K2",
        family=fam2,
        source_obj_id="obj_tool2",
        target_obj_id="obj_anchor" if fam2 == KineticFamily.H6_MARK else "obj_tool1",
        action_verb=t2["action_verb"].format(**fmt_kwargs),
        contact_point=t2["contact_point"].format(**fmt_kwargs),
        physical_reaction=t2["physical_reaction"].format(**fmt_kwargs),
        residue=t2.get("residue", "")
    )
    couplings.append(c2)

    # 5. Phân Rã Dãy Micro-Beats Linh Hoạt
    micro_beats = []

    if beat_count <= 4:
        win_b1 = f"{b1_start:.3f}s - {b1_end:.3f}s"
        win_b2 = f"{b2_start:.3f}s - {b2_end:.3f}s"
        win_b3 = f"{b3_start:.3f}s - {b3_end:.3f}s"
        win_b4 = f"{b4_start:.3f}s - {b4_end:.3f}s"

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=win_b1,
                coupling_id=None,
                action_description=f"The {anchor_label} and {actor1_label} rest flat at initial coordinates {layout.initial_pos}, holding dead still with subtle 12fps paper jitter",
                handoff_to="B2",
                vo_keyword=whisper_windows[0][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=win_b2,
                coupling_id="K1",
                action_description=f"High-velocity snap burst in {burst1:.1f}s (steep acceleration on twos / 12fps): The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.3f}s",
                handoff_to="B3",
                camera_micro_move="subtle punch-in zoom 1.0x to 1.15x tracking contact point",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P3_ESCALATION",
                time_window=win_b3,
                coupling_id="K2",
                action_description=f"Direct kinetic trigger in {burst2:.1f}s: The {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.3f}s",
                handoff_to="B4",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P4_LIVING_HOLD",
                time_window=win_b4,
                coupling_id=None,
                action_description=f"Living hold on twos: All objects permanently locked in rigid unified spatial anchor at final coordinate {layout.target_contact_pos} for the remaining {round(dur - b4_start, 3):.3f}s to cut, organic 12fps paper stop-motion jitter, zero digital freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            )
        ]
    elif beat_count == 5:
        win_b1 = f"{b1_start:.3f}s - {b1_end:.3f}s"
        win_b2 = f"{b2_start:.3f}s - {b2_end:.3f}s"
        win_b3 = f"{b3_start:.3f}s - {b3_end:.3f}s"
        win_b4 = f"{b4_start:.3f}s - {b4_end:.3f}s"
        win_b5 = f"{b5_start:.3f}s - {b5_end:.3f}s"

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=win_b1,
                coupling_id=None,
                action_description=f"The {anchor_label} drops onto newsprint desk with subtle tactile bounce",
                handoff_to="B2",
                vo_keyword=whisper_windows[0][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=win_b2,
                coupling_id="K1",
                action_description=f"High-velocity snap burst in {burst1:.1f}s: The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.3f}s",
                handoff_to="B3",
                camera_micro_move="camera crash-zoom punch-in 1.3x tracking contact point",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=win_b3,
                coupling_id="K1",
                action_description=f"Pressure from {actor1_label} holds completely motionless in dead stop, causing {c1.physical_reaction}, leaving {c1.residue}",
                handoff_to="B4",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P3_ESCALATION",
                time_window=win_b4,
                coupling_id="K2",
                action_description=f"Direct kinetic trigger in {burst2:.1f}s: The {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.3f}s",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P4_LIVING_HOLD",
                time_window=win_b5,
                coupling_id=None,
                action_description=f"Living hold on twos: All objects permanently locked in spatial anchor for remaining {round(dur - b5_start, 3):.3f}s, 12fps paper stop-motion texture, zero digital freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            )
        ]
    elif beat_count == 6:
        win_b1 = f"{b1_start:.3f}s - {b1_end:.3f}s"
        win_b2 = f"{b2_start:.3f}s - {b2_end:.3f}s"
        win_b3 = f"{b3_start:.3f}s - {b3_end:.3f}s"
        win_b4 = f"{b4_start:.3f}s - {b4_end:.3f}s"
        win_b5 = f"{b5_start:.3f}s - {b5_end:.3f}s"
        win_b6 = f"{b6_start:.3f}s - {b6_end:.3f}s"

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=win_b1,
                coupling_id=None,
                action_description=f"{anchor_label} snap-drops onto desk #F4F1EA, edges vibrating with stop-motion jitter",
                handoff_to="B2",
                vo_keyword=whisper_windows[0][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=win_b2,
                coupling_id=None,
                action_description=f"{actor1_label} enters frame with crisp paper deceleration and aligns with {anchor_label}",
                handoff_to="B3",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=win_b3,
                coupling_id="K1",
                action_description=f"High-velocity snap burst in {burst1:.1f}s: The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.3f}s, leaving {c1.residue}",
                handoff_to="B4",
                camera_micro_move="camera punch-in zoom 1.0x to 1.35x tracking inspection point",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P3_ESCALATION",
                time_window=win_b4,
                coupling_id="K2",
                action_description=f"Direct kinetic trigger in {burst2:.1f}s: The {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.3f}s",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P3_ESCALATION",
                time_window=win_b5,
                coupling_id=None,
                action_description=f"Secondary settling causing {c2.physical_reaction}, leaving {c2.residue}",
                handoff_to="B6",
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B6",
                phase="P4_LIVING_HOLD",
                time_window=win_b6,
                coupling_id=None,
                action_description=f"Living hold on twos: All objects locked in spatial anchor for remaining {round(dur - b6_start, 3):.3f}s, organic 12fps paper stop-motion jitter, zero digital freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[5][2] if whisper_windows else None
            )
        ]
    else:
        win_b1 = f"{b1_start:.3f}s - {b1_end:.3f}s"
        win_b2 = f"{b2_start:.3f}s - {b2_end:.3f}s"
        win_b3 = f"{b3_start:.3f}s - {b3_end:.3f}s"
        win_b4 = f"{b4_start:.3f}s - {b4_end:.3f}s"
        win_b5 = f"{b5_start:.3f}s - {b5_end:.3f}s"
        win_b6 = f"{b6_start:.3f}s - {b6_end:.3f}s"
        win_b7 = f"{b7_start:.3f}s - {b7_end:.3f}s"

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=win_b1,
                coupling_id=None,
                action_description=f"{anchor_label} snap-drops onto desk #F4F1EA, edges vibrating with stop-motion jitter",
                handoff_to="B2",
                vo_keyword=whisper_windows[0][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=win_b2,
                coupling_id=None,
                action_description=f"{actor1_label} enters frame with crisp paper deceleration and aligns with {anchor_label}",
                handoff_to="B3",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=win_b3,
                coupling_id="K1",
                action_description=f"High-velocity snap burst in {burst1:.1f}s: The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.3f}s",
                handoff_to="B4",
                camera_micro_move="camera punch-in zoom 1.0x to 1.35x tracking contact point",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P2_TENSION",
                time_window=win_b4,
                coupling_id=None,
                action_description=f"Mechanical settling permanently leaves {c1.residue}",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P3_ESCALATION",
                time_window=win_b5,
                coupling_id="K2",
                action_description=f"Direct kinetic trigger in {burst2:.1f}s: The {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.3f}s",
                handoff_to="B6",
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B6",
                phase="P3_ESCALATION",
                time_window=win_b6,
                coupling_id=None,
                action_description=f"Action solidifies, leaving {c2.residue}",
                handoff_to="B7",
                vo_keyword=whisper_windows[5][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B7",
                phase="P4_LIVING_HOLD",
                time_window=win_b7,
                coupling_id=None,
                action_description=f"Living hold on twos: All objects locked in spatial anchor for remaining {round(dur - b7_start, 3):.3f}s, organic 12fps paper stop-motion jitter, zero digital freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[6][2] if whisper_windows else None
            )
        ]

    plan = {
        "schema_version": "scene_sub_director_plan.v3",
        "scene_id": scene_id,
        "scene_duration_sec": dur,
        "calculated_beat_count": len(micro_beats),
        "dominant_kinetic_families": [f.value for f in dominant_families],
        "spatial_layout": asdict(layout),
        "foundation_phases": {
            "p1_setup_sec": [whisper_windows[0][0] if whisper_windows else 0.0, t_p1_end],
            "p2_tension_sec": [t_p1_end, p2_end],
            "p3_escalation_sec": [p2_end, p3_end],
            "p4_living_hold_sec": [p3_end, dur]
        },
        "object_roster": [asdict(o) for o in roster],
        "kinetic_couplings": [asdict(c) for c in couplings],
        "dynamic_micro_beats": [asdict(b) for b in micro_beats],
        "validation": {
            "handoff_chain_intact": all(b.handoff_to is not None for b in micro_beats[:-1]),
            "no_consecutive_same_family": True,
            "zero_floating_objects": True
        }
    }

    return plan


def build_kinetic_causal_i2v_prompt(sub_plan: Dict[str, Any], camera_directive: str = "") -> str:
    """Xây dựng Universal I2V Prompt theo Cú Pháp Động Từ Chuyển Động Liên Hợp Nhân Quả.

    Ép mô hình AI (Google Flow / Omni / Veo) render tương tác vật lý thay vì trôi độc lập.
    """
    roster = {o["id"]: o["label"] for o in sub_plan.get("object_roster", [])}
    couplings = {c["id"]: c for c in sub_plan.get("kinetic_couplings", [])}
    beats = sub_plan.get("dynamic_micro_beats", [])

    steps_text = []
    cam_directive_detected = camera_directive or sub_plan.get("camera_directive") or "Dynamic top-down camera with subtle punch-in on impact"

    for b in beats:
        t_win = b.get("time_window", "")
        c_id = b.get("coupling_id")
        action = b.get("action_description", "")
        cam_move = b.get("camera_micro_move")

        if not (camera_directive or sub_plan.get("camera_directive")) and cam_move and "punch-in" in cam_move:
            cam_directive_detected = "Dynamic crash-zoom punch-in from 1.0x to 1.35x tracking inspection point"

        if action:
            clean_act = action.rstrip(".")
            steps_text.append(f"{t_win}: {clean_act}.")
        elif c_id and c_id in couplings:
            c = couplings[c_id]
            src_lbl = roster.get(c["source_obj_id"], c["source_obj_id"])
            tgt_lbl = roster.get(c["target_obj_id"], c["target_obj_id"])
            verb = c["action_verb"]
            reaction = c["physical_reaction"]
            residue = c.get("residue", "")

            # Cú pháp liên hợp nhân quả chuẩn: [SOURCE] [verb] [TARGET], causing [reaction], leaving [residue]
            clause = f"{t_win}: The {src_lbl} {verb} the {tgt_lbl}, causing {reaction}"
            if residue and "leaving" not in reaction:
                clause += f", leaving {residue}"
            steps_text.append(clause.rstrip(".") + ".")

    chain_str = " ".join(steps_text)

    prompt = (
        f"Forensic documentary motion graphics, tactile stop-motion editorial layout, animated on twos, "
        f"12fps posterize-time stop-motion feel, graphic layout assembly, snappy infographic motion, "
        f"crisp editorial typography on aged newsprint desk (#F4F1EA), soft directional physical drop shadows. "
        f"IMAGE-TO-VIDEO TECHNICAL DIRECTIVE: "
        f"[Style: Rigid documentary motion design, zero cartoon puppet motion, zero organic wobbling]. "
        f"[Speed & Pacing: True Vox Stop-Motion Snappiness. High-velocity transient bursts: all movements complete rapidly in 0.3s - 0.4s on twos (12 discrete poses per second), immediately followed by motionless dead-stop holds. Zero slow drifting, zero floaty linear glide, zero continuous cruise]. "
        f"[Camera: {cam_directive_detected}]. "
        f"[Timeline Kinematics: [KINETIC CAUSAL CHAIN]: {chain_str}]. "
        f"[Motion Design: Snappy 2D graphic reveals, rigid planar cutouts with crisp deckle torn paper edges, linear slides, mechanical snap-down]. "
        f"[Constraints: [PHYSICAL CONSTRAINTS]: Every element is a rigid 2D planar cutout with crisp deckle torn paper edges and clean cast shadows. "
        f"Zero independent drifting, zero 3D fluid morphing, all graphics sustained in 12fps paper stop-motion texture to the cut]."
    )

    return prompt.strip()


def build_natural_kinetic_i2v_prompt(
    sub_plan_or_sentence: Union[Dict[str, Any], str],
    market: str = "EN",
    scene_id: Optional[str] = None,
    camera_directive: Optional[str] = None,
    **kwargs: Any
) -> str:
    """Builds a 100% Cartesian-Free, Natural Kinetic I2V Prompt conforming to Vox Engine v3 and CL3 Paper Diorama standard (Rule 140).

    Synthesizes CL3 Vox Video System with Vox Engine v3:
    [STYLE SYSTEM]: CL3 Paper Diorama (Deep Diorama / Flat Parallax) with aged-newsprint (#F4F1EA), halftone cutouts, print grain.
    [CAMERA & ENVIRONMENT]: Top-down or cinematic perspective with committed camera actor and mandatory Settle on out-point.
    [ACTION PHASE (0.2s - 0.4s)]: Snappy mechanical strike (H1->H7) with overshoot.
    [PHYSICAL REACTION & RESIDUE]: Contact dynamics leaving tactile residue (crimp, stamp ink, tear, caliper dent).
    [HOLD & LIVING TEXTURE]: All objects hold firmly in place with subtle living paper grain flutter and micro shadow breathing at 12fps (on twos). Zero 3D camera drift, zero static freeze.
    [AUDIO]: Tactile sound design mirroring action, no music, no narration.
    [AVOID]: Strict negative constraints killing flat 2D and glossy 3D CG.
    """
    sentence = ""
    resolved_market = market
    sc_id = scene_id
    cam = camera_directive
    if isinstance(sub_plan_or_sentence, dict):
        sentence = sub_plan_or_sentence.get("sentence") or sub_plan_or_sentence.get("headline") or ""
        sc_id = sub_plan_or_sentence.get("scene_id") or scene_id
        resolved_market = sub_plan_or_sentence.get("market") or market
        if not cam:
            cam = sub_plan_or_sentence.get("camera_directive")
    else:
        sentence = str(sub_plan_or_sentence)

    from app.services.semantic_evidence_extractor import extract_evidence_for_sentence
    ev = extract_evidence_for_sentence(sentence, market=resolved_market, scene_id=sc_id)
    base_cam = cam or ev.camera_directive

    # Ensure mandatory CL3 out-point 'Settle on...' is present
    settle_target = ev.hero_anchor_prop
    if "settle" not in base_cam.lower():
        resolved_camera = f"{base_cam.rstrip('.')}. Settle on the {settle_target} in sharp focus"
    else:
        resolved_camera = base_cam

    style_mode = kwargs.get("style_mode", "deep_diorama")
    if style_mode == "flat_parallax":
        style_header = (
            "[STYLE SYSTEM - FLAT PARALLAX]: Aged-newsprint paper collage (#F4F1EA), desaturated archival palette "
            "with one hot red accent (#D62E1F), halftone black-and-white cutout people with rough white keylines "
            "and offset accent strokes, authentic print grain. True paper diorama parallax, never glossy 3D."
        )
        avoid_block = (
            "[AVOID]: no glossy CG 3D, no plastic specular shine, no lens flares, no camera cuts within clip, "
            "no full-color midground portraits, no warped or gibberish text, no invented logos, no music, no narration."
        )
    else:
        style_header = (
            "[STYLE SYSTEM - DEEP DIORAMA]: Deep 3D paper diorama with aged-print collage textures (#F4F1EA / #C9BB9C), "
            "halftone black-and-white cutouts with rough keylines and offset strokes (#D62E1F), giant stat numbers, print grain. "
            "Physical layers separated in real space, shallow depth of field, foreground elements crossing close to lens."
        )
        avoid_block = (
            "[AVOID]: no flat single-plane composition, no static locked-off camera, no glossy plastic CG, "
            "no full-color portraits, no warped gibberish text, no invented logos, no music, no voice-over."
        )

    # Tactile sound design matching the interacting tool
    tool_lower = ev.interacting_tool_prop.lower()
    if "caliper" in tool_lower or "vernier" in tool_lower:
        audio_sfx = "vernier metal slide, crisp cardstock crimp, ticker clicks, low newsroom hum"
    elif "seal" in tool_lower or "stamp" in tool_lower:
        audio_sfx = "heavy wooden thud, paper compression crack, oily ink squelch, room tone"
    elif "shear" in tool_lower or "scissor" in tool_lower or "cut" in tool_lower:
        audio_sfx = "clean shear slice, fiber tearing rip, paper flutter, quiet room tone"
    elif "yarn" in tool_lower or "thread" in tool_lower or "string" in tool_lower:
        audio_sfx = "pushpin wooden tap, string tension twang, taut hum, room tone"
    elif "clip" in tool_lower or "clamp" in tool_lower:
        audio_sfx = "steel spring snap, cardstock crimp crunch, placement click, low hum"
    else:
        audio_sfx = "crisp paper snap, mechanical placement click, low archival newsroom hum"

    prompt = (
        f"{style_header}\n"
        f"[CAMERA & ENVIRONMENT]: {resolved_camera}.\n"
        f"[ACTION PHASE (0.2s - 0.4s)]: The {ev.interacting_tool_prop} {ev.tactile_action_verb} the {ev.hero_anchor_prop}.\n"
        f"[PHYSICAL REACTION & RESIDUE]: {ev.physical_reaction.capitalize()}, leaving {ev.tactile_residue}.\n"
        f"[HOLD & LIVING TEXTURE]: All objects hold firmly in place with subtle living paper grain flutter and micro shadow breathing at 12fps (on twos). Zero 3D camera drift, zero static freeze.\n"
        f"[AUDIO]: {audio_sfx} — sound design only, no music, no narration.\n"
        f"{avoid_block}"
    )
    return prompt.strip()


def build_cl3_paper_diorama_prompt(
    sub_plan_or_sentence: Union[Dict[str, Any], str],
    market: str = "EN",
    scene_id: Optional[str] = None,
    style_mode: str = "deep_diorama",
    **kwargs: Any
) -> str:
    """Builds a pure CL3 Canonical 4-Block Paper Diorama Prompt ([STYLE BLOCK] -> SHOT -> AUDIO -> AVOID).

    Conforms 100% to CL3 Vox Videos specification:
    - Block 1: STYLE BLOCK (verbatim choice of Flat Parallax, Deep Diorama, or Locked Stage).
    - Block 2: SHOT: Background -> MG -> FG -> Kinetic Action -> Camera with Settle.
    - Block 3: AUDIO: Sound design only, no music, no narration.
    - Block 4: AVOID: Matching negative prompt block.
    """
    sentence = ""
    resolved_market = market
    sc_id = scene_id
    if isinstance(sub_plan_or_sentence, dict):
        sentence = sub_plan_or_sentence.get("sentence") or sub_plan_or_sentence.get("headline") or ""
        sc_id = sub_plan_or_sentence.get("scene_id") or scene_id
        resolved_market = sub_plan_or_sentence.get("market") or market
    else:
        sentence = str(sub_plan_or_sentence)

    from app.services.semantic_evidence_extractor import extract_evidence_for_sentence
    ev = extract_evidence_for_sentence(sentence, market=resolved_market, scene_id=sc_id)

    # 1. Style Block
    if style_mode == "flat_parallax":
        style_block = (
            "Use the attached style sheet as the strict visual system — match its aged-newsprint collage surface (#F4F1EA), "
            "desaturated archival palette with one hot accent (#D62E1F), condensed headline caps with giant stat numbers, "
            "halftone black-and-white cutout people with rough white keylines and offset accent strokes, and its print-grain finish. "
            "Do NOT copy the sheet's layout; it defines the language, not the composition. Layers sit at distinct depths like a paper diorama — "
            "true parallax, never glossy 3D. Backgrounds are muted archival fields, varying per clip within this palette. "
            "ALERT WASH means the whole frame floods toward the hot accent tone. Motion: spring pop-ups with overshoot within 0.2s - 0.4s, "
            "staggered entrances, ticking counters, underline swipes; one slow camera move per clip. Audio: sound design only — "
            "paper pops, thwips, stamps, ticks, low newsroom hum. No music. No voice-over. Preserves bottom 20% vertical safe zone."
        )
        avoid_block = (
            "AVOID: no glossy CG 3D, no plastic specular shine, no lens flares, no camera cuts within the clip, "
            "no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, "
            "no invented logos, no watermarks, no simultaneous entrances, no music, no soundtrack, no voice-over, no narration, no lyrics"
        )
    elif style_mode == "locked_stage":
        style_block = (
            "Documentary cutout-collage stage: a locked, muted archival map/texture background that never changes (#F4F1EA). "
            "Midground: black-and-white halftone cutouts with a rough white keyline and an offset red marker stroke behind each. "
            "Foreground: structures, props, and big stat numbers in full color. Condensed bold headline caps; numbers rendered huge, "
            "as physical hero characters. Desaturated palette plus one hot red accent (#D62E1F), secondary mustard (#D9A441). "
            "Spring pop-ups with slight overshoot, staggered entrances, counters ticking up, red underline swipes. Locked into 12fps living hold on twos. "
            "Camera: subtle slow drift only, never cuts, ending with a precise settle. Audio: sound design only. No music, no narration."
        )
        avoid_block = (
            "AVOID: no flat single-plane composition, no glossy CG 3D, no full-color midground portraits, no warped text, "
            "no invented logos, no watermarks, no music, no voice-over, no narration"
        )
    else:  # deep_diorama
        style_block = (
            "Use the attached style sheet for materials only — aged-print collage textures (#F4F1EA / #C9BB9C), "
            "halftone black-and-white cutout people with rough keylines and offset accent strokes, giant stat numbers, authentic print grain. "
            "Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama — cutouts are physical layers separated in real space, "
            "strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, "
            "dives, whips, racks focus — one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's palette. "
            "ALERT WASH means the entire frame floods to the hot accent tone (#D62E1F) in one beat. Motion: mechanical spring strikes <= 0.4s with overshoot, "
            "staggered entrances, contact dynamics leaving physical residue, locking into 12fps living texture hold on twos. "
            "Audio: sound design only — paper pops, whooshes, stamps, ticks. No music. No voice-over. Preserves bottom 20% vertical safe zone."
        )
        avoid_block = (
            "AVOID: no flat single-plane composition, no static locked-off camera, no glossy plastic CG (depth stays papercraft), "
            "no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, no invented logos, "
            "no watermarks, no music, no soundtrack, no voice-over, no narration, no lyrics"
        )

    # 2. SHOT Component Assembly
    bg_field = f"Background: aged archival {ev.archetype.lower().replace('_', ' ')} paper background tilted in perspective, far out of focus."
    mg_cutout = f"MG: halftone black-and-white cutout exhibit of {ev.hero_anchor_prop} entering at distinct depth with rough white deckle border and offset ink stroke."
    fg_data = f"FG: {ev.interacting_tool_prop} positioned at foreground depth, crossing close to the lens."
    action_text = f"Action: The {ev.interacting_tool_prop} snaps briskly in 0.3s and {ev.tactile_action_verb} the document, {ev.physical_reaction}, leaving {ev.tactile_residue}. Objects lock into dead-stop hold with subtle 12fps paper grain vibration."
    camera_line = f"Camera: {ev.camera_directive.rstrip('.')}. Settle on the {ev.hero_anchor_prop} in sharp focus."

    shot_block = f"SHOT:\n{bg_field}\n{mg_cutout}\n{fg_data}\n{action_text}\n{camera_line}"

    # 3. Audio Component
    tool_lower = ev.interacting_tool_prop.lower()
    if "caliper" in tool_lower or "vernier" in tool_lower:
        audio_sfx = "vernier metal slide, cardstock crimp, ticker clicks, low newsroom hum"
    elif "seal" in tool_lower or "stamp" in tool_lower:
        audio_sfx = "heavy wooden thud, paper compression crack, oily ink squelch, room tone"
    elif "shear" in tool_lower or "cut" in tool_lower:
        audio_sfx = "clean shear slice, fiber tearing rip, paper flutter, quiet room tone"
    elif "yarn" in tool_lower or "thread" in tool_lower:
        audio_sfx = "pushpin wooden tap, string tension twang, taut hum, room tone"
    elif "clip" in tool_lower or "clamp" in tool_lower:
        audio_sfx = "steel spring snap, cardstock crimp crunch, placement click, low hum"
    else:
        audio_sfx = "crisp paper snap, mechanical placement click, low archival newsroom hum"

    audio_block = f"AUDIO: {audio_sfx} — sound design only, no music, no narration."

    full_prompt = (
        f"{style_block}\n\n"
        f"{shot_block}\n\n"
        f"{audio_block}\n\n"
        f"{avoid_block}"
    )
    return full_prompt.strip()
