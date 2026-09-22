# 📐 [TASK_SPEC] HYBRID_3D_TACTILE_DOCUDRAMA_OVERHAUL

## 📌 1. Bối Cảnh & Ranh Giới (Context & Boundaries)
- **Feature Title**: VOX Forensic Tactile Stop-Motion Pipeline Overhaul (Veo 3.1 Forensic Paper Physics + Remotion 2.5D Audio Spine Engine).
- **Target Episode ID**: `EN_EP0004_amazon_ad_lawsuit`
- **Tôn Chỉ Nghiệp Vụ Mới (VOX Forensic Stop-Motion Core)**:
  - Khắc phục triệt để hiệu ứng gấp giấy origami chim/thiên nga trừu tượng xa rời thực tế điều tra. Thay thế bằng **Bộ 4 Chuẩn Động Lực Học Hồ Sơ Pháp Y (4 Forensic Paper Physics Patterns)**:
    1. `CORNER_DOGEAR_PEEL`: Lật gấp góc hồ sơ 45 độ / Giở trang bóc lớp che giấu bộc lộ dữ liệu mật.
    2. `DOCUMENT_TABLE_DROP`: Hồ sơ rơi/trượt mạnh xuống bàn gỗ (0.3s snappy entry) kèm độ nảy và rung lắc vi mô (paper flutter).
    3. `BIFOLD_DOSSIER_OPEN`: Mở tập tài liệu gấp đôi / gấp ba (bifold/trifold docket unfold) phẳng ra mặt bàn điều tra.
    4. `MACRO_HIGHLIGHT_WIPE`: Camera macro trượt dọc theo văn bản kết hợp vệt bút dạ quang neon quét sáng theo audio Whisper.
  - Xuyên suốt video: Áp dụng **12fps Organic Stop-Motion Paper Jitter** (rung lắc xúc giác ±1px, xoay nhẹ ±0.5° mỗi 2-3 frames) tạo cảm giác hoạt họa cắt giấy thủ công sống động (Posterize Time 12fps).
  - Tăng cường liên kết ngữ cảnh (Thematic Cohesion): Nền (BG) và Vật thể (FG) gắn kết mật thiết thành bối cảnh điều tra hoàn chỉnh (Bảng ghim hồ sơ FBI/FTC, mặt bàn gỗ sồi flat-lay chứa hồ sơ dập dấu đỏ, phòng máy chủ đấu giá quảng cáo).

- **Primary Blocks Impacted**:
  - `B3.0` (`app/services/unified_vox_director.py`): Định tuyến động học thực tế (`spatial_physics_type`: `CORNER_DOGEAR_PEEL`, `DOCUMENT_TABLE_DROP`, `BIFOLD_DOSSIER_OPEN`, `MACRO_HIGHLIGHT_WIPE`). Phân bổ 18–20 cảnh chuyển hồi & bằng chứng xoay vòng tuần tự trên 6 tài khoản Google AI Pro (`acc_01` $\to$ `acc_06`, 3-4 clip/acc).
  - `B3.5` (`app/services/prompt_forge.py`): Tái thiết kế Prompt Engine:
    - BG Prompt: Bảng điều tra corkboard ghim chỉ đỏ, bàn gỗ sồi flat-lay chứa hồ sơ FTC, phòng máy chủ server rack.
    - FG Prompt: Hồ sơ bằng chứng dập dấu "CONFIDENTIAL", thanh che đen redaction bar, hóa đơn thiệt hại $20B, bảng cân đối kế toán.
    - Veo I2V Prompt: Mô tả chuyển động vật lý cụ thể (corner dog-ear peel, document table slam, bifold folder open) với chất giấy 300gsm, 12fps stop-motion rhythm, cấm tuyệt đối người thật photorealistic.
  - `B4.5` (`app/services/composite_generator.py`): Tự động tạo ảnh Seed 16:9 (`composite_seeds/composite_sc*.png`) ghép Layer 1 (Nền bàn điều tra) và Layer 2 (Hồ sơ chứng cứ) với bóng đổ tách lớp thực tế.
  - `B5.5` (`scripts/flow_video_dispatcher.py`): Chạy tuần tự an toàn từng Account (acc_01 -> acc_06) qua Playwright + CDP download 720p trực tiếp, tự động JS approve, kiểm soát tài nguyên máy.
  - `B6.0 / B6.5` (`app/services/build_remotion_props.py`, `remotion/src/index.tsx`): Remotion render video Veo làm nền/chuyển cảnh, áp hiệu ứng 12fps stop-motion jitter, hòa trộn âm thanh Foleys tiếng giấy lật xoẹt/snap/dập dấu (ducking BGM -6dB), và quét dạ quang neon khớp Whisper word timestamps.

