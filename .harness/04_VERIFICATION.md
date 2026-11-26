# 🧪 04_VERIFICATION.md - MA TRẬN KIỂM THỬ VIDEO PIPELINE

> **NGHIỆM THU THỰC THI CHƯƠNG TRÌNH SỐNG (PROGRAMMATIC RUNTIME EXECUTION GATE).**
> Cấm nghiệm thu bằng `py_compile` suông. Mọi thay đổi bắt buộc qua CI Lint, AST Rule 139, Ghost Scan, Semantic Bias, Unit Tests, E2E Smoketest và nghiệm thu thực tế trên tập `EN_EP0269_tjx_tariff_refund_trap`.

---

### [TEST-301] Kiểm thử Voice-First Papertrails Director & Contracts (Mã FT-301)
- **Mã Feature**: `FT-301`
- **Test File**: `tests/unit/test_papertrails_voice_first.py`
- **Lệnh chạy kiểm thử (CLI)**: `pytest -v tests/unit/test_papertrails_voice_first.py`
- **Tiêu chuẩn Gherkin (Acceptance Criteria)**:
  - `Given`: Tập từ vựng đo thực tế (`segments` kèm `words`), bảng 36 `VALID_PROPS`, tiêu đề chứa mã rò rỉ.
  - `When`: Gọi `_sanitize_viewer_title()`, `_normalize_llm_shots_to_words()`, `build_papertrails_timeline()`, `audit_papertrails_timeline_antipatterns()`.
  - `Then`: Tiêu đề sạch 100% không còn mã nội bộ (`Rule 136`); các shot phủ kín `0..duration` không lặp `(biome, prop)` hoặc `camera` tĩnh; 13 prop điều tra mới (`hanko-stamp`, `brass-caliper`, `forensic-loupe` + 10 props) thuộc `VALID_PROPS`; Timing Sheet + `foley_cues` nằm gọn trong biên cảnh.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-302] Kiểm thử Papertrails Stills Gate, Parallel Renderer (`--quality vox`) & VPS Bridge (Mã FT-302)
- **Mã Feature**: `FT-302`
- **Lệnh kiểm thử (CLI)**:
  - Trên VPS: `node --check /root/video_factory/vox/papertrails_engine/scripts/render_parallel.mjs && cd /root/video_factory/vox/papertrails_engine && npm run build`
  - Live Stills & Render Gate: `python -m orchestrator.run_pipeline --run-id <RUN_ID> --preset story_forensic --only s08_video_gen --stills-only --force`
- **Tiêu chuẩn Gherkin**:
  - `Given`: `timeline.json` (`1920x1080`) và `voice_narration.mp3` chuẩn EBU R128.
  - `When`: Chạy `--stills-only` rồi chạy `render_parallel.mjs --quality vox --render-fps 15 --frame-format jpeg --workers 2`.
  - `Then`: Sinh đủ ảnh `stills/*.png` kiểm định thị giác không freeze/artifact; video hợp nhất đạt `1920x1080`, đúng số frame `30fps CFR`, `repeatFrameStable=true`, luồng H.264/AAC.
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [TEST-303] Kiểm thử CI Toàn Hệ Thống & Chống Hồi Quy (Rules 125, 127, 128, 139)
- **Lệnh chạy kiểm thử (CLI)**:
  - `ruff check --select F821,F811 app/ scripts/ stages/ vox/ core/ tools/`
  - `python tools/ghost_scan.py`
  - `python scripts/forensics/probe_ast_rule139.py`
  - `python scripts/forensics/probe_zero_mock.py`
  - `pytest -v tests/test_zero_semantic_bias.py tests/test_contracts.py tests/test_human_gates.py tests/unit/test_s05_director_plan.py tests/unit/test_s10_render.py tests/unit/test_papertrails_voice_first.py`
  - `python scripts/e2e_pipeline_smoketest.py`
- **Trạng thái thực tế**: `READY_FOR_VERIFICATION`

---

### [LEGACY-COMPAT] Bộ Kiểm Thử Tương Thích Ngược (Hermetic `e2e_min` Only)
- `tests/test_contracts.py`, `tests/test_human_gates.py`, `tests/unit/test_s05_director_plan.py`, `tests/unit/test_s10_render.py`, `tests/test_temporal_motion_gate.py` — giữ nguyên PASS bảo toàn hợp đồng `StageID` và helper xuất khẩu.
