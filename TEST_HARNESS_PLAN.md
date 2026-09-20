# 🧪 [TEST_HARNESS_PLAN] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL

## 🎯 1. Chiến Lược Kiểm Thử (Test Strategy)
- **Mục tiêu**: Thẩm định toàn diện 2 tính năng nâng cấp mà không gây bất kỳ hồi quy nào lên Audio Spine (Rule 120), tốc độ render VPS, hay tính tất định của Remotion (Rule 122).
- **Nguyên tắc**: ISO Neighbor-Testing `[N-1, N, N+1]`, Live Runtime Execution (Rule 127), Zero Ghost Code (Rule 125), Quorum 4/4 Unanimous Pass trước Three-Way Sync (Rule 126).

---

## 📋 2. Ma Trận Kiểm Thử (Test Matrix)

| Test ID | Hạng mục kiểm thử | Đối tượng / Lệnh thực thi | Tiêu chí PASS (Acceptance Criteria) |
| :--- | :--- | :--- | :--- |
| **UT-01** | **Timeline Editor Agent Unit Test** | `pytest tests/test_timeline_editor_agent.py` | - Pacing dead-air detection: phát hiện và xử lý đoạn > 4.0s.<br>- Word-locked camera punch: tính đúng frame offset theo Whisper ms.<br>- Monotony breaker: tái cấu trúc khi có > 2 overlay cùng loại.<br>- Graceful Fallback: trả về props hợp lệ khi LLM mock lỗi. |
| **UT-02** | **Remotion TypeScript Bundle** | `npx --prefix /root/video_factory/remotion remotion bundle src/index.tsx /tmp/bundle_test` | Exit code 0, 0 lỗi cú pháp JSX/TS, zero missing imports. |
| **UT-03** | **Anti-OOM & Memory Leak Test** | `npx remotion still TwoLayerEpisode /tmp/test_parallax_still.jpg --frame=150` | Exit code 0, thời gian render frame $\le$ 3.0s, RAM Chromium $\le$ 800MB. |
| **NT-01** | **Neighbor Testing B3 ⇄ B6 ⇄ B7** | `python3 tests/ci_neighbor_tester.py` | Schema `remotion_props.json` khớp 100% với `PIPELINE_CONTRACTS.md`. Không vi phạm Rule 128 (Generic Contract). |
| **NT-02** | **Audio Spine Protection Gate** | `python3 -c "from app.services.beat_tts_engine import ..."` | Thời lượng frame tích lũy từ Whisper timestamps không lệch > 0.1s so với audio gốc (Rule 120). |
| **GH-01** | **Ghost Code Hunter Gate (Rule 125)** | `python3 scripts/orchestrator/ghost_code_detector.py` | 0 file `.bak*`, 0 dead imports, 0 orphan scripts, 0 defect. |
| **SM-01** | **CI Master Smoke Gate** | `python3 scripts/orchestrator/runner.py --mode ci` | 100% CI Quality Gates (ISO Neighbor + E2E Smoke) đều trả PASS. |

---

## 🔬 3. Phương Án Dự Phòng (Remediation & Fallback)
1. **Nếu AI Timeline Editor gặp rate-limit / timeout từ LLM API**:
   - `build_remotion_props.py` tự động kích hoạt fallback sang deterministic mapping trong vòng 500ms mà không làm gián đoạn dây chuyền (Rule 118).
2. **Nếu WebGL Shader hoặc Three.js ngốn quá 1.5GB RAM trên VPS**:
   - Chuyển `VoxAtmosphericLighting` sang thuần 2D canvas particle với bước nhảy 12fps, đảm bảo an toàn tuyệt đối cho Chromium headless.
