# 🧪 04_VERIFICATION.md - MA TRẬN KIỂM THỬ VIDEO PIPELINE

> **NGHIỆM THU THỰC THI CHƯƠNG TRÌNH SỐNG (PROGRAMMATIC RUNTIME EXECUTION GATE).**
> Cấm nghiệm thu bằng `py_compile` suông. Mọi thay đổi bắt buộc qua CI Lint, AST Rule 139, Ghost Scan, Semantic Bias, Unit Tests, E2E Smoketest và nghiệm thu thực tế trên tập `EN_EP0269_tjx_tariff_refund_trap`.

---

### [TEST-301] Kiểm thử Voice-First Papertrails Director & Contracts (Mã FT-301)
- **Mã Feature**: `FT-301`
- **Test File**: `tests/unit/test_papertrails_voice_first.py`
- **Lệnh chạy kiểm thử (CLI)**: `pytest -v tests/unit/test_papertrails_voice_first.py tests/unit/test_s01_s04_system_remediation.py`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Tập từ vựng đo thực tế (`segments` kèm `words`), bảng 36 `VALID_PROPS`, tiêu đề chứa mã rò rỉ, hoặc cụm từ ASR tách sai tên riêng (`many-to-one`).
  - `When`: Gọi `_sanitize_viewer_title()`, `_normalize_llm_shots_to_words()`, `build_papertrails_timeline()`, `direct_papertrails_timeline_with_llm()`, `audit_papertrails_timeline_antipatterns()`, và `_reconcile_script_casing_onto_whisper()`.
  - `Then`: `timeline["stageMode"] == "forensic_desk"`; tiêu đề sạch 100% không còn mã nội bộ (`Rule 136`); các shot phủ kín `0..duration` không lặp `prop` hoặc `(biome, prop)` hoặc `camera` tĩnh liền kề; shot `>= 12` đạt tối thiểu `20%` `note` cards bằng ngôn ngữ bản địa; `_reconcile_script_casing_onto_whisper` khôi phục 100% tên riêng đã duyệt không làm lệch mốc thời gian; Timing Sheet + `foley_cues` nằm gọn trong biên cảnh.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-302] Kiểm thử Papertrails Stills Gate, Parallel Renderer (`--quality vox`) & VPS Bridge (Mã FT-302)
- **Mã Feature**: `FT-302`
- **Lệnh kiểm thử (CLI)**:
  - Trên VPS: `node --check /root/video_factory/vox/papertrails_engine/engine/src/video/print_textures.js && node --check /root/video_factory/vox/papertrails_engine/engine/src/video/forensic_desk.js && node --check /root/video_factory/vox/papertrails_engine/scripts/render_parallel.mjs`
  - Live Stills & Render Gate: `python -m orchestrator.run_pipeline --run-id <RUN_ID> --preset story_forensic --only s08_video_gen --stills-only --force`
- **Tiêu chuẩn Gherkin**:
  - `Given`: `timeline.json` (`1920x1080`, `stageMode: "forensic_desk"`) và `voice_narration.mp3` chuẩn EBU R128.
  - `When`: Chạy `--stills-only` rồi chạy `render_parallel.mjs --quality vox --render-fps 15 --frame-format jpeg --workers 2`.
  - `Then`: Sinh đủ ảnh `stills/*.png` 3D Bàn Hồ Sơ Vox (`0%` cây cối cổ tích), prop 3D in trực tiếp chữ/số liệu sắc nét, không bị Note Card che khuất; video hợp nhất đạt `1920x1080`, đúng số frame `30fps CFR`, `repeatFrameStable=true`, luồng H.264/AAC.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-205] Kiểm thử Master QC Gate & Timeline Integrity (Mã FT-205)
- **Mã Feature**: `FT-205`
- **Test File**: `tests/unit/test_s11_qc_gate.py`
- **Lệnh chạy kiểm thử (CLI)**: `pytest -v tests/unit/test_s11_qc_gate.py`
- **Tiêu chuẩn Gherkin**:
  - `Given`: Master video `final.mp4`, EBU R128 bounds, và `director_plan.json` / `remotion_props.json`.
  - `When`: Chạy `stages/s11_qc.py:run()` và `verify_final_video_gates()`.
  - `Then`: Kiểm toán H.264/AAC, 0 black frames, độ trôi thời lượng trong biên, loudness đạt `[-17.0, -15.0] LUFS` & `<= -2.0 dBTP`.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-303] Kiểm thử Voice-First ASR Alignment, Foley Mixer & CI Toàn Hệ Thống (Mã FT-303)
- **Mã Feature**: `FT-303`
- **Test File**: `tests/unit/test_s01_s04_system_remediation.py`, `tests/unit/test_s10_render.py`
- **Lệnh chạy kiểm thử (CLI)**: `pytest -v tests/unit/test_s01_s04_system_remediation.py tests/unit/test_s10_render.py tests/unit/test_papertrails_voice_first.py tests/test_zero_semantic_bias.py`
- **Lệnh kiểm định mở rộng (CLI)**:
  - `ruff check --select F821,F811 app/ scripts/ stages/ vox/ core/ tools/`
  - `python tools/ghost_scan.py`
  - `python scripts/forensics/probe_ast_rule139.py`
  - `python scripts/forensics/probe_zero_mock.py`
  - `python scripts/e2e_pipeline_smoketest.py`
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [LEGACY-COMPAT] Bộ Kiểm Thử Tương Thích Ngược (Hermetic `e2e_min` Only)
- `tests/test_contracts.py`, `tests/test_human_gates.py`, `tests/unit/test_s05_director_plan.py`, `tests/unit/test_s10_render.py`, `tests/test_temporal_motion_gate.py` — giữ nguyên PASS bảo toàn hợp đồng `StageID` và helper xuất khẩu.
