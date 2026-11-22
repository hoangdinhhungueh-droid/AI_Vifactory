# 🧪 04_VERIFICATION.md - MA TRẬN KIỂM THỬ VIDEO PIPELINE

> **NGHIỆM THU THỰC THI CHƯƠNG TRÌNH SỐNG (PROGRAMMATIC RUNTIME EXECUTION GATE).**
> Cấm nghiệm thu bằng py_compile suông. Bắt buộc chạy live script với exit code 0.
> Mọi tiêu chuẩn nghiệm thu phải được định nghĩa theo cú pháp Gherkin (Given-When-Then).

---

### [TEST-201] Kiểm thử Khởi tạo Master Sheet 6-trong-1 & Cắt tách Alpha Layers (Mã FT-201)
- **Mã Feature**: `FT-201`
- **Test File**: `tests/test_master_sheet_slicer.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_master_sheet_slicer.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Kế hoạch phân cảnh từ S05.
  - `When`: Hàm `generate_master_sheet_bundle()` được thực thi.
  - `Then`: Bắt buộc sinh đủ 6 thành phần: `assembled_anchor_url`, `hero_cutout_url`, `interacting_tool_url`, `information_spec`, `transaction_prompt`, `wiring_spec`; `camera_movement == "locked"`, `ingress_duration_sec <= 0.4s`, ném lỗi nếu thiếu trường.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Verified: 2026-11-21 16:26:52) (Verified: 2026-11-21 01:32:59) (Verified: 2026-11-21 01:16:22)

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

### [TEST-206] Kiểm thử Bố Cục Động Đa Dạng & Triệt Tiêu Trùng Lặp Tọa Độ (Mã FT-206)
- **Mã Feature**: `FT-206`
- **Test File**: `tests/test_dynamic_layout_archetypes.py`
- **Lệnh chạy kiểm thử (CLI)**: `python -m pytest tests/test_dynamic_layout_archetypes.py -v`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Kế hoạch 4 phân cảnh liên tiếp của Act I.
  - `When`: Hàm `assign_scene_layout_blueprint` sinh bố cục và props.
  - `Then`: Không có hai phân cảnh liền kề nào có tọa độ Hero hoặc Tool giống nhau (delta vị trí $\ge 15\%$); Scene 02 phải có cấu trúc dây tỏa tia radial $\ge 3$ nhánh; Scene 04 phải dùng trục thời gian timeline nằm ngang với `stamp_slam`; 100% test assertions PASS.
- **Trạng thái thực tế**: `PASS` (Verified: 2026-11-23 02:03:27) (Verified: 2026-11-21 16:26:52) (Khởi tạo: 2026-11-21)

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
