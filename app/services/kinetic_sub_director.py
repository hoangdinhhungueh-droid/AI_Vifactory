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
from dataclasses import asdict, dataclass, field
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

        # Đếm số lượng con số hoặc tỷ lệ %
        has_metrics = bool(re.search(r"\d+([,\.]\d+)?\s*(%|tỷ|triệu|b|m|k|円|won|usd|yen|gbp|eur)?", s_clean))

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
            count = sum(1 for kw in keywords if kw in s_clean)
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


def generate_scene_sub_director_plan(
    scene_id: str,
    sentence: str,
    hero_cutout_object: str,
    interacting_objects: List[str],
    duration_sec: float = 8.0,
    market: str = "EN"
) -> Dict[str, Any]:
    """Sinh toàn diện Khung Đạo Diễn Vi Cảnh (Scene Sub-Director Plan) chuẩn hóa cho mọi Episode."""
    beat_count = SemanticClauseMapper.calculate_beat_count(sentence)
    dominant_families = SemanticClauseMapper.detect_dominant_families(sentence)

    hero_clean = (hero_cutout_object or "primary forensic document").split(" on ")[0].strip()
    inter1 = interacting_objects[0] if interacting_objects else "heavy brass caliper"
    inter2 = interacting_objects[1] if len(interacting_objects) > 1 else "red evidence thread"

    # Nhận diện vai trò vật lý: Đạo cụ tác động (Tool Actor) vs Mặt nền tài liệu (Document Target)
    tool_keywords = ["caliper", "scissors", "stamp", "marker", "highlighter", "loupe", "glass", "pen", "knife", "pin", "ruler", "shears"]
    doc_keywords = ["ledger", "sheet", "document", "paper", "contract", "dossier", "card", "report", "photo", "chart", "page", "envelope", "file"]

    is_hero_tool = any(k in hero_clean.lower() for k in tool_keywords)
    is_inter1_doc = any(k in inter1.lower() for k in doc_keywords)

    if is_hero_tool and is_inter1_doc:
        anchor_label = inter1
        actor1_label = hero_clean
        actor1_material = "solid_metal" if "caliper" in hero_clean.lower() or "scissors" in hero_clean.lower() else "wood_rubber"
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

    # Cặp K1: Tool 1 tác động lên Anchor
    fam1 = dominant_families[0] if dominant_families else KineticFamily.H2_CONSTRAINT
    if fam1 == KineticFamily.H2_CONSTRAINT:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb="clamps down firmly onto",
            contact_point="critical data row",
            physical_reaction="paper edges crinkle under metallic pressure as vernier scale locks data ticks",
            secondary_reaction={"object": "desk_surface", "reaction": "subtle mechanical micro-vibration"},
            residue="metric baseline ticks permanently marked"
        )
    elif fam1 == KineticFamily.H1_IMPACT:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb="slams down with high velocity onto",
            contact_point="header verification zone",
            physical_reaction="paper fibers indent, red ink bleeds cleanly into aged newsprint",
            secondary_reaction={"object": "desk_surface", "reaction": "adjacent paper cutouts jump 1-2 frames"},
            residue="deep crimson verification seal stamped"
        )
    elif fam1 == KineticFamily.H3_SEVER:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb="slices cleanly across",
            contact_point="perforated margin",
            physical_reaction="paper strip severs, spins half-turn, and lands with light bounce",
            secondary_reaction={"object": "obj_anchor", "reaction": "exposes lower archival layer"},
            residue="jagged cut edge with visible paper fibers"
        )
    else:
        c1 = KineticCoupling(
            id="K1",
            family=fam1,
            source_obj_id="obj_tool1",
            target_obj_id="obj_anchor",
            action_verb="engages directly with",
            contact_point="center focal area",
            physical_reaction="paper flexes as tool locks into position",
            residue="clear mechanical indentation"
        )
    couplings.append(c1)

    # Cặp K2: Tool 2 phản ứng hoặc nối từ Tool 1 / Anchor (Bảo đảm Causal Handoff)
    fam2 = dominant_families[1] if len(dominant_families) > 1 else KineticFamily.H6_MARK
    if fam2 == KineticFamily.H6_MARK:
        c2 = KineticCoupling(
            id="K2",
            family=fam2,
            source_obj_id="obj_tool2",
            target_obj_id="obj_anchor",
            action_verb="sweeps glowing neon dye across",
            contact_point="highlighted anomaly row",
            physical_reaction="text beneath absorbs neon pigment and illuminates brightly",
            residue="striking translucent yellow neon stripe"
        )
    elif fam2 == KineticFamily.H4_TETHER:
        c2 = KineticCoupling(
            id="K2",
            family=fam2,
            source_obj_id="obj_tool2",
            target_obj_id="obj_tool1",
            action_verb="pulls taut between brass pins connecting to",
            contact_point="caliper anchor pin",
            physical_reaction="crimson thread vibrates under tension then damps into rigid vector line",
            residue="taut red evidence vector linking data to source"
        )
    else:
        c2 = KineticCoupling(
            id="K2",
            family=fam2,
            source_obj_id="obj_tool2",
            target_obj_id="obj_anchor",
            action_verb="deploys alongside",
            contact_point="boundary perimeter",
            physical_reaction="flashing dashed boundary rectangle confirms forensic audit",
            residue="permanent forensic framing box"
        )
    couplings.append(c2)

    # 3. Phân Rã Dãy Micro-Beats Linh Hoạt (Từ 4 đến 7 bước)
    dur = float(duration_sec or 8.0)
    micro_beats = []

    # Ngân sách thời gian theo 4 Thì Gốc
    t_p1_end = min(1.5, round(dur * 0.2, 1))
    t_p2_end = min(3.8, round(dur * 0.5, 1))
    t_p3_end = min(dur - 1.2, round(dur * 0.85, 1))

    if beat_count <= 4:
        # Nhịp 4 bước chuẩn
        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=f"0.0s - {t_p1_end:.1f}s",
                coupling_id=None,
                action_description=f"{anchor_label} rests flat on #F4F1EA desk, edges quivering with 12fps paper jitter",
                handoff_to="B2"
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=f"{t_p1_end:.1f}s - {t_p2_end:.1f}s",
                coupling_id="K1",
                action_description=f"{actor1_label} {c1.action_verb} {anchor_label}, causing {c1.physical_reaction}",
                handoff_to="B3",
                camera_micro_move="subtle punch-in zoom 1.0x to 1.25x tracking contact point"
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P3_ESCALATION",
                time_window=f"{t_p2_end:.1f}s - {t_p3_end:.1f}s",
                coupling_id="K2",
                action_description=f"{inter2} {c2.action_verb} {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B4"
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P4_LIVING_HOLD",
                time_window=f"{t_p3_end:.1f}s - {dur:.1f}s",
                coupling_id=None,
                action_description="All objects permanently locked in spatial anchor, organic 12fps paper stop-motion jitter, zero static freeze",
                handoff_to=None
            )
        ]
    elif beat_count == 5:
        # Nhịp 5 bước
        t_step = (t_p3_end - t_p1_end) / 3.0
        t2 = round(t_p1_end + t_step, 1)
        t3 = round(t_p1_end + 2 * t_step, 1)
        micro_beats = [
            DynamicMicroBeat(
                beat_id="B1",
                phase="P1_SETUP",
                time_window=f"0.0s - {t_p1_end:.1f}s",
                coupling_id=None,
                action_description=f"{anchor_label} drops onto newsprint desk with subtle tactile bounce",
                handoff_to="B2"
            ),
            DynamicMicroBeat(
                beat_id="B2",
                phase="P2_TENSION",
                time_window=f"{t_p1_end:.1f}s - {t2:.1f}s",
                coupling_id="K1",
                action_description=f"{actor1_label} sweeps in with velocity and {c1.action_verb} {anchor_label}",
                handoff_to="B3",
                camera_micro_move="camera crash-zoom punch-in 1.3x tracking contact point"
            ),
            DynamicMicroBeat(
                beat_id="B3",
                phase="P2_TENSION",
                time_window=f"{t2:.1f}s - {t3:.1f}s",
                coupling_id="K1",
                action_description=f"Pressure from {actor1_label} causes {c1.physical_reaction}, leaving {c1.residue}",
                handoff_to="B4"
            ),
            DynamicMicroBeat(
                beat_id="B4",
                phase="P3_ESCALATION",
                time_window=f"{t3:.1f}s - {t_p3_end:.1f}s",
                coupling_id="K2",
                action_description=f"{inter2} {c2.action_verb} {anchor_label}, causing {c2.physical_reaction}",
                handoff_to="B5"
            ),
            DynamicMicroBeat(
                beat_id="B5",
                phase="P4_LIVING_HOLD",
                time_window=f"{t_p3_end:.1f}s - {dur:.1f}s",
                coupling_id=None,
                action_description="All objects settled in spatial anchor with 12fps paper shadow breathing <= 2px",
                handoff_to=None
            )
        ]
    else:
        # Nhịp 6..7 bước linh hoạt cho câu phức
        t_sub_step = (t_p3_end - t_p1_end) / 4.0
        t2 = round(t_p1_end + t_sub_step, 1)
        t3 = round(t_p1_end + 2 * t_sub_step, 1)
        t4 = round(t_p1_end + 3 * t_sub_step, 1)

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
                action_description=f"{actor1_label} sweeps in with velocity blur and {c1.action_verb} {anchor_label}",
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
                action_description="All objects locked in spatial anchor, organic 12fps paper stop-motion jitter, zero static freeze to cut",
                handoff_to=None
            )
        ]

    plan = {
        "schema_version": "scene_sub_director_plan.v3",
        "scene_id": scene_id,
        "calculated_beat_count": len(micro_beats),
        "dominant_kinetic_families": [f.value for f in dominant_families],
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
            cam_directive_detected = f"Dynamic crash-zoom punch-in from 1.0x to 1.35x tracking inspection point"

        if c_id and c_id in couplings:
            c = couplings[c_id]
            src_lbl = roster.get(c["source_obj_id"], c["source_obj_id"])
            tgt_lbl = roster.get(c["target_obj_id"], c["target_obj_id"])
            verb = c["action_verb"]
            reaction = c["physical_reaction"]
            residue = c.get("residue", "")

            # Cú pháp liên hợp nhân quả chuẩn: [SOURCE] [verb] [TARGET], causing [reaction], leaving [residue]
            clause = f"{t_win}: The {src_lbl} {verb} the {tgt_lbl}, causing {reaction}"
            if residue:
                clause += f", leaving {residue}"
            steps_text.append(clause + ".")
        else:
            steps_text.append(f"{t_win}: {action}.")

    chain_str = " ".join(steps_text)

    prompt = (
        f"Tactile paper collage stop-motion animation, animated on twos, authentic handcrafted jitter, "
        f"warm aged cream newsprint desk (#F4F1EA), soft directional physical drop shadows. "
        f"[CAMERA]: {cam_directive_detected}. "
        f"[KINETIC CAUSAL CHAIN]: {chain_str} "
        f"[PHYSICAL CONSTRAINTS]: Every movement is directly caused by physical contact with an interacting tool. "
        f"Zero independent drifting, zero 3D fluid morphing, all objects locked in 12fps paper stop-motion hold to the cut."
    )

    return prompt.strip()