---

## 🎯 2. Yêu Cầu Kỹ Thuật (Requirements R1 - R6)
- **R1 (Zero Photorealistic Real Humans - Rule 122)**: 100% video Veo sinh từ luồng Image-to-Video (I2V) lấy ảnh Graphic Novel B4 làm Seed Frame. Bảo lưu 100% nét mực comic ink, cel-shading, chất giấy có vân hạt.
- **R2 (VOX Forensic Stop-Motion Transitions)**: Thay thế hoàn toàn origami trừu tượng bằng 4 chuẩn chuyển động hồ sơ pháp y thực tế (Corner dog-ear peel, Table drop/slam, Bifold open, Macro highlight wipe) ở nhịp 12fps.
- **R3 (Thematic Background-Object Cohesion)**: Nền và vật thể chứng cứ phải gắn kết logic theo cốt truyện từng Beat của vụ kiện $20B FTC vs Amazon.
- **R4 (Dynamic Audio Spine & Foleys Sync - Rule 120)**: Remotion cắt cúp Veo clip để điểm rơi vật lý (bung nếp gấp, dập dấu) khớp mili-giây với từ khóa Whisper. Auto-ducking BGM khi phát Foleys tiếng giấy.
- **R5 (Sequential 6-Account Auto-Rotation & CDP Download)**: Dispatcher chạy tuần tự từ `acc_01` đến `acc_06`, tối ưu RAM/CPU, tự động duyệt modal qua JavaScript, tải trực tiếp 720p qua CDP.
- **R6 (Three-Way Physical Parity & Zero Ghost Code - Rule 125 & 126)**: AST `py_compile` exit 0, quét sạch 4 tầng qua `ghost_code_detector.py`, đối soát SHA256 VPS ⇄ GitHub ⇄ Local, CI green.

---

## 🔒 3. Khế Ước Giao Diện (Interface Contracts)
- **Director Plan Contract (`director_plan.json`)**:
  - `spatial_physics_type`: `"CORNER_DOGEAR_PEEL"` | `"DOCUMENT_TABLE_DROP"` | `"BIFOLD_DOSSIER_OPEN"` | `"MACRO_HIGHLIGHT_WIPE"` | `"REMOTION_FORENSIC"`
  - `seed_asset_mode`: `"COMPOSITE_16_9"` | `"CUTOUT_ONLY"`
  - `seed_asset_path`: File URI trên đĩa
  - `foleys_trigger`: `"paper_crease_snap"` | `"paper_page_turn"` | `"document_table_thud"` | `"stamp_impact"` | `"gavel_thud"`
- **Prompts Forge Contract (`prompts_forge.json`)**:
  - `bg_prompts`: Bối cảnh điều tra pháp y gắn kết (Corkboard, Oak Desk Flat-lay, Server Room, Hearing Room).
  - `fg_prompts`: Hồ sơ tài liệu chứng cứ chuẩn thực tế điều tra (FTC Docket, Redacted Memo, Revenue Ledger).
  - `veo_physics_prompts`: 5 thành phần động lực học hồ sơ pháp y 12fps.
- **Remotion Props Contract (`remotion_props.json`)**:
  - `videoSrc`: File MP4 của Veo
  - `foleysAudio`: Tên file âm thanh Foleys khớp thời điểm rơi
  - `highlighterKeywords`: Danh sách từ khóa kích hoạt vệt dạ quang

