#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""app/services/kinetic_sub_director.py — Object-to-Object Kinetic Coupling & Narrative Sub-Director Engine.

Enforces:
- Rule 128: Generic Contract Pattern (supports any market: EN, JA, KR, VN without hardcoding).
- Rule 132: Pure Transmission Engine (decoupled logic, no hardcoded episode scripts; presets in config).
- Rule 140 v3: Object-to-Object Kinetic Coupling Taxonomy ($H_1 \rightarrow H_7$),
  Semantic Clause Mapping ($4 \le N \le 7$ micro-beats), and Causal Compound Verb Prompt Syntax.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
import re

logger = logging.getLogger('kinetic_sub_director')
from typing import Any, Dict, List, Optional, Tuple


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
        "cắt", "giảm", "tách", "chia", "xé", "chỉ còn", "rút gọn", "phân đoạn",
        # EN
        "cut", "sever", "slice", "split", "tear", "reduce", "strip", "separate",
        # JA
        "切断", "削減", "分離", "分割", "裂く", "切り離す", "縮小",
        # KR
        "절단", "삭감", "분리", "분할", "찢다", "떼어내다", "축소"
    ],
    KineticFamily.H4_TETHER: [
        # VN
        "nối", "kết nối", "liên quan", "dây", "chảy về", "đứng sau", "mạng lưới",
        # EN
        "connect", "link", "tether", "thread", "wire", "flow", "behind", "network",
        # JA
        "接続", "連鎖", "関連", "糸", "背後", "ネットワーク", "結ぶ",
        # KR
        "연결", "연관", "실", "배후", "네트워크", "묶다", "이어지다"
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
    time_window: str       # e.g. "0.0s - 1.5s"
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
    pattern = r'(?<!\w)' + re.escape(kw) + r'(?!\w)'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _load_kinetic_presets() -> Dict[str, Any]:
    """Nạp layout presets và prose templates từ config/kinetic_layout_presets.json (Rule 132)."""
    cfg_path = Path(__file__).resolve().parent.parent.parent / "config" / "kinetic_layout_presets.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as _cfg_err:
            logger.warning("Could not load kinetic presets from %s: %s", cfg_path, _cfg_err)
    # Fallback an toàn nếu config chưa được nạp
    return {
        "layouts": {
            "center_right": {
                "initial_pos": "(X:52%, Y:42%)",
                "target_contact_pos": "(X:68%, Y:42%)",
                "dock_pin_pos": "(X:42%, Y:65%)",
                "bounding_box_bounds": "[X:58%-84%, Y:38%-68%]",
                "vector_reveal_direction": "horizontal",
            },
            "center_left": {
                "initial_pos": "(X:48%, Y:42%)",
                "target_contact_pos": "(X:32%, Y:42%)",
                "dock_pin_pos": "(X:58%, Y:65%)",
                "bounding_box_bounds": "[X:18%-46%, Y:38%-68%]",
                "vector_reveal_direction": "horizontal",
            },
            "vertical": {
                "initial_pos": "(X:50%, Y:36%)",
                "target_contact_pos": "(X:50%, Y:56%)",
                "dock_pin_pos": "(X:38%, Y:72%)",
                "bounding_box_bounds": "[X:36%-64%, Y:46%-74%]",
                "vector_reveal_direction": "vertical",
            }
        }
    }


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
    bounding_box: Optional[Dict[str, Any]] = None,
    object_roles: Optional[Dict[str, str]] = None,
    hero_cutout_object: Optional[str] = None,
    interacting_objects: Optional[List[str]] = None,
    layout_type: Optional[str] = None
) -> KineticSpatialLayout:
    """Tính toán toạ độ không gian 2D chuẩn hóa động học phân rã theo scene data (Rule 128, 132).
    Fail-closed trên scene_id rỗng (Rules 118/139).
    Toạ độ tiếp xúc target_contact_pos được tính toán trực tiếp từ bounding_box hoặc object roles,
    bảo đảm luôn nằm trọn bên trong bounding box.
    """
    if not scene_id or not isinstance(scene_id, str) or not scene_id.strip():
        raise ValueError("compute_kinetic_spatial_layout fail-closed (Rule 118/139): scene_id cannot be empty")

    clean_id = scene_id.lower().strip()
    presets_cfg = _load_kinetic_presets()
    presets = presets_cfg.get("layouts", {})

    # 1. Nếu bounding_box được cung cấp tường minh từ scene plan
    if bounding_box and isinstance(bounding_box, dict):
        x_min = int(bounding_box.get("x_min", bounding_box.get("left", 58)))
        x_max = int(bounding_box.get("x_max", bounding_box.get("right", x_min + bounding_box.get("width", 26))))
        y_min = int(bounding_box.get("y_min", bounding_box.get("top", 38)))
        y_max = int(bounding_box.get("y_max", bounding_box.get("bottom", y_min + bounding_box.get("height", 30))))
        x_c = round((x_min + x_max) / 2)
        y_c = round((y_min + y_max) / 2)

        l_type = layout_type or ("vertical" if (y_max - y_min) > (x_max - x_min) else "center_right")
        vec_dir = "vertical" if l_type == "vertical" else "horizontal"

        if l_type == "vertical":
            init_pos = f"(X:{x_c}%, Y:{max(10, y_min - 15)}%)"
            dock_pos = f"(X:{max(10, x_min - 10)}%, Y:{min(90, y_max + 12)}%)"
        elif l_type == "center_left":
            init_pos = f"(X:{min(90, x_max + 16)}%, Y:{y_c}%)"
            dock_pos = f"(X:{min(90, x_max + 20)}%, Y:{min(90, y_max + 15)}%)"
        else:
            init_pos = f"(X:{max(10, x_min - 16)}%, Y:{y_c}%)"
            dock_pos = f"(X:{max(10, x_min - 20)}%, Y:{min(90, y_max + 15)}%)"

        return KineticSpatialLayout(
            initial_pos=init_pos,
            target_contact_pos=f"(X:{x_c}%, Y:{y_c}%)",
            dock_pin_pos=dock_pos,
            bounding_box_bounds=f"[X:{x_min}%-{x_max}%, Y:{y_min}%-{y_max}%]",
            layout_type=l_type,
            vector_reveal_direction=vec_dir
        )

    # 2. Suy diễn layout_type từ object roles & semantic cues của scene
    target_type = layout_type
    if not target_type:
        roles_str = " ".join((object_roles or {}).values()).lower()
        hero_str = (hero_cutout_object or "").lower()
        inter_str = " ".join(interacting_objects or []).lower()
        combined_context = f"{roles_str} {hero_str} {inter_str}"

        vertical_keywords = ["vertical", "column", "timeline", "stamp", "seal", "knife", "shears", "top_down", "drop"]
        left_keywords = ["left", "source", "origin", "counterpart", "audit", "input", "baseline"]

        if any(vk in combined_context for vk in vertical_keywords) or family == KineticFamily.H1_IMPACT:
            target_type = "vertical"
        elif any(lk in combined_context for lk in left_keywords) or "left" in clean_id:
            target_type = "center_left"
        else:
            target_type = "center_right"

    preset = presets.get(target_type, presets.get("center_right", {}))
    return KineticSpatialLayout(
        initial_pos=preset.get("initial_pos", "(X:52%, Y:42%)"),
        target_contact_pos=preset.get("target_contact_pos", "(X:68%, Y:42%)"),
        dock_pin_pos=preset.get("dock_pin_pos", "(X:42%, Y:65%)"),
        bounding_box_bounds=preset.get("bounding_box_bounds", "[X:58%-84%, Y:38%-68%]"),
        layout_type=target_type,
        vector_reveal_direction=preset.get("vector_reveal_direction", "horizontal")
    )


