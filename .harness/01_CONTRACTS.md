# 📜 01_CONTRACTS.md - KHẾ ƯỚC DỮ LIỆU VIDEO FACTORY (SSOT)

> **NGUỒN SỰ THẬT DUY NHẤT CHO PIPELINE S1–S11 & VOX ENGINE V3.**
> Mọi thay đổi về cấu trúc kịch bản, đạo diễn xúc giác, hay render Remotion bắt buộc phải khai báo ở đây.
> Tuân thủ Hiến pháp R118 (Zero-Mock), R128 (Generic Contract), R132 (Decoupled Engine), và R140 (Kinetic Coupling).

---

## 1. STATE MACHINE PIPELINE CHUẨN (CANONICAL PIPELINE 2.0)
```mermaid
stateDiagram-v2
    [*] --> S01_IDEATION : Quét Google Trends RSS live
    S01_IDEATION --> S02_RESEARCH : Trích xuất Grounding Table & Causal Epochs
    S02_RESEARCH --> S03_SCRIPT : Kịch bản 5 Beat Docudrama
    S03_SCRIPT --> S04_CRITIC : Thẩm định kịch bản Hội đồng Critic
    S04_CRITIC --> S05_DIRECTOR : Kế hoạch Đạo diễn Xúc giác H1..H7
    S05_DIRECTOR --> S07_IMAGE_GEN : Sinh Master Sheet & Cắt tách Alpha Layers (FT-201)
    S07_IMAGE_GEN --> S08_VIDEO_GEN : Sinh Omni Tactile Texture Plates (FT-203)
    S08_VIDEO_GEN --> S09_VOICE_TTS : Tạo giọng đọc ElevenLabs + Whisper Timestamps
    S09_VOICE_TTS --> S10_RENDER : Remotion Master Compositor Render MP4 (FT-204)
    S10_RENDER --> S11_QC : Đồng bộ YouTube Chapter & QC Nghiệm thu (FT-205)
    S11_QC --> [*]
```

---

## 2. PYDANTIC SCHEMAS CHUẨN TẮC

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ==============================================================================
# [FT-201] MASTER SHEET ASSET BUNDLE SCHEMA (COMPREHENSIVE 6-IN-1)
# ==============================================================================
class WiringSpec(BaseModel):
    """Khế ước cách đấu nối không gian & động học giữa các object."""
    connector_type: str = Field(..., description="Loại đấu nối: red_yarn, brass_caliper, turned_wood_seal, index_arrow")
    source_anchor: List[int] = Field(..., description="Tọa độ điểm neo nguồn [x, y] trên khung 1920x1080")
    target_anchor: List[int] = Field(..., description="Tọa độ điểm neo đích [x, y] trên khung 1920x1080")
    ingress_axis: str = Field(default="X", description="Trục chuyển động vào (X đơn hướng)")
    ingress_duration_sec: float = Field(default=0.3, le=0.4, description="Thời gian bứt tốc vào sân khấu (<= 0.4s)")
    hold_fps: int = Field(default=12, description="Tốc độ vi rung nhịp thở stop-motion (12fps on twos)")
    snappy_physics: bool = Field(default=True, description="Khóa cứng gia tốc stop-motion giật dứt khoát")

class InformationSpec(BaseModel):
    """Khế ước thông tin nội dung & dữ liệu định lượng."""
    headline: str = Field(..., description="Tiêu đề phân cảnh điều tra")
    stat_hero: str = Field(..., description="Con số định lượng khổng lồ màu đỏ (ví dụ: '500+', '9 RETAIL')")
    stat_label: str = Field(..., description="Nhãn định danh con số định lượng")
    narration: str = Field(..., description="Toàn văn lời đọc voiceover")

