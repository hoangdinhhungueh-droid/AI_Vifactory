"""
Scene Layout Director - Dynamic Archetype & Kinetic Composition Engine (FT-206)
Part of Canonical Pipeline 2.0 & Vox Engine v3.

Triệt tiêu 100% căn bệnh "1 màu rập khuôn vị trí & hiệu ứng slide vô tri":
1. Mỗi Scene sở hữu một Bố cục Không gian Bất đối xứng (Asymmetric Spatial Blueprint).
2. Hiệu ứng chuẩn Vox: Rơi/đập từ trục Z (paper_slap / tactile_drop), dập mộc (stamp_slam), ghim đồng (pin_tack), cấm hoàn toàn trượt ngang kiểu slide PowerPoint.
3. Các mối nối (yarns & dimension lines) mang đầy đủ nhãn bằng chứng nghiệp vụ (Forensic Evidence Labels & Calipers).
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class LayoutArchetype(str, Enum):
    """5 Họ Bố Cục Không Gian Bất Đối Xứng."""
    CENTRAL_DOSSIER = "central_dossier"     # Hồ sơ trung tâm chiếm trọng tâm, công cụ soi/đo góc đối lập
    NETWORK_SPIDER = "network_spider"       # Mẹ-con phân nhánh, chỉ đỏ tỏa tia đa hướng
    CASCADING_PILE = "cascading_pile"       # Chồng chất tài liệu/cửa hàng dồn toa, thước kẹp đo độ rủi ro
    TIMELINE_STRIP = "timeline_strip"       # Trục thời gian ngang, hiện vật lịch sử chuyển sang dấu mộc
    SPLIT_COMPARISON = "split_comparison"   # Đối kháng 2 cực (A vs B)


class DynamicSpatialAnchor(BaseModel):
    """Tọa độ không gian độc lập cho từng thành phần trên khung 1920x1080 (tỷ lệ 0-100%)."""
    x_pct: float = Field(..., ge=0.0, le=100.0)
    y_pct: float = Field(..., ge=0.0, le=100.0)
    width_pct: float = Field(..., ge=5.0, le=80.0)
    rotation_deg: float = Field(default=0.0, ge=-35.0, le=35.0)
    entrance_type: str = Field(default="paper_slap")  # paper_slap, delicate_tack, stamp_slam, drop
    delay_sec: float = Field(default=0.5, ge=0.0)
    has_pin: bool = True
    has_tape: bool = False
    has_marker_highlight: bool = False
    highlight_text: Optional[str] = None


class SceneLayoutBlueprint(BaseModel):
    """Bản thiết kế không gian & động học riêng biệt cho từng Scene."""
    scene_id: str
    archetype: LayoutArchetype
    hero_anchor: DynamicSpatialAnchor
    tool_anchor: DynamicSpatialAnchor
    supporting_anchors: List[Dict[str, Any]] = Field(default_factory=list)
    connector_topology: str  # radial_star, perimeter_box, tension_loop, timeline_axis
    yarn_paths: List[Dict[str, Any]] = Field(default_factory=list)
    dimension_lines: List[Dict[str, Any]] = Field(default_factory=list)
    stamp_anchor: Dict[str, Any] = Field(default_factory=dict)
    camera_movement: str = "locked"


def assign_scene_layout_blueprint(
    scene_id: str,
    scene_index: int,
    archetype_override: Optional[LayoutArchetype] = None
) -> SceneLayoutBlueprint:
    """
    Phân bổ bố cục không gian và động học xúc giác riêng biệt chuẩn Vox Documentary.
    """
    archetype_cycle = [
        LayoutArchetype.CENTRAL_DOSSIER,
        LayoutArchetype.NETWORK_SPIDER,
        LayoutArchetype.CASCADING_PILE,
        LayoutArchetype.TIMELINE_STRIP,
    ]
    archetype = archetype_override or archetype_cycle[scene_index % len(archetype_cycle)]

    if archetype == LayoutArchetype.CENTRAL_DOSSIER:
        # SCENE 01: Hồ sơ pháp lý trung tâm (ASIC Notice), máy đếm odometer góc trên trái
        hero = DynamicSpatialAnchor(
            x_pct=48.0,
            y_pct=48.0,
            width_pct=44.0,
            rotation_deg=-1.5,
            entrance_type="paper_slap",  # Đập xuống bàn từ trục Z
            delay_sec=0.5,
            has_pin=True,
            has_marker_highlight=True,
            highlight_text="OFFICIAL ASIC NOTICE"
        )
        tool = DynamicSpatialAnchor(
            x_pct=20.0,
            y_pct=24.0,
            width_pct=28.0,
            rotation_deg=2.5,
            entrance_type="delicate_tack",
            delay_sec=1.4,
            has_pin=True
        )
        supporting = [
            {
                "id": "cutout_excerpt_legal",
                "variant": "excerpt",
                "badge": "STATUTORY CLAUSE",
                "label": "CORPORATIONS ACT 2001 // SEC. 436A",
                "subLabel": "APPOINTMENT OF EXTERNAL ADMINISTRATORS",
                "x_pct": 18.0,
                "y_pct": 70.0,
                "width_pct": 22.0,
                "rotation_deg": -3.0,
                "entrance_type": "paper_slap",
                "delay_sec": 1.2,
                "has_tape": True,
                "has_marker_highlight": True,
                "highlight_text": "SEC. 436A"
            },
            {
                "id": "cutout_sticky_notice",
                "variant": "sticky_note",
                "badge": "AUDIT NOTE",
                "label": "GENERAL PANTS CO. PTY LTD",
                "subLabel": "ENTERED ADMINISTRATION: 11/2026",
                "x_pct": 78.0,
                "y_pct": 24.0,
                "width_pct": 22.0,
                "rotation_deg": 3.5,
                "entrance_type": "delicate_tack",
                "delay_sec": 2.0,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "NOVEMBER 2026"
            },
            {
                "id": "cutout_stat_metric",
                "variant": "card",
                "badge": "QUANTITATIVE METRIC",
                "label": "STAT HERO // FISCAL YEAR",
                "subLabel": "2026 AUDITED FILING",
                "x_pct": 78.0,
                "y_pct": 72.0,
                "width_pct": 22.0,
                "rotation_deg": -1.0,
                "entrance_type": "paper_slap",
                "delay_sec": 2.8,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "2026"
            }
        ]
        # Topology: Perimeter Box kèm Nhãn Bằng Chứng Pháp Y cụ thể
        yarn_paths = [
            {"fromX": 22, "fromY": 34, "toX": 35, "toY": 42, "color": "#D62E1F", "delaySec": 1.6, "label": "STATUTORY AUDIT #00789"},
            {"fromX": 35, "fromY": 54, "toX": 20, "toY": 68, "color": "#D62E1F", "delaySec": 2.2, "label": "SEC 436A MANDATE"},
            {"fromX": 58, "fromY": 42, "toX": 74, "toY": 26, "color": "#D62E1F", "delaySec": 2.6, "label": "INSOLVENCY DISCLOSURE"},
            {"fromX": 76, "fromY": 32, "toX": 78, "toY": 66, "color": "#D62E1F", "delaySec": 3.4, "label": "AUDIT TIMELINE // 2026"}
        ]
        dimension_lines = []
        stamp = {
            "text": "ASIC NOTICE // NOV 2026",
            "color": "#D62E1F",
            "position": "bottom_right"
        }
        connector_top = "perimeter_box"

    elif archetype == LayoutArchetype.NETWORK_SPIDER:
        # SCENE 02: Hồ sơ mẹ bên trái, 3 thực thể con tỏa tia sang phải, bộ điều tốc ở đáy giữa
        hero = DynamicSpatialAnchor(
            x_pct=24.0,
            y_pct=46.0,
            width_pct=34.0,
            rotation_deg=-2.0,
            entrance_type="paper_slap",
            delay_sec=0.5,
            has_pin=True,
            has_marker_highlight=True,
            highlight_text="PARENT COMPANY // HOLDINGS"
        )
        tool = DynamicSpatialAnchor(
            x_pct=52.0,
            y_pct=78.0,
            width_pct=32.0,
            rotation_deg=0.5,
            entrance_type="delicate_tack",
            delay_sec=3.0,
            has_pin=True
        )
        supporting = [
            {
                "id": "cutout_stat_subsidiaries",
                "variant": "card",
                "badge": "QUANTITATIVE METRIC",
                "label": "STAT HERO // 9 RETAIL",
                "subLabel": "OPERATING SUBSIDIARIES",
                "x_pct": 78.0,
                "y_pct": 22.0,
                "width_pct": 24.0,
                "rotation_deg": -1.5,
                "entrance_type": "paper_slap",
                "delay_sec": 1.2,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "9 RETAIL UNITS"
            },
            {
                "id": "cutout_sticky_capital",
                "variant": "sticky_note",
                "badge": "CAPITAL FLOW MEMO",
                "label": "INTERCOMPANY CLAIMS REGISTER",
                "subLabel": "CROSS-GUARANTEE EXPOSURE: AUDIT VERIFIED",
                "x_pct": 82.0,
                "y_pct": 50.0,
                "width_pct": 22.0,
                "rotation_deg": 2.0,
                "entrance_type": "delicate_tack",
                "delay_sec": 1.8,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "CROSS-GUARANTEE"
            },
            {
                "id": "cutout_subsidiary_reg",
                "variant": "excerpt",
                "badge": "ASIC SUBSIDIARY REGISTER",
                "label": "RETAIL ENTITIES UNDER ADMINISTRATION",
                "subLabel": "9 OPERATING DIVISIONS AUDITED",
                "x_pct": 80.0,
                "y_pct": 78.0,
                "width_pct": 24.0,
                "rotation_deg": -2.0,
                "entrance_type": "paper_slap",
                "delay_sec": 2.4,
                "has_tape": True,
                "has_marker_highlight": True,
                "highlight_text": "9 DIVISIONS"
            }
        ]
        # Topology: Radial Star với Nhãn Bằng Chứng thể hiện dòng tiền và quyền kiểm soát
        yarn_paths = [
            {"fromX": 30, "fromY": 40, "toX": 74, "toY": 24, "color": "#D62E1F", "delaySec": 1.4, "label": "100% SUBSIDIARY CONTROL"},
            {"fromX": 32, "fromY": 48, "toX": 78, "toY": 50, "color": "#D62E1F", "delaySec": 2.0, "label": "CROSS-GUARANTEE EXPOSURE"},
            {"fromX": 30, "fromY": 56, "toX": 76, "toY": 76, "color": "#D62E1F", "delaySec": 2.6, "label": "RETAIL TRADING ENTITIES"},
            {"fromX": 32, "fromY": 62, "toX": 48, "toY": 74, "color": "#D62E1F", "delaySec": 3.2, "label": "CAPITAL REGULATION DRAIN"}
        ]
        dimension_lines = []
        stamp = {
            "text": "PARENT ENTITY // AUDIT DATA",
            "color": "#D62E1F",
            "position": "bottom_right"
        }
        connector_top = "radial_star"

    elif archetype == LayoutArchetype.CASCADING_PILE:
        # SCENE 03: Đống cửa hàng dồn toa góc trái dưới, thẻ số liệu 500 JOBS góc trên giữa, thước kẹp đo độ rủi ro
        hero = DynamicSpatialAnchor(
            x_pct=36.0,
            y_pct=58.0,
            width_pct=46.0,
            rotation_deg=2.0,
            entrance_type="paper_slap",
            delay_sec=0.5,
            has_pin=True,
            has_marker_highlight=True,
            highlight_text="35 RETAIL STOREFRONTS"
        )
        tool = DynamicSpatialAnchor(
            x_pct=78.0,
            y_pct=30.0,
            width_pct=32.0,
            rotation_deg=-2.5,
            entrance_type="delicate_tack",
            delay_sec=1.6,
            has_pin=True
        )
        supporting = [
            {
                "id": "cutout_stat_jobs",
                "variant": "card",
                "badge": "AT-RISK METRIC",
                "label": "STAT HERO // RETAIL FOOTPRINT",
                "subLabel": "AUSTRALIA & NEW ZEALAND UNITS",
                "x_pct": 42.0,
                "y_pct": 18.0,
                "width_pct": 26.0,
                "rotation_deg": -1.0,
                "entrance_type": "drop",
                "delay_sec": 1.0,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "500 JOBS"
            },
            {
                "id": "cutout_sticky_stores",
                "variant": "sticky_note",
                "badge": "STORE AUDIT MEMO",
                "label": "GENERAL PANTS NETWORK",
                "subLabel": "35 LEASED PREMISES UNDER THREAT",
                "x_pct": 18.0,
                "y_pct": 32.0,
                "width_pct": 22.0,
                "rotation_deg": 4.0,
                "entrance_type": "delicate_tack",
                "delay_sec": 2.0,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "35 STORES"
            },
            {
                "id": "cutout_excerpt_creditors",
                "variant": "excerpt",
                "badge": "ASIC LIQUIDATION NOTICE",
                "label": "UNSECURED CREDITORS CLAIM",
                "subLabel": "TENANCY LEASES AUDITED: NOV 2026",
                "x_pct": 76.0,
                "y_pct": 74.0,
                "width_pct": 26.0,
                "rotation_deg": -2.0,
                "entrance_type": "paper_slap",
                "delay_sec": 2.8,
                "has_tape": True,
                "has_marker_highlight": True,
                "highlight_text": "CREDITOR CLAIMS"
            }
        ]
        # Thước kẹp Dimension Line đo độ phủ 35 cửa hàng
        dimension_lines = [
            {
                "startX": 18,
                "endX": 60,
                "y": 75,
                "label": "35 RETAIL DOORS UNDER AUDIT",
                "color": "#DC2626",
                "delaySec": 2.4,
                "rotation": 0
            }
        ]
        # Topology: Tension Loop với Nhãn Bằng Chứng
        yarn_paths = [
            {"fromX": 40, "fromY": 24, "toX": 34, "toY": 50, "color": "#D62E1F", "delaySec": 1.4, "label": "500 WORKERS TERMINATED"},
            {"fromX": 38, "fromY": 24, "toX": 22, "toY": 30, "color": "#D62E1F", "delaySec": 2.2, "label": "35 LEASEHOLD SITES"},
            {"fromX": 44, "fromY": 64, "toX": 72, "toY": 72, "color": "#D62E1F", "delaySec": 3.0, "label": "UNSECURED LEASE CLAIMS"},
            {"fromX": 76, "fromY": 68, "toX": 76, "toY": 42, "color": "#D62E1F", "delaySec": 3.6, "label": "LIQUIDATION DEBT AUDIT"}
        ]
        stamp = {
            "text": "STORE NETWORK // AUDIT RISK",
            "color": "#D62E1F",
            "position": "bottom_right"
        }
        connector_top = "tension_loop"

    else:
        # SCENE 04: Trục thời gian nằm ngang (Timeline Strip): Vải jean 1972 bên trái -> Dòng thời gian -> Dấu mộc dập mạnh bên phải
        hero = DynamicSpatialAnchor(
            x_pct=24.0,
            y_pct=44.0,
            width_pct=34.0,
            rotation_deg=-3.0,
            entrance_type="paper_slap",
            delay_sec=0.5,
            has_pin=True,
            has_marker_highlight=True,
            highlight_text="ESTABLISHED 1972"
        )
        tool = DynamicSpatialAnchor(
            x_pct=82.0,
            y_pct=62.0,
            width_pct=28.0,
            rotation_deg=1.0,
            entrance_type="stamp_slam",  # Con dấu mộc xoay tay dập mạnh
            delay_sec=3.0,
            has_pin=True
        )
        supporting = [
            {
                "id": "cutout_stat_heritage",
                "variant": "card",
                "badge": "HERITAGE RECORD",
                "label": "STAT HERO // FOUNDING YEAR",
                "subLabel": "50 YEARS OF AUSTRALIAN RETAIL",
                "x_pct": 52.0,
                "y_pct": 24.0,
                "width_pct": 24.0,
                "rotation_deg": -1.0,
                "entrance_type": "delicate_tack",
                "delay_sec": 1.2,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "EST. 1972"
            },
            {
                "id": "cutout_excerpt_ragtrader",
                "variant": "excerpt",
                "badge": "INDUSTRY DISCLOSURE",
                "label": "RAGTRADER AUSTRALIA // 1972-2026",
                "subLabel": "YOUTH APPAREL & DENIM CONCESSIONS",
                "x_pct": 22.0,
                "y_pct": 78.0,
                "width_pct": 24.0,
                "rotation_deg": 2.5,
                "entrance_type": "paper_slap",
                "delay_sec": 1.8,
                "has_tape": True,
                "has_marker_highlight": True,
                "highlight_text": "RAGTRADER 1972"
            },
            {
                "id": "cutout_sticky_flagship",
                "variant": "sticky_note",
                "badge": "ARCHIVE NOTE",
                "label": "RAGTRADER HISTORICAL FILE",
                "subLabel": "FLAGSHIP SYDNEY & MELBOURNE DOORS",
                "x_pct": 58.0,
                "y_pct": 68.0,
                "width_pct": 24.0,
                "rotation_deg": -2.0,
                "entrance_type": "delicate_tack",
                "delay_sec": 2.4,
                "has_pin": True,
                "has_marker_highlight": True,
                "highlight_text": "FLAGSHIP DOORS"
            }
        ]
        # Thước kẹp Dimension Line đo chu kỳ 54 năm lịch sử
        dimension_lines = [
            {
                "startX": 24,
                "endX": 82,
                "y": 38,
                "label": "54-YEAR RETAIL LIFESPAN (1972 - 2026)",
                "color": "#DC2626",
                "delaySec": 1.6,
                "rotation": 0
            }
        ]
        # Topology: Timeline Axis với Nhãn Bằng Chứng
        yarn_paths = [
            {"fromX": 26, "fromY": 54, "toX": 22, "toY": 72, "color": "#D62E1F", "delaySec": 1.2, "label": "1972 FOUNDING RECORD"},
            {"fromX": 30, "fromY": 42, "toX": 48, "toY": 26, "color": "#D62E1F", "delaySec": 1.8, "label": "AUSTRALIAN YOUTH ROOTS"},
            {"fromX": 54, "fromY": 30, "toX": 58, "toY": 62, "color": "#D62E1F", "delaySec": 2.6, "label": "SYDNEY & MELBOURNE DOORS"},
            {"fromX": 64, "fromY": 68, "toX": 80, "toY": 64, "color": "#D62E1F", "delaySec": 3.4, "label": "OFFICIAL REGISTRY DOCKET"}
        ]
        stamp = {
            "text": "FOUNDING RECORD // RAGTRADER 1972",
            "color": "#D62E1F",
            "position": "bottom_right"
        }
        connector_top = "timeline_axis"

    return SceneLayoutBlueprint(
        scene_id=scene_id,
        archetype=archetype,
        hero_anchor=hero,
        tool_anchor=tool,
        supporting_anchors=supporting,
        connector_topology=connector_top,
        yarn_paths=yarn_paths,
        dimension_lines=dimension_lines,
        stamp_anchor=stamp,
        camera_movement="locked"
    )
