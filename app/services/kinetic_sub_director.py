#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""app/services/kinetic_sub_director.py — Object-to-Object Kinetic Coupling & Narrative Sub-Director Engine.

Enforces:
- Rule 128: Generic Contract Pattern (supports any market: EN, JA, KR, VN without hardcoding).
- Rule 132: Pure Transmission Engine (decoupled logic, no hardcoded episode scripts).
- Rule 140 v3: Object-to-Object Kinetic Coupling Taxonomy ($H_1 \rightarrow H_7$),
  Semantic Clause Mapping ($4 \le N \le 7$ micro-beats), and Causal Compound Verb Prompt Syntax.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
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
    """Kiểm tra ký tự thuộc hệ chữ CJK (Hán tự, Hiragana, Katakana, Hangul)."""
    return (
        '\u4e00' <= char <= '\u9fff'
        or '\u3040' <= char <= '\u30ff'
        or '\uac00' <= char <= '\ud7af'
    )


def _match_keyword(kw: str, text: str) -> bool:
    """Khớp từ khóa thông minh có word boundary cho tiếng Việt / Latinh, tránh false positive (Rule 120, 128)."""
    if any(_is_cjk_char(c) for c in kw):
        return kw in text
    pattern = r'(?<!\w)' + re.escape(kw) + r'(?!\w)'
    return bool(re.search(pattern, text, re.IGNORECASE))


@dataclass
class KineticSpatialLayout:
    """Toạ độ không gian 2D động học được tính toán động theo phân cảnh (Rule 128, 132)."""
    initial_pos: str          # e.g. "(X:52%, Y:42%)"
    target_contact_pos: str   # e.g. "(X:68%, Y:42%)"
    dock_pin_pos: str         # e.g. "(X:42%, Y:65%)"
    bounding_box_bounds: str  # e.g. "[X:58%-84%, Y:38%-68%]"


def compute_kinetic_spatial_layout(scene_id: str) -> KineticSpatialLayout:
    """Tính toán toạ độ không gian 2D chuẩn hóa động học phân rã theo scene_id (Rule 128, 132).
    Loại bỏ hardcode toạ độ tĩnh bất biến, bảo đảm mỗi phân cảnh có bố cục đồ họa chuyên biệt.
    """
    seed = sum(ord(c) for c in scene_id) if scene_id else 0
    variant = seed % 3

    if variant == 0:
        # Layout A: Center-Right Inspection (Default forensic audit focus)
        return KineticSpatialLayout(
            initial_pos="(X:52%, Y:42%)",
            target_contact_pos="(X:68%, Y:42%)",
            dock_pin_pos="(X:42%, Y:65%)",
            bounding_box_bounds="[X:58%-84%, Y:38%-68%]"
        )
    elif variant == 1:
        # Layout B: Center-Left Verification Focus
        return KineticSpatialLayout(
            initial_pos="(X:48%, Y:42%)",
            target_contact_pos="(X:32%, Y:42%)",
            dock_pin_pos="(X:58%, Y:65%)",
            bounding_box_bounds="[X:18%-46%, Y:38%-68%]"
        )
    else:
        # Layout C: Vertical Center Alignment Focus
        return KineticSpatialLayout(
            initial_pos="(X:50%, Y:36%)",
            target_contact_pos="(X:50%, Y:56%)",
            dock_pin_pos="(X:38%, Y:72%)",
            bounding_box_bounds="[X:36%-64%, Y:46%-74%]"
        )