class MasterSheetAssetBundle(BaseModel):
    """
    Khế ước Bộ linh kiện Master Sheet toàn diện 6-trong-1 (FT-201).
    BẮT BUỘC có đủ: (1) Image Result, (2) Object Chủ thể, (3) Object Tương tác,
    (4) Thông tin, (5) Transaction Prompt, và (6) Cách đấu nối.
    Thiếu bất kỳ thành phần nào sẽ fail-closed ngay lập tức.
    """
    scene_id: str = Field(..., pattern=r"^SCENE_\d{2}$")
    assembled_anchor_url: str = Field(..., description="1. Image Result mong muốn: Ảnh kết quả tổng thành 2560x1440")
    hero_cutout_url: str = Field(..., description="2. Object Chủ thể: Ảnh tài liệu/nhân vật trên nền trắng #FFFFFF có Alpha")
    interacting_tool_url: str = Field(..., description="3. Object Tương tác: Ảnh thước kẹp/con dấu/chỉ đỏ trên nền trắng #FFFFFF có Alpha")
    stage_backdrop_url: str = Field(default="", description="Ảnh nền sân khấu bàn làm việc (#F4F1EA)")
    stat_card_url: str = Field(default="", description="Ảnh thẻ số liệu đỏ (#D62E1F) hoặc vector chip")
    connector_url: str = Field(default="", description="Ảnh hoặc vector sợi chỉ đỏ / thước kẹp kết nối")
    information_spec: InformationSpec = Field(..., description="4. Thông tin: Headline, stat hero, narration")
    transaction_prompt: str = Field(..., description="5. Transaction Prompt: Prompt tương tác cơ học xúc giác cho Omni/Veo plate")
    wiring_spec: WiringSpec = Field(..., description="6. Cách đấu nối: Tọa độ điểm neo source/target, loại connector, ingress <= 0.4s")
    ingress_direction: str = Field(default="screen_right_to_left", description="Hướng trượt vào duy nhất")
    ingress_duration_sec: float = Field(default=0.3, le=0.4, description="Thời gian bứt tốc vào sân khấu (<= 0.4s)")
    camera_movement: str = Field(default="locked", description="Khóa cứng khung máy tính 1920x1080, cấm zoom/pan")

# ==============================================================================
# [FT-203] OMNI TACTILE TEXTURE PLATE SCHEMA
# ==============================================================================
class OmniTactilePlate(BaseModel):
    """
    Khế ước Clip chất liệu môi trường động sinh từ Omni 1.1 Flash / Veo (FT-203).
    Chỉ dùng làm background plate hoặc overlay thớ giấy sống; CẤM giao layer cho Omni.
    """
    scene_id: str = Field(..., pattern=r"^SCENE_\d{2}$")
    plate_type: str = Field(..., regex=r"^(paper_grain|crt_scanline|archival_fume|desk_surface)$")
    prompt_used: str = Field(..., description="Bắt buộc có tiền tố 'Locked static computer screen frame, no zoom'")
    video_clip_url: str = Field(..., description="Đường dẫn file MP4 1280x720 hoặc 1920x1080")
    duration_sec: float = Field(..., ge=3.0, le=10.0)
    temporal_motion_delta: float = Field(..., ge=0.5, description="Độ biến thiên pixel tối thiểu (chống freeze-frame)")

# ==============================================================================
# [FT-204] REMOTION SCENE RENDER PROPS SCHEMA
# ==============================================================================
class RemotionSceneProp(BaseModel):
    """
    Khế ước Đạo diễn Phân cảnh Remotion kết hợp Master Sheet + Omni Plate (FT-204).
    """
    scene_id: str = Field(...)
    duration_in_frames: int = Field(..., ge=30)
    headline: str = Field(...)
    stat_value: str = Field(...)
    stat_label: str = Field(...)
    background_plate_src: str = Field(..., description="Đường dẫn Omni Tactile Plate hoặc Master Stage")
    hero_src: str = Field(..., description="Hero cutout PNG alpha")
    stat_card_src: str = Field(..., description="Stat card PNG alpha")
    ingress_axis: str = Field(default="X", description="Trục chuyển động trượt vào")
    ingress_duration_sec: float = Field(default=0.3, le=0.4)
    camera_movement: str = Field(default="locked")
    yarn_connections: List[Dict[str, Any]] = Field(default_factory=list, description="Khóa khớp chỉ đỏ nối chủ thể")
    whisper_subtitles: List[Dict[str, Any]] = Field(default_factory=list, description="Phụ đề word-level sync")

# ==============================================================================
# [FT-206] SCENE-SPECIFIC DYNAMIC LAYOUT ARCHETYPES & KINETIC COMPOSITION SCHEMA
# ==============================================================================
from enum import Enum

class LayoutArchetype(str, Enum):
    """
    5 Họ Bố Cục Phân Cảnh Bất Đối Xứng (Triệt tiêu 100% căn bệnh rập khuôn 1 màu):
    1. CENTRAL_DOSSIER: Hồ sơ trung tâm chiếm diện tích lớn, công cụ đo/soi bên trái/phải.
    2. NETWORK_SPIDER: Cấu trúc phân nhánh mẹ-con (spiderweb), chỉ đỏ tỏa tia đa hướng.
    3. CASCADING_PILE: Chồng chất tài liệu/cửa hàng dồn toa, thẻ số liệu khổng lồ góc đối xứng.
    4. TIMELINE_STRIP: Trục thời gian ngang/chéo, hiện vật lịch sử chuyển dịch sang dấu mộc chốt hạ.
    5. SPLIT_COMPARISON: Phân tách đối lập 2 thực thể/hai cán cân đối trọng.
    """
    CENTRAL_DOSSIER = "central_dossier"
    NETWORK_SPIDER = "network_spider"
    CASCADING_PILE = "cascading_pile"
    TIMELINE_STRIP = "timeline_strip"
    SPLIT_COMPARISON = "split_comparison"

