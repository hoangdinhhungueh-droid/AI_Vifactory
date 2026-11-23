# 🧩 02_FEATURES.md - DANH MỤC TÍNH NĂNG PIPELINE (IN-PLACE LIVING STATE)

> **CẤM GHI NHẬT KÝ SONG SONG (ZERO APPEND-ONLY LOGS).**
> Khi cập nhật stage hay logic sản xuất, tìm đúng mã `[FT-xxx]` và sửa đè trực tiếp tại khối đó.
> Mọi thay đổi lịch sử thuộc về `git log`. File này luôn là bản đồ thực tế sống của hệ thống.

---

### [FT-201] Master Sheet Component Kit & Layer Slicer
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/master_scene_sheet.py`
- **Hàm/Service**: `generate_master_sheet_bundle`
- **Input Contract**: `SceneSubDirectorPlan` từ Stage S05
- **Output Contract**: `MasterSheetAssetBundle` (xem `01_CONTRACTS.md`)
- **Logic cốt lõi**:
  1. Sinh trọn vẹn Bộ Master Sheet 6-trong-1 bắt buộc:
     - (1) Image Result mong muốn: Ảnh kết quả tổng thành 2560x1440 (`assembled_anchor_url`).
     - (2) Object Chủ thể: Ảnh nhân vật/tài liệu cô lập trên nền trắng #FFFFFF có Alpha (`hero_cutout_url`).
     - (3) Object Tương tác: Ảnh dụng cụ cơ khí thước kẹp/con dấu/chỉ đỏ trên nền trắng #FFFFFF có Alpha (`interacting_tool_url`).
     - (4) Thông tin dữ liệu định lượng: Headline, stat hero đỏ, narration (`information_spec`).
     - (5) Transaction Prompt: Prompt tương tác xúc giác chuyển động H1..H7 cho Omni/Veo living texture (`transaction_prompt`).
     - (6) Sơ đồ & Khế ước Đấu nối: Tọa độ neo source -> target, loại connector, ingress <= 0.4s cubic-bezier, dead-stop hold 12fps (`wiring_spec`).
  2. Tự động bóc tách (slice) thành các file ảnh PNG có kênh Alpha trong suốt.
  3. Xuất Master Asset Sheet trực quan (1920x1080) và Dashboard HTML đồng bộ.
  4. Cấp phát bundle đầy đủ cho Remotion và Omni; triệt tiêu hoàn toàn căn bệnh nạp ảnh composite phẳng vào model video hoặc thiếu linh kiện kết nối.

---

### [FT-202] Kinetic Sub-Director Planner (Vox Engine v3)
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s05_director_plan.py`
- **Hàm/Service**: `run`
- **Input Contract**: `S03_ScriptOutput` & `S04_CriticApproval`
- **Output Contract**: `SceneSubDirectorPlan` ($H_1 \to H_7$)
- **Logic cốt lõi**:
  1. Phân rã mỗi Scene thành 4..7 Micro-Beats xúc giác theo 7 Họ tương tác vật lý ($H_1$ Dập dấu, $H_2$ Thước kẹp, $H_4$ Chỉ đỏ...).
  2. Khóa cứng quy tắc chuyển động đơn hướng: các layer đưa vào tốc độ cao theo cùng 1 chiều ($X$-axis, $\le 0.4\text{s}$, cubic-bezier), dead-stop spatial hold.
  3. Neo cứng từng mốc chuyển động với Whisper word timestamps ($0\text{ms}$ drift).

---

### [FT-203] Omni Tactile Texture Engine (Google Flow I2V)
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s08_video_gen.py`
- **Hàm/Service**: `run`
- **Input Contract**: `OmniTactilePlateRequest`
- **Output Contract**: `OmniTactilePlate` (xem `01_CONTRACTS.md`)
- **Logic cốt lõi**:
  1. Chỉ sử dụng Omni 1.1 Flash / Veo 3.1 để sinh các đoạn video chất liệu môi trường sống (living paper texture, scanlines CRT, archival fumes).
  2. Bắt buộc prompt chứa mệnh lệnh triệt tiêu camera motion: `Locked static computer screen frame, no zoom, no pan, zero camera movement`.
  3. CẤM TUYỆT ĐỐI giao layer định vị, di chuyển chủ thể hoặc chữ số cho Omni.
  4. Kiểm định chuyển động vật lý bằng `validate_video_motion_temporal_delta >= 0.5`.

---

### [FT-204] Remotion Master Director Compositor
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s10_render.py`
- **Hàm/Service**: `run`
- **Input Contract**: `RemotionRenderProps` (tổng hợp từ FT-201, FT-202, FT-203, FT-205)
- **Output Contract**: `final.mp4` (1080p @ 30/60fps)
- **Logic cốt lõi**:
  1. Giữ vai trò Đạo diễn Khung hình tối thượng: Khung máy tính cố định 1920x1080 (zero camera zoom/pan).
  2. Nhúng clip chất liệu Omni (FT-203) làm background plate sống động.
  3. Điều phối các layer PNG alpha (FT-201) trượt vào tốc độ cao cùng chiều từ mép phải theo đường cong cubic-bezier overshoot ($\le 0.3\text{s}$).
  4. Vẽ sợi chỉ đỏ / thước kẹp khóa khớp giữa các chủ thể sau khi các chủ thể dừng lại.
  5. Bảo toàn 100% độ sắc nét chuẩn xác của con số và văn bản.

