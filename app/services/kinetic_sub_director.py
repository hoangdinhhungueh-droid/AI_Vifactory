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
_METRIC_PREFIX_CURRENCY = r"[$€£¥₫]\s*\d+(?:[,\.]\d+)?"
_METRIC_UNITS = (
    r"(?:%|円|원|[$€£¥₫]|"
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
        "chi", "phê duyệt", "ký", "xác nhận", "dập", "đóng dấu", "áp đặt", "kết luận",
        # EN
        "spend", "approve", "sign", "confirm", "stamp", "slam", "impose", "conclude", "strike",
        # JA
        "支出", "承認", "署名", "確認", "押印", "結論", "打撃", "確定",
        # KR
        "지출", "승인", "서명", "확인", "도장", "결론", "타격", "확정"
    ],
    KineticFamily.H2_CONSTRAINT: [
        # VN
        "đo", "kẹp", "so sánh", "tăng", "giảm", "tỷ lệ", "phần trăm", "thước", "chuẩn mực",
        # EN
        "measure", "clamp", "compare", "rate", "percent", "gauge", "baseline", "benchmark", "ratio",
        # JA
        "計測", "クランプ", "比較", "比率", "パーセント", "基準", "ベースライン", "尺度",
        # KR
        "측정", "고정", "비교", "비율", "퍼센트", "기준", "베이스라인", "척도"
    ],
    KineticFamily.H3_SEVER: [
        # VN
        "cắt", "xé", "chia cắt", "loại bỏ", "tách rời", "phá vỡ", "rạch", "bãi bỏ", "giảm",
        # EN
        "cut", "tear", "sever", "split", "remove", "separate", "slice", "perforate", "reduce",
        # JA
        "切断", "破断", "分割", "分離", "撤廃", "切り離す", "削除", "スライス", "削減",
        # KR
        "절단", "분리", "분할", "철폐", "가르다", "삭제", "찢다", "제거", "삭감"
    ],
    KineticFamily.H4_TETHER: [
        # VN
        "nối", "liên kết", "ghim", "dây", "ràng buộc", "kết nối", "móc nối", "mạng lưới",
        # EN
        "connect", "link", "pin", "tether", "bind", "network", "attach",
        # JA
        "連結", "接続", "ピン", "束縛", "糸", "ネットワーク", "結びつける", "固定",
        # KR
        "연결", "접속", "핀", "결속", "실", "네트워크", "묶다", "고정"
    ],
KineticFamily.H5_OPTICAL: [
        # VN
        "phát hiện", "tìm kiếm", "che giấu", "lộ", "ẩn", "soi", "phơi bày", "điều tra",
        # EN
        "discover", "reveal", "hide", "hidden", "investigate", "search", "expose", "inspect", "loupe",
        # JA
        "発見", "調査", "隠蔽", "暴露", "暴く", "拡大", "検察", "ルーペ",
        # KR
        "발견", "조사", "은폐", "폭로", "드러나다", "확대", "검증", "돋보기"
    ],
    KineticFamily.H6_MARK: [
        # VN
        "chỉ", "duy nhất", "nhấn mạnh", "cảnh báo", "đặc biệt", "bôi đậm", "điểm nóng",
        # EN
        "only", "highlight", "alert", "crucial", "warning", "solely", "hotspot", "neon",
        # JA
        "唯一", "警告", "強調", "ハイライト", "注目", "警戒", "ネオン",
        # KR
        "유일", "경고", "강조", "하이라이트", "주목", "비상", "네온"
    ],
    KineticFamily.H7_DISPLACE: [
        # VN
        "dẫn đến", "sụp đổ", "đẩy", "lan ra", "kéo theo", "mở ra", "bung", "lật",
        # EN
        "lead to", "trigger", "collapse", "push", "spread", "fan out", "unfold", "topple",
        # JA
        "誘発", "崩壊", "推進", "拡散", "展開", "連鎖倒壊", "広がる",
        # KR
        "유발", "붕괴", "밀어내다", "확산", "펼치다", "도미노", "퍼지다"
    ],
}


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