class DynamicSpatialAnchor(BaseModel):
    """Tọa độ không gian độc lập cho từng phân cảnh."""
    x_pct: float = Field(..., ge=5.0, le=95.0)
    y_pct: float = Field(..., ge=5.0, le=95.0)
    width_pct: float = Field(..., ge=10.0, le=75.0)
    rotation_deg: float = Field(default=0.0, ge=-25.0, le=25.0)
    entrance_type: str = Field(default="slide_in_deal")
    delay_sec: float = Field(default=0.5, ge=0.0)

class SceneLayoutBlueprint(BaseModel):
    """Bản thiết kế không gian & động học riêng biệt cho từng Scene."""
    scene_id: str = Field(..., pattern=r"^SCENE_\d{2}$")
    archetype: LayoutArchetype = Field(...)
    hero_anchor: DynamicSpatialAnchor = Field(...)
    tool_anchor: DynamicSpatialAnchor = Field(...)
    supporting_anchors: List[DynamicSpatialAnchor] = Field(default_factory=list)
    connector_topology: str = Field(..., description="Kiểu kết nối: radial_star, linear_chain, tension_loop, timeline_axis")
    yarn_paths: List[Dict[str, Any]] = Field(default_factory=list)
    stamp_anchor: Optional[Dict[str, Any]] = None

# ==============================================================================
# [FT-207] CONTINUOUS VOX DESKWORLD & CAMERA JOURNEY SCHEMA (VOX ENGINE V3)
# ==============================================================================
class DeskStationAnchor(BaseModel):
    """Tọa độ trạm khảo sát trên bàn điều tra mở rộng (World Canvas 3840x2160)."""
    station_id: str = Field(..., pattern=r"^STATION_\d{2}$")
    scene_id: str = Field(..., pattern=r"^SCENE_\d{2}$")
    center_x: float = Field(..., description="Tọa độ X trung tâm trạm trên bàn điều tra (pixels)")
    center_y: float = Field(..., description="Tọa độ Y trung tâm trạm trên bàn điều tra (pixels)")
    camera_zoom: float = Field(default=1.0, ge=0.7, le=1.8, description="Hệ số zoom của camera khi đỗ tại trạm")
    dwell_duration_sec: float = Field(..., ge=3.0, description="Thời gian khảo sát tại trạm")
    hero_spec: Dict[str, Any] = Field(..., description="Chủ thể bằng chứng thực tế (loại bỏ 100% chip TSMC và clutter)")
    evidence_nodes: List[Dict[str, Any]] = Field(default_factory=list, description="Các node bằng chứng vệ tinh")
    semantic_yarns: List[Dict[str, Any]] = Field(default_factory=list, description="Dây chỉ đỏ nối trực tiếp giữa các trạm")

class CameraTransitionCurve(BaseModel):
    """Khế ước chuyển động máy quay giữa 2 trạm (Pan/Zoom mượt mà thay thế Hard-Cut)."""
    from_station_id: str
    to_station_id: str
    transition_start_sec: float
    transition_duration_sec: float = Field(default=1.2, ge=0.8, le=2.0)
    pan_spring_preset: str = Field(default="opuscarContinuousPan")
    lead_connector_id: Optional[str] = Field(None, description="Sợi chỉ đỏ dẫn hướng camera sang trạm tiếp theo")

class ContinuousDeskWorldProps(BaseModel):
    """Khế ước tổng thể toàn Act của Bàn Điều Tra Liên Tục (FT-207)."""
    act_id: str = Field(..., pattern=r"^ACT_\d{2}$")
    world_width: int = Field(default=3840, ge=1920)
    world_height: int = Field(default=2160, ge=1080)
    desk_material: str = Field(default="aged_newsprint_kraft")
    stations: List[DeskStationAnchor] = Field(..., min_items=2)
    camera_transitions: List[CameraTransitionCurve] = Field(default_factory=list)
    word_timestamps: List[Dict[str, Any]] = Field(default_factory=list)

# ==============================================================================
# MASTER EPISODE CONTEXT (SINGLE SOURCE OF TRUTH)
# ==============================================================================
class EpisodeContext(BaseModel):
    episode_id: str = Field(..., pattern=r"^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$")
    topic_slug: str
    total_scenes: int = Field(..., ge=1)
    target_fps: int = Field(default=30)
    master_sheet_bundles: Dict[str, MasterSheetAssetBundle]
    tactile_plates: Dict[str, OmniTactilePlate]
    render_props: Optional[Dict[str, Any]] = None
    karaoke_drift_tolerance_ms: int = Field(default=0, description="Dung sai lệch audio = 0ms")
```