---

### [FT-205] Ground-Truth Timeline & Subtitle Chapter Sync
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s11_qc.py`
- **Hàm/Service**: `run`
- **Input Contract**: `final.mp4` & `remotion_props.json`
- **Output Contract**: `YouTubeMetadata` & `QCReport`
- **Logic cốt lõi**:
  1. Trích xuất chính xác mốc thời gian chương hồi (`00:00`, `MM:SS`) từ `remotion_props.json` thực tế kết xuất.
  2. Cấm tính mốc chapter từ độ dài ước lượng hay tổng thời lượng audio rời rạc.
  3. Nghiệm thu dung sai Karaoke Subtitle Drift = 0ms.

---

### [FT-206] Opus 5.5 Dynamic Art Director & Tactile Kinetic Engine (Vox Engine v3)
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/opus_art_director.py`
- **Hàm/Service**: `generate_dynamic_art_manifest`
- **Input Contract**: `scene_id`, `narration`, `headline`
- **Output Contract**: `DynamicMasterArtManifest` (xem `01_CONTRACTS.md`)
- **Logic cốt lõi**:
  1. Opus 5.5 (HHTech API) đóng vai trò Giám đốc Mỹ thuật Tối cao, sáng tạo manifest độc bản cho từng Scene (zero hardcoding đạo cụ).
  2. Tuân thủ Rule 132 Decoupled Engine: System prompt kỹ thuật lưu tại `config/prompts/cl3_vox_engine/opus_art_director.md`, nạp động qua `skill_loader.py`.
  3. Quyết định điểm chạm cơ học xúc giác 7 họ ($H_1 \to H_7$) và tồn dư vật lý (`red_ink_stain`, `yellow_glow`, `paper_tear`, `needle_hole`, `embossed_crease`).
  4. Quyết định camera Macro Punch-In lướt sâu vào tiêu điểm chuẩn hóa `[norm_x, norm_y]` ($1.25x - 1.55x$) thay thế lia máy trượt bàn (`pan`) lặp lại.
  5. Hỗ trợ fallback đối kháng GPT-6-Astra và deterministic contextual fallback đảm bảo độ bền vững 100% trong mọi điều kiện mạng.

---

### [FT-207] Continuous Vox DeskWorld & Semantic Forensic Camera Journey
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/desk_world_director.py`
- **Hàm/Service**: `build_continuous_desk_world`
- **Input Contract**: `ActNarrativeContext` & `WordTimestamps`
- **Output Contract**: `ContinuousDeskWorldProps` (xem `01_CONTRACTS.md`)
- **Logic cốt lõi**:
  1. **Không gian Bàn Điều Tra Duy Nhất (`DeskWorld` 3840x2160)**:
     - Xóa bỏ hoàn toàn căn bệnh Hard-Cut giữa các `<Sequence>` độc lập khiến khán giả mất bộ nhớ không gian.
     - Đặt toàn bộ 4 phân cảnh của Act I lên cùng 1 mặt bàn điều tra liên tục tại 4 trạm khảo sát (`STATION_01` đến `STATION_04`).
  2. **Camera Hành Trình Liên Tục (`CameraJourney`)**:
     - Camera pan/zoom mượt mà từ trạm này sang trạm khác dọc theo sợi dây chỉ đỏ liên kết (`lead_connector_id`).
     - Vật thể của trạm trước vẫn nằm ở mép ngoại vi khi camera chuyển sang trạm mới, bảo toàn 100% định hướng không gian của người xem.
  3. **Sửa Chữa Triệt Để Lỗi Ngữ Nghĩa (Semantic Correction)**:
     - Thay thế 100% hình ảnh vi mạch TSMC 7nm tại Scene 01 bằng tài liệu công bố hành chính chính thống của Ủy ban Chứng khoán Úc (ASIC Form 505 / Notice of External Administration).
     - Xóa bỏ nhãn "VOX" tự phát trên bìa hồ sơ công ty mẹ tại Scene 02.
     - Thay thế công cụ cơ khí vintage bằng bản đồ mạng lưới 35 cửa hàng tại Scene 03 và thước kẹp niên biểu tại Scene 04.
  4. **Nhịp Động Học Micro-Beats Đồng Bộ Faster-Whisper**:
     - Loại bỏ hiện tượng rơi xuống trong 0.4s rồi đóng băng tĩnh 7s.
     - Cứ mỗi 1.5s - 2.0s kích hoạt một biến đổi trạng thái có nghĩa (reveal bằng chứng, vẽ dây nối, đóng dấu, highlight từ khóa) bám sát âm thanh.
