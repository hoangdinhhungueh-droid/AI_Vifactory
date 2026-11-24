# 🧪 04_VERIFICATION.md - MA TRẬN KIỂM THỬ VIDEO PIPELINE

> **NGHIỆM THU THỰC THI CHƯƠNG TRÌNH SỐNG (PROGRAMMATIC RUNTIME EXECUTION GATE).**
> Cấm nghiệm thu bằng py_compile suông. Bắt buộc chạy live script với exit code 0.
> Mọi tiêu chuẩn nghiệm thu phải được định nghĩa theo cú pháp Gherkin (Given-When-Then).

---

### [TEST-301] Kiểm thử Papertrails Director & Timeline Forge (Mã FT-301)
- **Mã Feature**: `FT-301`
- **Test File**: `tests/test_papertrails_director.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_papertrails_director.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Kịch bản điều tra S03 kèm file giọng đọc và Whisper timestamps.
  - `When`: Hàm `build_papertrails_timeline()` được thực thi.
  - `Then`: Bắt buộc sinh `timeline.json` chuẩn v1; duration khớp 100% audio; 100% scenes có Biome, 3D Prop, Camera hợp lệ; Captions chia nhỏ $\le 3.5\text{s}$ kèm mốc `words` chính xác để phục vụ karaoke.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-302] Kiểm thử Papertrails VPS Renderer Bridge (Mã FT-302)
- **Mã Feature**: `FT-302`
- **Test File**: `tests/test_papertrails_vps_bridge.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_papertrails_vps_bridge.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: File `timeline.json` và file giọng đọc `voice.mp3`.
  - `When`: Lệnh render Playwright WebGL2 được kích hoạt trên VPS Linux.
  - `Then`: Kết xuất video `final.mp4` hợp lệ; ffprobe xác nhận luồng video h264 và luồng audio aac; độ sai lệch thời lượng $\le 0.08\text{s}$; hiệu ứng âm thanh tactile lật giấy `--sfx` hòa quyện dưới giọng đọc.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-202] Kiểm thử Kế hoạch Đạo diễn Xúc giác 7 Họ $H_1..H_7$ (Mã FT-202)
- **Mã Feature**: `FT-202`
- **Test File**: `tests/test_kinetic_sub_director.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_kinetic_sub_director.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Kịch bản phân cảnh kèm Voiceover.
  - `When`: Hàm `run()` của Stage S05 được thực thi.
  - `Then`: 100% Scene sinh ra phải có `scene_sub_director_plan` với 4..7 Micro-Beats, cú pháp liên hợp `[SOURCE] + [verb] + [TARGET]`, và neo cứng Whisper word timestamps ($0\text{ms}$ drift).
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Verified: 2026-11-21 16:26:52) (Verified: 2026-11-21 01:32:59) (Verified: 2026-11-21 01:16:22) (Verified: 2026-11-20 15:27:51) (Verified: 2026-11-19 13:14:48) (31/31 tests passed)

---

### [TEST-203] Kiểm thử Cổng Chuyển Động Xúc Giác Omni (Mã FT-203)
- **Mã Feature**: `FT-203`
- **Test File**: `tests/test_temporal_motion_gate.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_temporal_motion_gate.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Clip video chất liệu môi trường sinh từ Omni.
  - `When`: Hàm `validate_video_motion_temporal_delta()` được gọi.
  - `Then`: Clip phải có độ biến thiên pixel $\ge 0.5$ (chống freeze-frame). Video tĩnh loop ảnh bị chặn đứng ngay lập tức với `StaticFreezeFrameError`.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Verified: 2026-11-21 16:26:52) (Verified: 2026-11-21 01:32:59) (Verified: 2026-11-21 01:16:22) (Verified: 2026-11-20 15:27:51) (Verified: 2026-11-19 13:14:48) (3/3 tests passed)

---

### [TEST-204] Kiểm thử Nhất Quán Khế Ước Remotion Props Parity (Mã FT-204)
- **Mã Feature**: `FT-204`
- **Test File**: `tests/test_remotion_props_parity.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_remotion_props_parity.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Schema Pydantic `RemotionRenderProps` và schema file TypeScript trên đĩa.
  - `When`: Kiểm tra đối soát thuộc tính.
  - `Then`: Khớp chính xác 100% từng trường thuộc tính (properties và required list), độ lệch vi sai bằng 0.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Verified: 2026-11-21 16:26:52) (Verified: 2026-11-21 01:32:59) (Verified: 2026-11-21 01:16:22) (Verified: 2026-11-20 15:27:51) (Verified: 2026-11-19 13:14:48) (1/1 test passed)

---

### [TEST-205] Kiểm thử Khế Ước Stage Artifact & Import Integrity (Mã FT-205)
- **Mã Feature**: `FT-205`
- **Test File**: `tests/test_contracts.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_contracts.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Toàn bộ các Stage trong Pipeline từ S01 đến S11.
  - `When`: Khởi tạo và serialization `StageArtifact`.
  - `Then`: Exit code == 0, enum StageID toàn vẹn, import integrity của Stage S10 đạt chuẩn 100%.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Verified: 2026-11-21 16:26:52) (Verified: 2026-11-21 01:32:59) (Verified: 2026-11-21 01:16:22) (Verified: 2026-11-20 15:27:51) (Verified: 2026-11-19 13:14:48) (6/6 tests passed)

---

### [TEST-206] Kiểm thử Opus 5.5 Dynamic Art Director & Tactile Manifest (Mã FT-206)
- **Mã Feature**: `FT-206`
- **Test File**: `tests/test_opus_art_director.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_opus_art_director.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Phân cảnh với lời đọc voiceover và tiêu đề điều tra.
  - `When`: Hàm `generate_dynamic_art_manifest()` được thực thi.
  - `Then`: Bắt buộc sinh ra `DynamicMasterArtManifest` hợp lệ, chứa đủ 3 prompt sinh ảnh (`assembled_keyframe_prompt`, `hero_cutout_prompt`, `interacting_tool_prompt`), điểm chạm `TactileContactPoint` thuộc họ H1-H7, camera `DynamicMacroCamera` với tiêu điểm chuẩn hóa và zoom scale $1.1 - 1.6$, `ingress_duration_sec <= 0.4s`, `dual_pass_shadow == True`; 100% test assertions PASS.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 04:45:00)

---

### [TEST-207] Kiểm thử Bàn Điều Tra Liên Tục DeskWorld & Camera Pan Journey (Mã FT-207)
- **Mã Feature**: `FT-207`
- **Test File**: `tests/test_desk_world_director.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_desk_world_director.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Kế hoạch Act I với 4 phân cảnh liên tiếp.
  - `When`: Hàm `build_continuous_desk_world()` được thực thi.
  - `Then`: Bắt buộc sinh đủ 4 trạm khảo sát trên bàn điều tra mở rộng ($\ge 3840\times 2160$); 100% các trạm có camera transition pan mượt mà (duration $0.8s - 2.0s$); Scene 01 Hero bắt buộc là tài liệu pháp lý ASIC (cấm tuyệt đối từ khóa/hình ảnh TSMC/chip/microprocessor); 100% test assertions PASS.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Khởi tạo: 2026-11-23)
