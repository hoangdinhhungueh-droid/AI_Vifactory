# 🧩 02_FEATURES.md - DANH MỤC TÍNH NĂNG PIPELINE (IN-PLACE LIVING STATE)

> **CẤM GHI NHẬT KÝ SONG SONG (ZERO APPEND-ONLY LOGS).**
> Khi cập nhật stage hay logic sản xuất, tìm đúng mã `[FT-xxx]` và sửa đè trực tiếp tại khối đó.
> Mọi thay đổi lịch sử thuộc về `git log`. File này luôn là bản đồ thực tế sống của hệ thống.

---

### [FT-301] Papertrails Director & Semantic Timeline Forge
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/papertrails_director.py`
- **Hàm/Service**: `build_papertrails_timeline`
- **Input Contract**: `S03_ScriptOutput` & `WhisperTimestamps` (từ S09)
- **Output Contract**: `PapertrailsTimelineSpec` (xem `01_CONTRACTS.md`)
- **Logic cốt lõi**:
  1. Đọc kịch bản 5-Beat đã chốt tại Human Gate 1 và timestamps giọng đọc.
  2. Tự động phân tích ngữ nghĩa (bilingual Vietnamese & English):
     - Gán Biome 3D phù hợp: `heartland`, `desert`, `snow`, `blossom`, `pinewood`.
     - Gán 3D Prop tương thích: `factory`, `chart`, `coin`, `clock`, `book`, `globe`, `bridge`, `forest`, `mountain`, `water`, `sun`, `moon`, `village`, `house`, `people`, `mic`, `bubble`.
     - Gán Camera 3D biến đổi liên tục: `push` (dolly tiến), `low` (góc anh hùng cận sàn giấy), `crane` (nâng tầm nhìn bao quát), `orbit`, `wide`, `top`.
  3. Tự động ngắt nhịp phụ đề (split captions) $\le 3.5\text{s}$ hoặc theo dấu câu, bảo toàn danh sách `words` với mốc thời gian thực để phục vụ tô đỏ chữ karaoke (0ms drift).
  4. Hỗ trợ tạo `card` kiểu `note` (ghi chú dán băng dính) và `photo` (ảnh tư liệu có elip highlight đỏ và tem mộc pháp y).
  5. Xuất file `timeline.json` chuẩn v1.

---

### [FT-302] Papertrails VPS Playwright WebGL2 Headless Renderer
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/papertrails_vps_bridge.py` & `vox/papertrails_engine/scripts/render.mjs`
- **Hàm/Service**: `render_papertrails_on_vps`
- **Input Contract**: `PapertrailsTimelineSpec` (`timeline.json`) & `voice_narration.mp3`
- **Output Contract**: `final.mp4` (1080p @ 30fps, H.264/AAC, có tactile paper flip SFX)
- **Logic cốt lõi**:
  1. Khởi chạy Vite server và Chromium headless trên VPS Linux thông qua Playwright.
  2. Bơm timeline và Voice Envelope RMS tính từ audio gốc vào Three.js WebGL2 context.
  3. Mô phỏng thời gian tất định từng frame (`renderFrame(frame)`), chụp canvas screenshot và pipe thẳng vào `ffmpeg` qua `stdin`.
  4. Tự động tổng hợp dải giấy rách torn paper có phụ đề chữ đỏ karaoke theo thời gian thực.
  5. Chèn âm thanh lật giấy tactile sfx tại các điểm cắt chuyển cảnh (cut transitions) hòa quyện dưới giọng đọc gốc.
  6. Kiểm tra tính toàn vẹn của MP4, thời lượng, số frame và độ trôi âm thanh (0ms drift).

---

### [FT-303] Unified Voice-First Papertrails Orchestration Bridge
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s08_video_gen.py` & `stages/s10_render.py`
- **Hàm/Service**: `run`
- **Input Contract**: RunContext kèm kịch bản S3 và giọng đọc S9
- **Output Contract**: StageArtifact
- **Logic cốt lõi**:
  1. Đấu nối trực tiếp sau Human Gate 1: Lấy kịch bản từ S3/S4, giọng đọc từ S9.
  2. Tự động gọi FT-301 sinh `timeline.json`, sau đó gọi FT-302 render MP4 master trên VPS.
  3. Hoàn toàn loại bỏ việc chờ ảnh thủ công, loại bỏ Google Flow Veo 7 tài khoản, loại bỏ các prompt tạo ảnh tốn phí.

---

### [FT-201] Master Sheet Component Kit & Layer Slicer [QUARANTINED]
- **Trạng thái**: `QUARANTINED_LEGACY`
- **Ghi chú**: Đã được cô lập vào khu vực cách ly, nhường chỗ cho Papertrails 3D Engine.

---

### [FT-203] Omni Tactile Texture Engine [QUARANTINED]
- **Trạng thái**: `QUARANTINED_LEGACY`
- **Ghi chú**: Đã được cô lập vào khu vực cách ly, không còn sử dụng trong pipeline chính.

---

### [FT-205] Ground-Truth Timeline & Subtitle Chapter Sync
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s11_qc.py`
- **Hàm/Service**: `run`
- **Input Contract**: `final.mp4` & `timeline.json`
- **Output Contract**: `YouTubeMetadata` & `QCReport`
- **Logic cốt lõi**:
  1. Trích xuất chính xác mốc thời gian chương hồi (`00:00`, `MM:SS`) từ các cảnh của `timeline.json` thực tế kết xuất.
  2. Nghiệm thu dung sai Karaoke Subtitle Drift = 0ms.

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
