# 📝 [CHANGE_MANIFEST] HYBRID_VOX_VEO_FORENSIC_PAPER_ANIMATION_PIPELINE

## 📌 1. Trạng Thái Thực Thi (Execution Metadata)
- **Author Role**: Builder / Implementer & Architect
- **Target Task**: `HYBRID_VOX_VEO_FORENSIC_PAPER_ANIMATION_PIPELINE`
- **Scope**: Tái cấu trúc toàn diện từ Bước 3 (B3) trở đi: Hợp nhất B3 + B3.5, chuyển dịch 100% sang Bộ 4 Chuẩn Động Lực Học Hồ Sơ Pháp Y (Forensic Paper Stop-Motion I2V), điều phối tuần tự 6 tài khoản Google Flow Playwright CDP, và nâng cấp Remotion Audio Spine (12fps Jitter, Foleys SFX & Auto-Ducking BGM -6dB, Rule 136 Zero-Asset-Leak).
- **AST Py-Compile**: `EXIT CODE 0` trên cả Hetzner VPS Linux và Windows Local.
- **Remotion TypeScript Bundle**: `EXIT CODE 0` (`Bundling 100% ○ /home/agent-mcp/workspace/build`).
- **Remotion Still Render**: `EXIT CODE 0` (Rendered 1080p audit frames: `frame_audit.jpg`, `frame_audit_300.jpg`).
- **Three-Way Physical Sync**: VPS ⇄ GitHub ⇄ Local 100% bit-for-bit parity.

---

## 📂 2. Chi Tiết File Sửa Đổi (Line-Level Changes)

### A. Remotion Audio & Motion Engine (`remotion/src/index.tsx`)
1. **Background Video Playback**:
   - Tích hợp thẻ `<Video>` tự động phát video MP4/WebM lặp vô tận (`loop`, `muted`) khi phát hiện `hero_video_sc*.mp4`.
2. **12fps Organic Stop-Motion Paper Jitter**:
   - Áp dụng micro-jitter ngẫu nhiên có kiểm soát (`steppedFrame`, `jitterX`, `jitterY`, `jitterRot` ±1.25px / ±0.8°) tạo hiệu ứng hoạt họa cắt giấy thủ công xúc giác.
3. **Foley SFX Sequence Execution**:
   - Thêm mảng `foleyElements` render `<Audio src={resolveSrc(foleySrc)} volume={0.85} />` khớp từng scene có `foleysAudio`.
4. **BGM Auto-Ducking (-6dB)**:
   - Hàm `getBgmVolume(frame)` tự động hạ âm lượng nhạc nền BGM xuống 0.5x (-6dB) trong 30 frames đầu của mỗi phân cảnh kích hoạt Foleys SFX với đường dốc êm ái (smooth ramp).
5. **Rule 136 Zero-Asset-Leak Speaker Tag**:
   - Hàm `cleanSpeakerTag()` triệt tiêu 100% rò rỉ mã asset nội bộ (`.png`, `.jpg`, `bg_`, `fg_`, `ARCHIVE X`), chỉ cho phép hiển thị `TÊN // VAI TRÒ` hoặc `BEAT <X>: <TIÊU ĐỀ>`.

### B. Remotion Props Builder & Asset Routing (`app/services/build_remotion_props.py`)
1. **Candidate Path Auto-Resolution**:
   - Tự động quét và định tuyến đường dẫn asset cho `bg_key` và `fg_key` trên cả thư mục `public/pulled/`, `images/`, và root episode.
2. **Foleys SFX Mapping**:
   - Trích xuất `foleys_audio` / `foleys_trigger` từ `director_plan.json` và chuẩn hóa thành đường dẫn `sfx/<name>.mp3` trong `remotion_props.json`.
3. **Hero Video Binding**:
   - Tự động nhận diện và gán `hero_video_{scene_id}.mp4` vào thuộc tính `background` khi shot type là `HERO_AI_VIDEO`.

### C. Unified VOX Director (`app/services/unified_vox_director.py`)
1. **Hợp Nhất B3 + B3.5**:
   - Tạo cấu trúc phân cảnh 131 scenes, chỉ định 20 Hero AI Video clips phân bổ tuần tự trên 6 tài khoản (`acc_01` $\to$ `acc_06`).
2. **4 Chuẩn Động Lực Học Pháp Y**:
   - `CORNER_DOGEAR_PEEL`, `DOCUMENT_TABLE_DROP`, `BIFOLD_DOSSIER_OPEN`, `MACRO_HIGHLIGHT_WIPE`.
   - Prompt vật lý chất liệu giấy bìa 300gsm, ánh sáng directional keylight 45 độ, nét vẽ comic ink/cel-shading 2D, 12fps stop-motion rhythm.

### D. Composite Seed Generator (`app/services/composite_generator.py`)
1. **Tự Động Ghép Ảnh Seed 16:9**:
   - Ghép Layer 1 Background (16:9) và Layer 2 Foreground Evidence (1:1 sticker cutout) với bóng đổ 3D drop-shadow thực tế.
   - Batch sinh 20/20 composite seeds cho tập `EN_EP0004_amazon_ad_lawsuit`.

### E. Flow Video Dispatcher (`scripts/flow_video_dispatcher.py`)
1. **Playwright + CDP Pipeline**:
   - Tự động đăng nhập/sử dụng profile Chrome của 6 tài khoản.
   - Nạp I2V composite seed, điền Veo 3.1 - Fast prompt.
   - Auto JS click dialog duyệt quyền `Approve` / `Always approve`.
   - Download trực tiếp luồng video 720p qua Chrome DevTools Protocol (CDP).

### F. SFX Foley Library (`remotion/public/sfx/`)
1. **Bổ Sung 6 File Foley Chuẩn**:
   - `document_table_thud.mp3`, `gavel_thud.mp3`, `paper_crease_snap.mp3`, `paper_page_turn.mp3`, `paper_rustle.mp3`, `stamp_impact.mp3`.

---

## 🧹 3. Cam Kết Dọn Rác & Zero-Ghost (Rule 119, 125, 126)
- [x] Không tồn tại file `.bak*`, `.backup*`, file shadow code.
- [x] Đã đồng bộ tài liệu nội hàm và khế ước (Rule 125 Single Truth).
- [x] `python3 -m py_compile` đạt Exit Code 0 trên cả VPS và Local.
- [x] Remotion bundle và Still render đạt Exit Code 0.
