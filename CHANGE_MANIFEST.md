# 📝 [CHANGE_MANIFEST] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL

## 📌 1. Trạng Thái Thực Thi (Execution Metadata)
- **Author Role**: Builder / Implementer
- **Target Task**: `VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL`
- **Scope**: Nâng cấp khâu dựng Remotion với Frontier LLM Post-Production Director (`app/services/timeline_editor_agent.py`) và Canvas thị giác điện ảnh Continuous Storyboard Canvas (Seedance 2.5 / Veo style continuous transitions, continuous drift, macro orbit, seamless whip pan trong `remotion/src/index.tsx` & `VoxParallaxLayer.tsx`).
- **AST Py-Compile**: `EXIT CODE 0` (Verified on VPS Linux & Windows)
- **Zero Ghost Code**: `0 DEFECTS` (Verified by `ghost_code_detector.py`)

---

## 📂 2. Chi Tiết File Sửa Đổi (Line-Level Changes)

### A. Core Pipeline & AI Editorial Intelligence
1. **`app/services/timeline_editor_agent.py`**:
   - Tích hợp `llm_timeline_director_review()` gọi `ModelGateway` (`gpt-6-astra` primary, `claude-opus-5` fallback) phân tích kịch bản 5-Beat và timeline cảnh.
   - Thẩm định và chỉ đạo: dynamic pacing curve, continuous camera momentum, high-impact reveals, rule 136 clean lower-thirds.
   - Cơ chế Graceful Fallback: timeout 35s, nếu API lỗi tự động fallback về heuristic rules mà không làm gián đoạn pipeline.
   - Lưu trữ audit artifact `/var/vf/episodes/{episode_id}/llm_director_review.json`.
   - Kết hợp an toàn với Heuristic Safety Gates: Word-locked punches, visual monotony breaker, dead air elimination, 2.5D parallax flags.
2. **`app/services/build_remotion_props.py`**:
   - Tại dòng 782, truyền đầy đủ context `options={"episode_id": episode_id, "brain_input_path": brain_input_path, "segments_path": segments_path}` vào `audit_and_optimize_timeline()`.

### B. Remotion Visual Engine & Continuous Storyboard Canvas
3. **`remotion/src/index.tsx`**:
   - Mở rộng `computeCameraTransform` hỗ trợ 4 chuyển động máy liên tục:
     * `continuous_drift`: Smooth continuous camera glide (pan & slow zoom với cubic bezier easing) loại bỏ hiện tượng giật khựng giữa các cảnh.
     * `seamless_whip_pan`: Lateral swipe tốc độ cao trong 6 frame đầu lắng dần vào chuyển động trôi êm ái.
     * `macro_orbit`: Quỹ đạo elip 2.5D xoay quanh bằng chứng trọng tâm.
     * `cinematic_orbit`: Góc nghiêng tinh tế kết hợp zoom đẩy nhẹ.
4. **`remotion/src/components/vox/VoxParallaxLayer.tsx`**:
   - Bổ sung differential offset tính toán độc lập cho 3 lớp độ sâu (`background` 0.8x, `midground` 1.0x, `foreground` 1.25x) tương thích hoàn hảo với `continuous_drift`, `seamless_whip_pan`, `macro_orbit`, `cinematic_orbit`.

### C. Test Harness
5. **`tests/test_timeline_editor_agent.py`**:
   - 7 bài kiểm thử chuyên sâu bao phủ toàn diện:
     * `test_clean_speaker_tags_rule_136`
     * `test_visual_monotony_breaker`
     * `test_dead_air_elimination`
     * `test_word_locked_camera_punch`
     * `test_continuous_camera_movements_support`
     * `test_llm_director_review_fallback_on_error`
     * `test_llm_director_review_success_merging`

---

## 🧹 3. Cam Kết Dọn Rác & Zero-Ghost (Rule 119 & 125)
- [x] Không để lại file tạm rác trong `/tmp/` (đã xóa sạch file trung gian).
- [x] Không tạo file `.bak*`, `.backup*`, file shadow code.
- [x] Đã đồng bộ comment/docstring nội hàm (Rule 125 Single Truth).
- [x] `python3 -m py_compile` đạt Exit Code 0 trên cả VPS và Local.