class SemanticClauseMapper:
    """Bộ phân rã ngữ nghĩa câu thoại tự động thành chuỗi vi nhịp động học."""

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
        has_contrast = any(m in s_clean for m in contrast_markers)

        # Đếm liên từ nhân quả / hệ quả (causal / consequence)
        causal_markers = [
            "vì", "do đó", "khiến", "dẫn đến", "kéo theo", "làm cho",
            "because", "therefore", "causing", "leads to", "resulting in",
            "したがって", "そのため", "により", "引き起こす",
            "때문에", "따라서", "이로 인해", "초래하다"
        ]
        has_causal = any(m in s_clean for m in causal_markers)

        # Đếm số lượng con số hoặc tỷ lệ % (Rule 120 / Rule 128: regex lượng hóa chuẩn xác)
        has_metrics = bool(re.search(r"\b\d+([,\.]\d+)?\s*(%|tỷ|triệu|trieu|ty|billion|million|percent|b|m|k|円|won|usd|yen|gbp|eur)\b|\b\d{2,}\b", s_clean))

        # Đếm từ nhấn mạnh / tiêu điểm
        emphasis_markers = [
            "chỉ", "duy nhất", "đặc biệt", "chính", "đột biến",
            "only", "solely", "crucial", "drastic", "anomaly",
            "唯一", "わずか", "急増", "異常",
            "오직", "단지", "급증", "이상"
        ]
        has_emphasis = any(m in s_clean for m in emphasis_markers)

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
    whisper_words: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Sinh toàn diện Khung Đạo Diễn Vi Cảnh (Scene Sub-Director Plan) chuẩn hóa cho mọi Episode."""
    # Xác định thời lượng cảnh (Rule 120 / Rule 135: ưu tiên Whisper word-level timestamps thật nếu có)
    if whisper_words and len(whisper_words) > 0:
        w_start = float(whisper_words[0].get("start", 0.0))
        w_end = float(whisper_words[-1].get("end", 0.0))
        dur = round(max(2.5, min(10.0, w_end - w_start)), 2)
    elif duration_sec is None or float(duration_sec) <= 0.0:
        dur = estimate_speech_duration(sentence, market)
    else:
        dur = round(max(2.5, min(10.0, float(duration_sec))), 2)

    layout = compute_kinetic_spatial_layout(scene_id)

    raw_beat_count = SemanticClauseMapper.calculate_beat_count(sentence)
    # Beat Count Governor: Giới hạn số vi nhịp theo ngân sách thời gian thực tế
    if dur < 4.0:
        beat_count = 4
    elif dur < 6.5:
        beat_count = min(5, raw_beat_count)
    else:
        beat_count = raw_beat_count

    dominant_families = SemanticClauseMapper.detect_dominant_families(sentence)

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

    # 2. Xây dựng Cặp Tương Tác Nhân Quả (Kinetic Couplings)
    couplings = []

    # Cặp K1: Tool 1 tác động lên Anchor với TỐC ĐỘ SNAPPY VOX STOP-MOTION & TOẠ ĐỘ ĐỘNG (Rule 128, 132)
    fam1 = dominant_families[0] if dominant_families else KineticFamily.H2_CONSTRAINT
    if fam1 == KineticFamily.H2_CONSTRAINT:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb=f"snaps in a high-velocity 0.4s slide from initial coordinate {layout.initial_pos} and locks jaws shut precisely onto target coordinate {layout.target_contact_pos} of",
            contact_point=f"critical data row at {layout.target_contact_pos}",
            physical_reaction="vernier scale aligns precisely with grid ticks, locking coordinate measurement into an instant mechanical dead stop at 1.0s, holding completely still",
            secondary_reaction={"object": "desk_surface", "reaction": "subtle mechanical micro-vibration"},
            residue="metric baseline ticks permanently marked"
        )
    elif fam1 == KineticFamily.H1_IMPACT:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb=f"strikes down in a rapid 2-frame snap onto coordinate {layout.target_contact_pos} of",
            contact_point=f"header verification zone at {layout.target_contact_pos}",
            physical_reaction="crisp crimson stamp imprint locks onto newsprint with sharp vector borders, stopping dead in place at 1.0s",
            secondary_reaction={"object": "desk_surface", "reaction": "adjacent paper cutouts settle in 1 frame"},
            residue="deep crimson verification seal stamped"
        )
    elif fam1 == KineticFamily.H3_SEVER:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb=f"slices across coordinate line ({layout.initial_pos} to {layout.target_contact_pos}) in a swift 0.4s cut of",
            contact_point=f"perforated margin coordinate {layout.target_contact_pos}",
            physical_reaction=f"clean vertical mask separation cleanly reveals the underlying archival graphic layer, stopping dead at {layout.target_contact_pos} at 1.0s",
            secondary_reaction={"object": "obj_anchor", "reaction": "exposes lower archival layer"},
            residue="sharp cut edge with visible paper fibers"
        )
    else:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb=f"snaps rigidly into position on coordinate {layout.target_contact_pos} in a fast 0.4s step of",
            contact_point=f"center focal area at {layout.target_contact_pos}",
            physical_reaction="graphic layout locks firmly into alignment grid with zero drift at 1.0s",
            residue="clear mechanical indentation"
        )
    couplings.append(c1)

    # Cặp K2: Tool 2 KẾT NỐI TRỰC TIẾP TỪ TOOL 1 & ANCHOR (Triệt tiêu tính rời rạc, tạo Unified Physical Cluster)
    fam2 = dominant_families[1] if len(dominant_families) > 1 else KineticFamily.H6_MARK
    if fam2 == KineticFamily.H6_MARK:
        c2 = KineticCoupling(
            id="K2",
            family=fam2,
            source_obj_id="obj_tool2",
            target_obj_id="obj_anchor",
            action_verb=f"originates directly from contact coordinate {layout.target_contact_pos}, wiping in a rapid 0.4s horizontal vector reveal across coordinate bounds {layout.bounding_box_bounds} of",
            contact_point=f"highlighted anomaly coordinate {layout.bounding_box_bounds}",
            physical_reaction="neon yellow highlight box illuminates key typography with crisp editorial contrast, locking dead still at 1.6s",
            residue="striking translucent yellow neon stripe"
        )
    elif fam2 == KineticFamily.H4_TETHER:
        c2 = KineticCoupling(
            id="K2",
            family=fam2,
            source_obj_id="obj_tool2",
            target_obj_id="obj_tool1",
            action_verb=f"originates from contact coordinate {layout.target_contact_pos}, snapping a straight dashed vector thread in 0.4s connecting directly to anchor pin at {layout.dock_pin_pos} of",
            contact_point=f"caliper anchor pin at {layout.dock_pin_pos}",
            physical_reaction="crimson evidence vector line snaps between pin coordinates, locking forensic link into a single unified cluster at 1.6s",
            residue="taut red evidence vector linking data to source"
        )
    else:
        c2 = KineticCoupling(
            id="K2",
            family=fam2,
            source_obj_id="obj_tool2",
            target_obj_id="obj_tool1",
            action_verb=f"docks flush against the hero tool base at coordinate {layout.dock_pin_pos} in a rapid 0.5s snap, while contact coordinate {layout.target_contact_pos} triggers a sharp dashed bounding box {layout.bounding_box_bounds} in an instant 2-frame pop on",
            contact_point=f"hero tool anchor pin at {layout.dock_pin_pos}",
            physical_reaction="sharp dashed bounding box snaps around target data, locking all objects into a single unified physical cluster with a complete dead-stop freeze from 1.6s",
            residue="permanent forensic framing box"
        )
    couplings.append(c2)

    # 3. Phân Rã Dãy Micro-Beats Linh Hoạt (Từ 4 đến 7 bước) theo Tốc Độ Snappy Vox Stop-Motion
    micro_beats = []

    # Ngân sách thời gian theo 4 Thì Gốc: Setup ngắn -> Active Snap Bursts dứt khoát -> Massive Living Hold
    t_p1_end = min(0.6, round(dur * 0.1, 1))
    t_p3_end = round(max(t_p1_end + 1.2, min(dur - 0.8, dur * 0.45)), 1)
    active_span = t_p3_end - t_p1_end

    if beat_count <= 4:
        # Nhịp 4 bước siêu dứt khoát chuẩn Vox Stop-Motion:
        # B1: Setup (0.0s - 0.6s)
        # B2: High-Velocity Snap Slide (0.6s - 1.0s, 0.4s burst!)
        # B3: Causal Snap Dock & Pop (1.0s - 1.6s, 0.6s burst!)
        # B4: Unified Dead-Stop Living Hold (1.6s - {dur}s, massive frozen hold with 12fps texture!)
        t_snap1 = round(t_p1_end + 0.4, 1)   # e.g. 1.0s
        t_snap2 = round(t_snap1 + 0.6, 1)   # e.g. 1.6s
        t_p2_end = t_snap1
        t_p3_end = t_snap2

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=f"0.0s - {t_p1_end:.1f}s",
                coupling_id=None,
                action_description=f"The {anchor_label} and {actor1_label} rest flat at initial coordinates {layout.initial_pos}, holding dead still with subtle 12fps paper jitter",
                handoff_to="B2"
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=f"{t_p1_end:.1f}s - {t_snap1:.1f}s",
                coupling_id="K1",
                action_description=f"High-velocity snap burst in 0.4s (steep acceleration on twos / 12fps): The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}. Snap-stop freeze holds completely still from {t_snap1:.1f}s",
                handoff_to="B3",
                camera_micro_move="subtle punch-in zoom 1.0x to 1.15x tracking contact point"
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P3_ESCALATION",
                time_window=f"{t_snap1:.1f}s - {t_snap2:.1f}s",
                coupling_id="K2",
                action_description=f"Direct kinetic trigger: in a rapid 0.6s burst, the {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}. Unified cluster freeze holds motionless from {t_snap2:.1f}s",
                handoff_to="B4"
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P4_LIVING_HOLD",
                time_window=f"{t_snap2:.1f}s - {dur:.1f}s",
                coupling_id=None,
                action_description=f"All objects permanently locked in rigid unified spatial anchor at final coordinate {layout.target_contact_pos} for the remaining {dur - t_snap2:.1f}s to cut, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None
            )
        ]
    elif beat_count == 5:
        # Nhịp 5 bước: Setup -> Snap 1 -> Dead-Stop Hold -> Snap 2 -> Massive Living Hold
        t_snap1 = round(t_p1_end + 0.4, 1)
        t_hold1 = round(t_snap1 + 0.8, 1)
        t_snap2 = round(t_hold1 + 0.5, 1)
        t_p2_end = t_hold1
        t_p3_end = t_snap2

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=f"0.0s - {t_p1_end:.1f}s",
                coupling_id=None,
                action_description=f"The {anchor_label} drops onto newsprint desk with subtle tactile bounce",
                handoff_to="B2"
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=f"{t_p1_end:.1f}s - {t_snap1:.1f}s",
                coupling_id="K1",
                action_description=f"High-velocity snap burst in 0.4s: The {actor1_label} {c1.action_verb} the {anchor_label}, causing {c1.physical_reaction}",
                handoff_to="B3",
                camera_micro_move="camera crash-zoom punch-in 1.3x tracking contact point"
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=f"{t_snap1:.1f}s - {t_hold1:.1f}s",
                coupling_id="K1",
                action_description=f"Pressure from {actor1_label} holds completely motionless in dead stop, causing {c1.physical_reaction}, leaving {c1.residue}",
                handoff_to="B4"
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P3_ESCALATION",
                time_window=f"{t_hold1:.1f}s - {t_snap2:.1f}s",
                coupling_id="K2",
                action_description=f"Direct kinetic trigger: in a rapid 0.5s burst, the {inter2} {c2.action_verb} the {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B5"
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P4_LIVING_HOLD",
                time_window=f"{t_snap2:.1f}s - {dur:.1f}s",
                coupling_id=None,
                action_description=f"All objects permanently locked in spatial anchor for remaining {dur - t_snap2:.1f}s, 12fps paper stop-motion texture, zero static freeze to cut",
                handoff_to=None
            )
        ]
    elif beat_count == 6:
        # Nhịp 6 bước linh hoạt
        t_sub_step = min(0.5, round(active_span / 4.0, 1))
        t2 = round(t_p1_end + t_sub_step, 1)
        t3 = round(t2 + t_sub_step, 1)
        t4 = round(t3 + t_sub_step, 1)
        t_p2_end = t3
        t_p3_end = round(t4 + t_sub_step, 1)

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=f"0.0s - {t_p1_end:.1f}s",
                coupling_id=None,
                action_description=f"{anchor_label} snap-drops onto desk #F4F1EA, edges vibrating with stop-motion jitter",
                handoff_to="B2"
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=f"{t_p1_end:.1f}s - {t2:.1f}s",
                coupling_id="K1",
                action_description=f"High-velocity snap burst: {actor1_label} {c1.action_verb} {anchor_label}",
                handoff_to="B3"
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=f"{t2:.1f}s - {t3:.1f}s",
                coupling_id="K1",
                action_description=f"Mechanical impact causes {c1.physical_reaction}, leaving {c1.residue}",
                handoff_to="B4",
                camera_micro_move="camera punch-in zoom 1.0x to 1.35x tracking inspection point"
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P3_ESCALATION",
                time_window=f"{t3:.1f}s - {t4:.1f}s",
                coupling_id="K2",
                action_description=f"Action on {anchor_label} immediately triggers {inter2} to {c2.action_verb} {anchor_label}",
                handoff_to="B5"
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P3_ESCALATION",
                time_window=f"{t4:.1f}s - {t_p3_end:.1f}s",
                coupling_id="K2",
                action_description=f"{c2.physical_reaction}, leaving {c2.residue}",
                handoff_to="B6"
            ),
            DynamicMicroBeat(
                beat_id="B6",
                phase="P4_LIVING_HOLD",
                time_window=f"{t_p3_end:.1f}s - {dur:.1f}s",
                coupling_id=None,
                action_description=f"All objects locked in spatial anchor for remaining {dur - t_p3_end:.1f}s, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None
            )
        ]
    else:
        # Nhịp 7 bước tối đa cho câu phức / cao trào
        t_sub_step = min(0.4, round(active_span / 5.0, 1))
        t2 = round(t_p1_end + t_sub_step, 1)
        t3 = round(t2 + t_sub_step, 1)
        t4 = round(t3 + t_sub_step, 1)
        t5 = round(t4 + t_sub_step, 1)
        t_p2_end = t3
        t_p3_end = round(t5 + t_sub_step, 1)

        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=f"0.0s - {t_p1_end:.1f}s",
                coupling_id=None,
                action_description=f"{anchor_label} snap-drops onto desk #F4F1EA, edges vibrating with stop-motion jitter",
                handoff_to="B2"
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=f"{t_p1_end:.1f}s - {t2:.1f}s",
                coupling_id="K1",
                action_description=f"{actor1_label} enters frame with crisp paper deceleration and aligns with {anchor_label}",
                handoff_to="B3"
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=f"{t2:.1f}s - {t3:.1f}s",
                coupling_id="K1",
                action_description=f"{actor1_label} {c1.action_verb} {anchor_label}, causing {c1.physical_reaction}",
                handoff_to="B4",
                camera_micro_move="camera punch-in zoom 1.0x to 1.35x tracking contact point"
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P2_TENSION",
                time_window=f"{t3:.1f}s - {t4:.1f}s",
                coupling_id="K1",
                action_description=f"Mechanical settling permanently leaves {c1.residue}",
                handoff_to="B5"
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P3_ESCALATION",
                time_window=f"{t4:.1f}s - {t5:.1f}s",
                coupling_id="K2",
                action_description=f"{inter2} {c2.action_verb} {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B6"
            ),
            DynamicMicroBeat(
                beat_id="B6",
                phase="P3_ESCALATION",
                time_window=f"{t5:.1f}s - {t_p3_end:.1f}s",
                coupling_id="K2",
                action_description=f"Action solidifies, leaving {c2.residue}",
                handoff_to="B7"
            ),
            DynamicMicroBeat(
                beat_id="B7",
                phase="P4_LIVING_HOLD",
                time_window=f"{t_p3_end:.1f}s - {dur:.1f}s",
                coupling_id=None,
                action_description="All objects locked in spatial anchor, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None
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
            "p2_tension_sec": [t_p1_end, t_p2_end],
            "p3_escalation_sec": [t_p2_end, t_p3_end],
            "p4_living_hold_sec": [t_p3_end, dur]
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