@lru_cache(maxsize=4)
def _load_kinetic_presets(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Nạp và kiểm định nghiêm ngặt layout presets và prose templates từ config/kinetic_layout_presets.json (Rule 132, 134).

    Fail-closed (Rule 118, 125, 134, 139):
    - File không tồn tại -> raise FileNotFoundError.
    - File JSON lỗi cú pháp hoặc thiếu keys bắt buộc -> raise ValueError.
    - Tuyệt đối cấm fallback open dạng hardcoded dict.
    """
    if config_path is not None:
        cfg_path = Path(config_path)
    else:
        cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "kinetic_layout_presets.json"

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

    import copy
    return copy.deepcopy(data)


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
        if hasattr(bounding_box, "model_dump"):
            b_dict = bounding_box.model_dump()
        elif isinstance(bounding_box, dict):
            b_dict = bounding_box
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

        vertical_keywords = presets_cfg["spatial_keywords"]["vertical"]
        left_keywords = presets_cfg["spatial_keywords"]["center_left"]

        if any(_match_keyword(vk, combined_context) for vk in vertical_keywords) or family == KineticFamily.H1_IMPACT:
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
            "하지만", "그러나", "그럼에도", "반면에"
        ]
        has_contrast = any(_match_keyword(m, s_clean) for m in contrast_markers)

        # Đếm liên từ nhân quả / hệ quả (causal / consequence)
        causal_markers = [
            "vì", "do đó", "khiến", "dẫn đến", "kéo theo", "làm cho",
            "because", "therefore", "causing", "leads to", "resulting in",
            "したがって", "そのため", "により", "引き起こす",
            "때문에", "따라서", "이로 인해", "초래하다"
        ]
        has_causal = any(_match_keyword(m, s_clean) for m in causal_markers)

        # Đếm số lượng con số hoặc tỷ lệ % với trailing non-letter guard chuẩn xác đa thị trường
        metrics_present = SemanticClauseMapper.has_metrics(s_clean)

        # Đếm từ nhấn mạnh / tiêu điểm
        emphasis_markers = [
            "chỉ", "duy nhất", "đặc biệt", "chính", "đột biến",
            "only", "solely", "crucial", "drastic", "anomaly",
            "唯一", "わずか", "急増", "異常",
            "오직", "단지", "급증", "이상"
        ]
        has_emphasis = any(_match_keyword(m, s_clean) for m in emphasis_markers)

        # Công thức: Gốc 4 thì + bonus mệnh đề phức
        score = 4
        if has_contrast:
            score += 1
        if has_causal:
            score += 1
        if metrics_present or has_emphasis:
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


def estimate_speech_duration(sentence: str, market: str = "EN") -> float:
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
        "nhưng", "vì", "do", "khi", "tuy", "khiến", "làm", "dẫn"
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

    slices = [0] + list(best_combo) + [n_words]
    return [(slices[b], slices[b+1]) for b in range(beat_count)]


def generate_scene_sub_director_plan(
    scene_id: str,
    sentence: str,
    hero_cutout_object: str,
    interacting_objects: List[str],
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
            if hasattr(w, "model_dump"):
                w = w.model_dump()
            if not isinstance(w, dict) or "start" not in w or "end" not in w or w["start"] is None or w["end"] is None:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} missing valid 'start'/'end' timestamps: {w!r}")
            if isinstance(w["start"], bool) or isinstance(w["end"], bool):
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} timestamps cannot be boolean: {w!r}")
            try:
                s_val = float(w["start"])
                e_val = float(w["end"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} has invalid non-numeric timestamps: {w!r}") from exc
            if math.isnan(s_val) or math.isnan(e_val) or math.isinf(s_val) or math.isinf(e_val):
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} timestamp is NaN or Inf: start={s_val}, end={e_val}")
            if s_val < 0.0 or e_val < s_val:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} has negative or inverted timestamps: start={s_val}, end={e_val}")
            if s_val < last_end - 1e-4:
                raise ValueError(f"Whisper integration fail-closed (Rule 120): Word #{idx} start timestamp ({s_val}s) is non-monotonic (earlier than preceding end {last_end}s)")
            last_end = e_val
            validated_whisper.append({"word": str(w.get("word", "")), "start": s_val, "end": e_val})

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

    dominant_families = SemanticClauseMapper.detect_dominant_families(sentence)
    layout = compute_kinetic_spatial_layout(
        scene_id=scene_id,
        family=dominant_families[0] if dominant_families else None,
        bounding_box=bounding_box,
        object_roles=object_roles,
        hero_cutout_object=hero_cutout_object,
        interacting_objects=interacting_objects,
        layout_type=layout_type,
        config_path=config_path
    )

    raw_beat_count = SemanticClauseMapper.calculate_beat_count(sentence)
    if dur < 4.0:
        beat_count = 4
    elif dur < 6.5:
        beat_count = min(5, raw_beat_count)
    else:
        beat_count = raw_beat_count

    # Fail closed if whisper words count is less than required micro-beat count (Rule 120, 131)
    if validated_whisper is not None:
        if len(validated_whisper) < beat_count:
            raise ValueError(
                f"Whisper integration fail-closed (Rule 120): Word count ({len(validated_whisper)}) "
                f"is less than required micro-beat count ({beat_count})"
            )

    hero_clean = (hero_cutout_object or "primary forensic document").split(" on ")[0].strip()
    inter1 = interacting_objects[0] if interacting_objects else "heavy brass caliper"
    inter2 = interacting_objects[1] if len(interacting_objects) > 1 else "red evidence thread"

    tool_keywords = ["caliper", "scissors", "stamp", "marker", "highlighter", "loupe", "glass", "pen", "knife", "pin", "ruler", "shears"]
    doc_keywords = ["ledger", "sheet", "document", "paper", "contract", "dossier", "card", "report", "photo", "chart", "page", "envelope", "file"]

    is_hero_tool = any(k in hero_clean.lower() for k in tool_keywords)
    is_inter1_doc = any(k in inter1.lower() for k in doc_keywords)

    if is_hero_tool:
        actor1_label = hero_clean
        actor1_material = "solid_metal" if "caliper" in hero_clean.lower() or "scissors" in hero_clean.lower() else "wood_rubber"
        anchor_label = inter1 if is_inter1_doc else "forensic accounting ledger document"
        anchor_material = "aged_newsprint_paper"
    else:
        anchor_label = hero_clean
        actor1_label = inter1
        actor1_material = "solid_metal" if "caliper" in inter1.lower() or "scissors" in inter1.lower() else "wood_rubber"
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
            mass_class="heavy" if "caliper" in actor1_label.lower() or "stamp" in actor1_label.lower() else "medium",
            z_index=3,
            role="interactive_tool"
        ),
        KineticObject(
            id="obj_tool2",
            label=inter2,
            material="cotton_thread" if "thread" in inter2.lower() else "fluorescent_ink",
            mass_class="feather" if "thread" in inter2.lower() else "light",
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
                    seg_end = round(seg_start + 0.010, 3)
                if seg_end >= dur:
                    seg_end = round(dur - 0.010 * (beat_count - 1 - b_i), 3)

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

    if beat_count <= 4:
        t_snap1 = whisper_windows[1][1] if whisper_windows else round(t_p1_end + 0.4, 3)
        t_snap2 = whisper_windows[2][1] if whisper_windows else round(t_snap1 + 0.6, 3)
        p2_end = t_snap1
        p3_end = t_snap2
    elif beat_count == 5:
        t_snap1 = whisper_windows[1][1] if whisper_windows else round(t_p1_end + 0.4, 3)
        t_hold1 = whisper_windows[2][1] if whisper_windows else round(t_snap1 + 0.8, 3)
        t_snap2 = whisper_windows[3][1] if whisper_windows else round(t_hold1 + 0.5, 3)
        p2_end = t_hold1
        p3_end = t_snap2
    elif beat_count == 6:
        p2_end = whisper_windows[2][1] if whisper_windows else round(t_p1_end + active_span * 0.4, 3)
        p3_end = whisper_windows[4][1] if whisper_windows else round(t_p1_end + active_span * 0.8, 3)
        t_snap1 = p2_end
        t_snap2 = p3_end
    else:
        p2_end = whisper_windows[3][1] if whisper_windows else round(t_p1_end + active_span * 0.5, 3)
        p3_end = whisper_windows[5][1] if whisper_windows else round(t_p1_end + active_span * 0.85, 3)
        t_snap1 = p2_end
        t_snap2 = p3_end

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
        "k1_dead_stop": f"{p2_end:.3f}s",
        "k2_dead_stop": f"{p3_end:.3f}s",
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
        win_b1 = f"{whisper_windows[0][0]:.3f}s - {whisper_windows[0][1]:.3f}s" if whisper_windows else f"0.000s - {t_p1_end:.3f}s"
        win_b2 = f"{whisper_windows[1][0]:.3f}s - {whisper_windows[1][1]:.3f}s" if whisper_windows else f"{t_p1_end:.3f}s - {t_snap1:.3f}s"
        win_b3 = f"{whisper_windows[2][0]:.3f}s - {whisper_windows[2][1]:.3f}s" if whisper_windows else f"{t_snap1:.3f}s - {t_snap2:.3f}s"
        win_b4 = f"{whisper_windows[3][0]:.3f}s - {whisper_windows[3][1]:.3f}s" if whisper_windows else f"{t_snap2:.3f}s - {dur:.3f}s"

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
                action_description=f"High-velocity snap burst in {round(whisper_windows[1][1] - whisper_windows[1][0], 2) if whisper_windows else 0.4:.1f}s (steep acceleration on twos / 12fps): The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.3f}s",
                handoff_to="B3",
                camera_micro_move="subtle punch-in zoom 1.0x to 1.15x tracking contact point",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P3_ESCALATION",
                time_window=win_b3,
                coupling_id="K2",
                action_description=f"Direct kinetic trigger: in a rapid {round(whisper_windows[2][1] - whisper_windows[2][0], 2) if whisper_windows else 0.6:.1f}s burst, the {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.3f}s",
                handoff_to="B4",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P4_LIVING_HOLD",
                time_window=win_b4,
                coupling_id=None,
                action_description=f"All objects permanently locked in rigid unified spatial anchor at final coordinate {layout.target_contact_pos} for the remaining {dur - t_snap2:.3f}s to cut, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            )
        ]
    elif beat_count == 5:
        win_b1 = f"{whisper_windows[0][0]:.3f}s - {whisper_windows[0][1]:.3f}s" if whisper_windows else f"0.000s - {t_p1_end:.3f}s"
        win_b2 = f"{whisper_windows[1][0]:.3f}s - {whisper_windows[1][1]:.3f}s" if whisper_windows else f"{t_p1_end:.3f}s - {t_snap1:.3f}s"
        win_b3 = f"{whisper_windows[2][0]:.3f}s - {whisper_windows[2][1]:.3f}s" if whisper_windows else f"{t_snap1:.3f}s - {t_hold1:.3f}s"
        win_b4 = f"{whisper_windows[3][0]:.3f}s - {whisper_windows[3][1]:.3f}s" if whisper_windows else f"{t_hold1:.3f}s - {t_snap2:.3f}s"
        win_b5 = f"{whisper_windows[4][0]:.3f}s - {whisper_windows[4][1]:.3f}s" if whisper_windows else f"{t_snap2:.3f}s - {dur:.3f}s"

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
                action_description=f"High-velocity snap burst in {round(whisper_windows[1][1] - whisper_windows[1][0], 2) if whisper_windows else 0.4:.1f}s: The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}",
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
                action_description=f"Direct kinetic trigger: in a rapid {round(whisper_windows[3][1] - whisper_windows[3][0], 2) if whisper_windows else 0.5:.1f}s burst, the {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P4_LIVING_HOLD",
                time_window=win_b5,
                coupling_id=None,
                action_description=f"All objects permanently locked in spatial anchor for remaining {dur - t_snap2:.3f}s, 12fps paper stop-motion texture, zero static freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            )
        ]
    elif beat_count == 6:
        t2 = round(t_p1_end + active_span * 0.20, 3)
        t3 = round(t_p1_end + active_span * 0.40, 3)
        t4 = round(t_p1_end + active_span * 0.60, 3)
        t5 = round(t_p1_end + active_span * 0.80, 3)
        win_b1 = f"{whisper_windows[0][0]:.3f}s - {whisper_windows[0][1]:.3f}s" if whisper_windows else f"0.000s - {t_p1_end:.3f}s"
        win_b2 = f"{whisper_windows[1][0]:.3f}s - {whisper_windows[1][1]:.3f}s" if whisper_windows else f"{t_p1_end:.3f}s - {t2:.3f}s"
        win_b3 = f"{whisper_windows[2][0]:.3f}s - {whisper_windows[2][1]:.3f}s" if whisper_windows else f"{t2:.3f}s - {t3:.3f}s"
        win_b4 = f"{whisper_windows[3][0]:.3f}s - {whisper_windows[3][1]:.3f}s" if whisper_windows else f"{t3:.3f}s - {t4:.3f}s"
        win_b5 = f"{whisper_windows[4][0]:.3f}s - {whisper_windows[4][1]:.3f}s" if whisper_windows else f"{t4:.3f}s - {t5:.3f}s"
        win_b6 = f"{whisper_windows[5][0]:.3f}s - {whisper_windows[5][1]:.3f}s" if whisper_windows else f"{t5:.3f}s - {dur:.3f}s"

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
                coupling_id="K1",
                action_description=f"High-velocity snap burst: {actor1_label} {c1.action_verb} {anchor_label}",
                handoff_to="B3",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=win_b3,
                coupling_id="K1",
                action_description=f"Mechanical impact causes {c1.physical_reaction}, leaving {c1.residue}",
                handoff_to="B4",
                camera_micro_move="camera punch-in zoom 1.0x to 1.35x tracking inspection point",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P3_ESCALATION",
                time_window=win_b4,
                coupling_id="K2",
                action_description=f"Action on {anchor_label} immediately triggers {inter2} to {c2.action_verb} {anchor_label}",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P3_ESCALATION",
                time_window=win_b5,
                coupling_id="K2",
                action_description=f"{c2.physical_reaction}, leaving {c2.residue}",
                handoff_to="B6",
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B6",
                phase="P4_LIVING_HOLD",
                time_window=win_b6,
                coupling_id=None,
                action_description=f"All objects locked in spatial anchor for remaining {dur - p3_end:.3f}s, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[5][2] if whisper_windows else None
            )
        ]
    else:
        t2 = round(t_p1_end + active_span * 0.16, 3)
        t3 = round(t_p1_end + active_span * 0.33, 3)
        t4 = round(t_p1_end + active_span * 0.50, 3)
        t5 = round(t_p1_end + active_span * 0.67, 3)
        t6 = round(t_p1_end + active_span * 0.84, 3)
        win_b1 = f"{whisper_windows[0][0]:.3f}s - {whisper_windows[0][1]:.3f}s" if whisper_windows else f"0.000s - {t_p1_end:.3f}s"
        win_b2 = f"{whisper_windows[1][0]:.3f}s - {whisper_windows[1][1]:.3f}s" if whisper_windows else f"{t_p1_end:.3f}s - {t2:.3f}s"
        win_b3 = f"{whisper_windows[2][0]:.3f}s - {whisper_windows[2][1]:.3f}s" if whisper_windows else f"{t2:.3f}s - {t3:.3f}s"
        win_b4 = f"{whisper_windows[3][0]:.3f}s - {whisper_windows[3][1]:.3f}s" if whisper_windows else f"{t3:.3f}s - {t4:.3f}s"
        win_b5 = f"{whisper_windows[4][0]:.3f}s - {whisper_windows[4][1]:.3f}s" if whisper_windows else f"{t4:.3f}s - {t5:.3f}s"
        win_b6 = f"{whisper_windows[5][0]:.3f}s - {whisper_windows[5][1]:.3f}s" if whisper_windows else f"{t5:.3f}s - {t6:.3f}s"
        win_b7 = f"{whisper_windows[6][0]:.3f}s - {whisper_windows[6][1]:.3f}s" if whisper_windows else f"{t6:.3f}s - {dur:.3f}s"

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
                coupling_id="K1",
                action_description=f"{actor1_label} enters frame with crisp paper deceleration and aligns with {anchor_label}",
                handoff_to="B3",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=win_b3,
                coupling_id="K1",
                action_description=f"{actor1_label} {c1.action_verb} {anchor_label}, causing {c1.physical_reaction}",
                handoff_to="B4",
                camera_micro_move="camera punch-in zoom 1.0x to 1.35x tracking contact point",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P2_TENSION",
                time_window=win_b4,
                coupling_id="K1",
                action_description=f"Mechanical settling permanently leaves {c1.residue}",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P3_ESCALATION",
                time_window=win_b5,
                coupling_id="K2",
                action_description=f"{inter2} {c2.action_verb} {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B6",
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B6",
                phase="P3_ESCALATION",
                time_window=win_b6,
                coupling_id="K2",
                action_description=f"Action solidifies, leaving {c2.residue}",
                handoff_to="B7",
                vo_keyword=whisper_windows[5][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B7",
                phase="P4_LIVING_HOLD",
                time_window=win_b7,
                coupling_id=None,
                action_description="All objects locked in spatial anchor, organic 12fps paper stop-motion jitter, zero static freeze to cut",
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
    cam_directive_detected = camera_directive or "Dynamic top-down camera with subtle punch-in on impact"

    for b in beats:
        t_win = b.get("time_window", "")
        c_id = b.get("coupling_id")
        action = b.get("action_description", "")
        cam_move = b.get("camera_micro_move")

        if cam_move and "punch-in" in cam_move:
            cam_directive_detected = "Dynamic crash-zoom punch-in from 1.0x to 1.35x tracking inspection point"

        if action and "causing" in action:
            steps_text.append(f"{t_win}: {action.rstrip('.')}.")
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
        else:
            steps_text.append(f"{t_win}: {action.rstrip('.')}.")

    chain_str = " ".join(steps_text)

    prompt = (
        f"Forensic documentary motion graphics, tactile stop-motion editorial layout, animated on twos, "
        f"12fps posterize-time stop-motion feel, graphic layout assembly, snappy infographic motion, "
        f"crisp editorial typography on aged newsprint desk (#F4F1EA), soft directional physical drop shadows. "
        f"IMAGE-TO-VIDEO TECHNICAL DIRECTIVE: "
        f"[Style: Rigid documentary motion design, zero cartoon puppet motion, zero organic wobbling]. "
        f"[Speed & Pacing: True Vox Stop-Motion Snappiness. High-velocity transient bursts: all movements complete rapidly in 0.4s - 0.6s on twos (12 discrete poses per second), immediately followed by long motionless dead-stop holds. Zero slow drifting, zero floaty linear glide, zero continuous cruise]. "
        f"[Camera: {cam_directive_detected}]. "
        f"[Timeline Kinematics: [KINETIC CAUSAL CHAIN]: {chain_str}]. "
        f"[Motion Design: Snappy 2D graphic reveals, rigid planar cutouts, linear slides, mechanical snap-down]. "
        f"[Constraints: [PHYSICAL CONSTRAINTS]: Every element is a rigid 2D planar cutout with clean cast shadows. "
        f"Zero independent drifting, zero 3D fluid morphing, all graphics locked in 12fps paper stop-motion hold to the cut]."
    )

    return prompt.strip()
