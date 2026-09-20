# 📝 [CHANGE_MANIFEST] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL

## 📌 1. Thông Tin Bản Thay Đổi (Change Metadata)
- **Author Role**: Builder / Implementer
- **Target Task**: `VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL`
- **Scope**: Nâng cấp khâu dựng Remotion với AI Senior Post-Production Editor Gate (`app/services/timeline_editor_agent.py`) và Canvas thị giác điện ảnh 2.5D Multi-Plane Parallax & Atmospheric Lighting (`VoxParallaxLayer.tsx`, `VoxAtmosphericLighting.tsx`).

---

## 📂 2. Danh Mục File Đã Thay Đổi (Touched Files)

### A. Core Pipeline & AI Editorial Intelligence
1. **[NEW] `app/services/timeline_editor_agent.py`**:
   - Agent Đạo diễn Hậu kỳ thẩm định và tối ưu hóa timeline trước khi render:
     * **Pacing Audit**: Phát hiện dead-air thị giác (>4.0s) để tự động chêm micro-motion hoặc đổi góc máy.
     * **Word-Locked Camera Punch**: Khóa góc máy (snap_zoom, slow_push_in) và micro-SFX cue chính xác theo từng mili-giây Whisper word timestamp (`whisper_segments.json`).
     * **Visual Monotony Breaker**: Tự động chuyển layout/hướng khi có > 2 cảnh cùng dùng 1 loại overlay liên tiếp.
     * **Clean Speaker Tags (Rule 136)**: Khử toàn bộ rò rỉ mã asset, reuse_key, hash, chỉ cho phép hiển thị `TÊN // VAI TRÒ` hoặc `BEAT <X>: <TIÊU ĐỀ>`.
     * **Graceful Fallback (Rule 118)**: Tự động fallback an toàn về deterministic props nếu LLM timeout hoặc gặp lỗi.
2. **[MODIFY] `app/services/build_remotion_props.py`**:
   - Tích hợp hàm `audit_and_optimize_timeline()` vào khâu lắp ráp `build_remotion_props()`.
   - Bổ sung cờ `--enable-ai-editor` (mặc định True trong pipeline sản xuất).

### B. Remotion Visual Engine & 2.5D Cinematic Canvas
3. **[NEW] `remotion/src/components/vox/VoxAtmosphericLighting.tsx`**:
   - Hạt bụi điện ảnh (Cinema Dust Motes) di chuyển với nhịp lượng tử 12fps bằng pure Remotion math (`steppedFrame = Math.floor(frame / 2.5) * 2.5`).
   - Quét sáng thể tích mềm (Volumetric Light Sweep) tạo không gian ánh sáng phim tài liệu điện ảnh đẳng cấp như Veo 2 / Seedance.
   - Không sử dụng CSS transition, không gây sụt giảm FPS trên headless Linux CPU.
4. **[NEW] `remotion/src/components/vox/VoxParallaxLayer.tsx`**:
   - Thùng chứa độ sâu 2.5D Multi-Plane Parallax phân tách 3 lớp chuyển động vi sai:
     * `background`: Hệ số 0.8x (tạo cảm giác không gian sâu thẳm).
     * `midground`: Hệ số 1.0x (evidence props, documents, maps).
     * `foreground`: Hệ số 1.25x (nhân vật cutout nổi bật về phía trước).
5. **[MODIFY] `remotion/src/index.tsx`**:
   - Bao bọc `BackgroundSegment` và `ForegroundLayer` trong `<VoxParallaxLayer depth="background">` và `<VoxParallaxLayer depth="foreground">`.
   - Bao bọc `OverlaySegmentView` trong `<VoxParallaxLayer depth="midground">`.
   - Bổ sung `<VoxAtmosphericLighting intensity={0.9} />` phủ trên video layer.

### C. Test Harness & Production Utilities
6. **[NEW] `tests/test_timeline_editor_agent.py`**:
   - 4 bài kiểm thử chuyên sâu: `test_clean_speaker_tags_rule_136`, `test_visual_monotony_breaker`, `test_dead_air_elimination`, `test_word_locked_camera_punch`.
7. **[NEW] `scripts/render_preview_2min.py`**:
   - Kịch bản render preview 2 phút đầu (3,600 frames) tích hợp FFmpeg Sidechain Ducking, trích xuất 5 frame pháp y và gửi trực tiếp Telegram.

---

## 🛡️ 3. Kiểm Tra Ghost Code & Biên Dịch (Rule 125 & Rule 127)
- `python3 -m py_compile app/services/timeline_editor_agent.py app/services/build_remotion_props.py scripts/render_preview_2min.py tests/test_timeline_editor_agent.py` ➔ **Exit code 0**
- `pytest tests/test_timeline_editor_agent.py` ➔ **4/4 PASSED (Exit code 0)**
- `npx remotion bundle src/index.tsx` ➔ **Exit code 0**
- `python3 scripts/render_twolayer_visual.py ... --frames 0-9` ➔ **10/10 frames rendered in 10.1s (Exit code 0)**
- `python3 scripts/orchestrator/ghost_code_detector.py` ➔ **0 ghost artifacts, 0 defect**