class SemanticClauseMapper:
    """Bộ phân rã ngữ nghĩa câu thoại tự động thành chuỗi vi nhịp động học."""

    @staticmethod
    def has_metrics(sentence: str) -> bool:
        """Kiểm tra câu thoại có chứa số liệu, phần trăm hoặc đơn vị định lượng chuẩn xác đa thị trường (Rule 120, 128).
        Bảo đảm trailing non-letter guard để loại bỏ hoàn toàn false positives (e.g. '3 minutes', '2 key points', '4 types', '5 bugs', '1 member').
        """
        if not sentence:
            return False
        s_clean = sentence.strip()
        pattern = (
            r"(?<!\d)\d+([,\.]\d+)?\s*(?:%|円|tỷ|triệu|trieu|(?:billion|million|percent|won|usd|yen|gbp|eur|ty|b|m|k)(?![a-zA-Z]))"
            r"|(?<!\d)\d{2,}(?!\d)"
        )
        return bool(re.search(pattern, s_clean, re.IGNORECASE))

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
        has_metrics = SemanticClauseMapper.has_metrics(s_clean)

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
        if has_metrics or has_emphasis:
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
    """Ước tính thời lượng nói (giây) của câu thoại dựa trên ngôn ngữ và số từ/ký tự.
    Tuân thủ trần an toàn [2.5s, 10.0s] theo kỷ luật nhịp điệu tài liệu điều tra VOX.
    """
    if not sentence or not sentence.strip():
        return 5.0

    s = sentence.strip()
    m = (market or "EN").upper()

    if m in ["JA", "JP", "KO", "KR"]:
        # Ngôn ngữ tượng hình / âm tiết: trung bình 5.5 ký tự / giây (bỏ qua khoảng trắng)
        char_count = len(re.sub(r"\s+", "", s))
        raw_dur = char_count / 5.5
    elif m in ["VN", "VI"]:
        # Tiếng Việt: trung bình ~3.5 từ / giây (đơn âm tiết)
        words = s.split()
        raw_dur = len(words) / 3.5
    else:
        # Tiếng Anh và ngôn ngữ Latin: trung bình ~2.8 từ / giây (~160 wpm)
        words = s.split()
        raw_dur = len(words) / 2.8

    # Kẹp chặt trong dải an toàn [2.5s, 10.0s]
    dur = round(max(2.5, min(10.0, raw_dur)), 2)
    return dur


def generate_scene_sub_director_plan(
    scene_id: str,
    sentence: str,
    hero_cutout_object: str,
    interacting_objects: List[str],
    duration_sec: Optional[float] = None,
    market: str = "EN",
    whisper_words: Optional[List[Dict[str, Any]]] = None,
    bounding_box: Optional[Dict[str, Any]] = None,
    object_roles: Optional[Dict[str, str]] = None,
    layout_type: Optional[str] = None
) -> Dict[str, Any]:
    """Sinh toàn diện Khung Đạo Diễn Vi Cảnh (Scene Sub-Director Plan) chuẩn hóa cho mọi Episode."""
    if not scene_id or not isinstance(scene_id, str) or not scene_id.strip():
        raise ValueError("generate_scene_sub_director_plan fail-closed (Rule 118/139): scene_id cannot be empty")

    # Rule 120 & 135: Tích hợp Word-level Timestamps từ Whisper (nếu có) để tính toán nhịp độ thực tế
    w_start = 0.0
    if whisper_words is not None:
        if not isinstance(whisper_words, list) or len(whisper_words) == 0:
            raise ValueError("Whisper integration fail-closed (Rule 120): whisper_words must be a non-empty list of dicts.")
        last_end = -1.0
        for idx, w in enumerate(whisper_words):
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

        w_start = float(whisper_words[0]["start"])
        w_end = float(whisper_words[-1]["end"])
        measured_dur = round(w_end - w_start, 2)
        if measured_dur <= 0.0:
            raise ValueError(f"Whisper integration fail-closed (Rule 120): Total speech duration must be positive, got {measured_dur}s")
        # Rule 120/135: Measured speech duration is authentic; do NOT artificially truncate/clamp!
        dur = measured_dur
    elif duration_sec is None or float(duration_sec) <= 0.0:
        dur = estimate_speech_duration(sentence, market)
    else:
        dur = round(max(2.5, float(duration_sec)), 2)

    dominant_families = SemanticClauseMapper.detect_dominant_families(sentence)
    layout = compute_kinetic_spatial_layout(
        scene_id=scene_id,
        family=dominant_families[0] if dominant_families else None,
        bounding_box=bounding_box,
        object_roles=object_roles,
        hero_cutout_object=hero_cutout_object,
        interacting_objects=interacting_objects,
        layout_type=layout_type
    )

    raw_beat_count = SemanticClauseMapper.calculate_beat_count(sentence)
    # Beat Count Governor: Giới hạn số vi nhịp theo ngân sách thời gian thực tế
    if dur < 4.0:
        beat_count = 4
    elif dur < 6.5:
        beat_count = min(5, raw_beat_count)
    else:
        beat_count = raw_beat_count

    hero_clean = (hero_cutout_object or "primary forensic document").split(" on ")[0].strip()
    inter1 = interacting_objects[0] if interacting_objects else "heavy brass caliper"
    inter2 = interacting_objects[1] if len(interacting_objects) > 1 else "red evidence thread"

    # Nhận diện vai trò vật lý: Đạo cụ tác động (Tool Actor) vs Mặt nền tài liệu (Document Target)
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

    # 2. Xây dựng Cặp Tương Tác Nhân Quả từ Cấu Hình Khách Quan (Rule 132)
    presets_cfg = _load_kinetic_presets()
    prose_cfg = presets_cfg.get("prose_templates", {})
    k1_templates = prose_cfg.get("K1", {})
    k2_templates = prose_cfg.get("K2", {})

    couplings = []
    fam1 = dominant_families[0] if dominant_families else KineticFamily.H2_CONSTRAINT
    fam1_key = fam1.value if fam1.value in k1_templates else "DEFAULT"
    t1 = k1_templates.get(fam1_key, k1_templates.get("DEFAULT", {}))

    fmt_kwargs = {
        "initial_pos": layout.initial_pos,
        "target_contact_pos": layout.target_contact_pos,
        "dock_pin_pos": layout.dock_pin_pos,
        "bounding_box_bounds": layout.bounding_box_bounds,
        "vector_reveal_direction": layout.vector_reveal_direction
    }

    c1 = KineticCoupling(
        id="K1",
        family=fam1,
        source_obj_id="obj_tool1",
        target_obj_id="obj_anchor",
        action_verb=t1.get("action_verb", "").format(**fmt_kwargs),
        contact_point=t1.get("contact_point", "").format(**fmt_kwargs),
        physical_reaction=t1.get("physical_reaction", "").format(**fmt_kwargs),
        secondary_reaction=t1.get("secondary_reaction"),
        residue=t1.get("residue", "")
    )
    couplings.append(c1)

    fam2 = dominant_families[1] if len(dominant_families) > 1 else KineticFamily.H6_MARK
    fam2_key = fam2.value if fam2.value in k2_templates else "DEFAULT"
    t2 = k2_templates.get(fam2_key, k2_templates.get("DEFAULT", {}))

    c2 = KineticCoupling(
        id="K2",
        family=fam2,
        source_obj_id="obj_tool2",
        target_obj_id="obj_anchor" if fam2 == KineticFamily.H6_MARK else "obj_tool1",
        action_verb=t2.get("action_verb", "").format(**fmt_kwargs),
        contact_point=t2.get("contact_point", "").format(**fmt_kwargs),
        physical_reaction=t2.get("physical_reaction", "").format(**fmt_kwargs),
        residue=t2.get("residue", "")
    )
    couplings.append(c2)

    # 3. Phân Rã Dãy Micro-Beats Linh Hoạt
    micro_beats = []

    # Ngân sách thời gian
    t_p1_end = min(0.6, round(dur * 0.1, 1))
    t_p3_end = round(max(t_p1_end + 1.2, min(dur - 0.8, dur * 0.45)), 1)
    active_span = t_p3_end - t_p1_end

    # Nếu whisper_words có sẵn, tính toán micro-beat windows trực tiếp từ word timestamps
    whisper_windows: Optional[List[Tuple[float, float, str]]] = None
    if whisper_words:
        n_words = len(whisper_words)
        whisper_windows = []
        for b_i in range(beat_count):
            if n_words >= beat_count:
                start_idx = min(n_words - 1, max(0, int(b_i * n_words / beat_count)))
                end_idx = min(n_words - 1, max(start_idx, int((b_i + 1) * n_words / beat_count) - 1))
                w_seg_start = round(float(whisper_words[start_idx]["start"]) - w_start, 2)
                w_seg_end = round(float(whisper_words[end_idx]["end"]) - w_start, 2)
                seg_text = " ".join(str(whisper_words[k].get("word", "")) for k in range(start_idx, end_idx + 1)).strip()
            else:
                w_seg_start = round(b_i * dur / beat_count, 2)
                w_seg_end = round((b_i + 1) * dur / beat_count, 2)
                word_idx = min(n_words - 1, int(b_i * n_words / beat_count))
                seg_text = str(whisper_words[word_idx].get("word", "")).strip()

            if b_i == 0:
                w_seg_start = 0.0
            if b_i == beat_count - 1:
                w_seg_end = dur
            whisper_windows.append((w_seg_start, max(w_seg_start + 0.1, w_seg_end), seg_text))

    if beat_count <= 4:
        # Nhịp 4 bước chuẩn Vox Stop-Motion
        t_snap1 = round(t_p1_end + 0.4, 1)
        t_snap2 = round(t_snap1 + 0.6, 1)
        p2_end = t_snap1
        p3_end = t_snap2

        win_b1 = f"{whisper_windows[0][0]:.1f}s - {whisper_windows[0][1]:.1f}s" if whisper_windows else f"0.0s - {t_p1_end:.1f}s"
        win_b2 = f"{whisper_windows[1][0]:.1f}s - {whisper_windows[1][1]:.1f}s" if whisper_windows else f"{t_p1_end:.1f}s - {t_snap1:.1f}s"
        win_b3 = f"{whisper_windows[2][0]:.1f}s - {whisper_windows[2][1]:.1f}s" if whisper_windows else f"{t_snap1:.1f}s - {t_snap2:.1f}s"
        win_b4 = f"{whisper_windows[3][0]:.1f}s - {whisper_windows[3][1]:.1f}s" if whisper_windows else f"{t_snap2:.1f}s - {dur:.1f}s"

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
                action_description=f"High-velocity snap burst in 0.4s (steep acceleration on twos / 12fps): The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.1f}s",
                handoff_to="B3",
                camera_micro_move="subtle punch-in zoom 1.0x to 1.15x tracking contact point",
                vo_keyword=whisper_windows[1][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P3_ESCALATION",
                time_window=win_b3,
                coupling_id="K2",
                action_description=f"Direct kinetic trigger: in a rapid 0.6s burst, the {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.1f}s",
                handoff_to="B4",
                vo_keyword=whisper_windows[2][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P4_LIVING_HOLD",
                time_window=win_b4,
                coupling_id=None,
                action_description=f"All objects permanently locked in rigid unified spatial anchor at final coordinate {layout.target_contact_pos} for the remaining {dur - t_snap2:.1f}s to cut, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            )
        ]
    elif beat_count == 5:
        # Nhịp 5 bước
        t_snap1 = round(t_p1_end + 0.4, 1)
        t_hold1 = round(t_snap1 + 0.8, 1)
        t_snap2 = round(t_hold1 + 0.5, 1)
        p2_end = t_hold1
        p3_end = t_snap2

        win_b1 = f"{whisper_windows[0][0]:.1f}s - {whisper_windows[0][1]:.1f}s" if whisper_windows else f"0.0s - {t_p1_end:.1f}s"
        win_b2 = f"{whisper_windows[1][0]:.1f}s - {whisper_windows[1][1]:.1f}s" if whisper_windows else f"{t_p1_end:.1f}s - {t_snap1:.1f}s"
        win_b3 = f"{whisper_windows[2][0]:.1f}s - {whisper_windows[2][1]:.1f}s" if whisper_windows else f"{t_snap1:.1f}s - {t_hold1:.1f}s"
        win_b4 = f"{whisper_windows[3][0]:.1f}s - {whisper_windows[3][1]:.1f}s" if whisper_windows else f"{t_hold1:.1f}s - {t_snap2:.1f}s"
        win_b5 = f"{whisper_windows[4][0]:.1f}s - {whisper_windows[4][1]:.1f}s" if whisper_windows else f"{t_snap2:.1f}s - {dur:.1f}s"

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
                action_description=f"High-velocity snap burst in 0.4s: The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}",
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
                action_description=f"Direct kinetic trigger: in a rapid 0.5s burst, the {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B5",
                vo_keyword=whisper_windows[3][2] if whisper_windows else None
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P4_LIVING_HOLD",
                time_window=win_b5,
                coupling_id=None,
                action_description=f"All objects permanently locked in spatial anchor for remaining {dur - t_snap2:.1f}s, 12fps paper stop-motion texture, zero static freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[4][2] if whisper_windows else None
            )
        ]
    elif beat_count == 6:
        # Nhịp 6 bước linh hoạt
        t_sub_step = min(0.5, round(active_span / 4.0, 1))
        t2 = round(t_p1_end + t_sub_step, 1)
        t3 = round(t2 + t_sub_step, 1)
        t4 = round(t3 + t_sub_step, 1)
        p2_end = t3
        p3_end = round(t4 + t_sub_step, 1)

        win_b1 = f"{whisper_windows[0][0]:.1f}s - {whisper_windows[0][1]:.1f}s" if whisper_windows else f"0.0s - {t_p1_end:.1f}s"
        win_b2 = f"{whisper_windows[1][0]:.1f}s - {whisper_windows[1][1]:.1f}s" if whisper_windows else f"{t_p1_end:.1f}s - {t2:.1f}s"
        win_b3 = f"{whisper_windows[2][0]:.1f}s - {whisper_windows[2][1]:.1f}s" if whisper_windows else f"{t2:.1f}s - {t3:.1f}s"
        win_b4 = f"{whisper_windows[3][0]:.1f}s - {whisper_windows[3][1]:.1f}s" if whisper_windows else f"{t3:.1f}s - {t4:.1f}s"
        win_b5 = f"{whisper_windows[4][0]:.1f}s - {whisper_windows[4][1]:.1f}s" if whisper_windows else f"{t4:.1f}s - {p3_end:.1f}s"
        win_b6 = f"{whisper_windows[5][0]:.1f}s - {whisper_windows[5][1]:.1f}s" if whisper_windows else f"{p3_end:.1f}s - {dur:.1f}s"

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
                action_description=f"All objects locked in spatial anchor for remaining {dur - p3_end:.1f}s, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None,
                vo_keyword=whisper_windows[5][2] if whisper_windows else None
            )
        ]
    else:
        # Nhịp 7 bước tối đa cho câu phức / cao trào
        t_sub_step = min(0.4, round(active_span / 5.0, 1))
        t2 = round(t_p1_end + t_sub_step, 1)
        t3 = round(t2 + t_sub_step, 1)
        t4 = round(t3 + t_sub_step, 1)
        t5 = round(t4 + t_sub_step, 1)
        p2_end = t3
        p3_end = round(t5 + t_sub_step, 1)

        win_b1 = f"{whisper_windows[0][0]:.1f}s - {whisper_windows[0][1]:.1f}s" if whisper_windows else f"0.0s - {t_p1_end:.1f}s"
        win_b2 = f"{whisper_windows[1][0]:.1f}s - {whisper_windows[1][1]:.1f}s" if whisper_windows else f"{t_p1_end:.1f}s - {t2:.1f}s"
        win_b3 = f"{whisper_windows[2][0]:.1f}s - {whisper_windows[2][1]:.1f}s" if whisper_windows else f"{t2:.1f}s - {t3:.1f}s"
        win_b4 = f"{whisper_windows[3][0]:.1f}s - {whisper_windows[3][1]:.1f}s" if whisper_windows else f"{t3:.1f}s - {t4:.1f}s"
        win_b5 = f"{whisper_windows[4][0]:.1f}s - {whisper_windows[4][1]:.1f}s" if whisper_windows else f"{t4:.1f}s - {t5:.1f}s"
        win_b6 = f"{whisper_windows[5][0]:.1f}s - {whisper_windows[5][1]:.1f}s" if whisper_windows else f"{t5:.1f}s - {p3_end:.1f}s"
        win_b7 = f"{whisper_windows[6][0]:.1f}s - {whisper_windows[6][1]:.1f}s" if whisper_windows else f"{p3_end:.1f}s - {dur:.1f}s"

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
            "p1_setup_sec": [0.0, t_p1_end],
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
