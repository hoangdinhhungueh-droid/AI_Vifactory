# 📐 [TASK_SPEC] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL

## 📌 1. Bối Cảnh & Ranh Giới (Context & Boundaries)
- **Feature Title**: Frontier LLM Post-Production Director Gate (`timeline_editor_agent.py`) & Vox Object-Driven Continuous Storyboard Canvas (`Remotion`)
- **Target Task ID**: `GENERIC_EP_RENDER_TIMELINE_DIRECTOR` (Pattern: `^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$`)
- **Primary Blocks Impacted**:
  - `B6.0` (`app/services/timeline_editor_agent.py`): Tích hợp Frontier LLM (`gpt-6-astra` / `claude-opus-5` via `ModelGateway`) thẩm định song song 5-Beat script đối chiếu với timeline scenes để chỉ đạo nhịp dựng (pacing, cuts, camera movement, transitions, evidence staging) kèm cơ chế resilient fallback (<=35s timeout).
  - `B6.5` (`app/services/build_remotion_props.py`): Truyền đầy đủ episode context (`episode_id`, `story.txt`, `segments_path`) vào `audit_and_optimize_timeline()`.
  - `B7.0` (`remotion/src/index.tsx` & `src/components/vox/VoxParallaxLayer.tsx`): Nâng cấp Continuous Storyboard Canvas (Seedance 2.5 / Veo style continuous transitions, continuous drift, macro orbit, seamless whip pan, object-driven evidence tracking).
- **In-Scope**:
  - Frontier LLM Director invocation (`gpt-6-astra` primary, `claude-opus-5` fallback) phân tích kịch bản 5 Beat và các cảnh đã gán để ra quyết định đạo diễn vi mô (camera, pacing, tension, transitions, lower-thirds).
  - Xuất audit log `/var/vf/episodes/{episode_id}/llm_director_review.json` ghi nhận toàn bộ lý do nghệ thuật và các điều chỉnh cảnh.
  - Heuristic fallback bảo vệ 100% thời gian hoạt động: nếu API timeout (>35s) hoặc lỗi mạng, tự động kích hoạt bộ quy tắc heuristic xác định (pacing, monotony breaker, word-locked camera punches, Rule 136 clean tags).
  - Continuous Storyboard Canvas: hỗ trợ các chuyển động máy liên tục (`continuous_drift`, `seamless_whip_pan`, `macro_orbit`, `cinematic_orbit`) không bị giật khựng giữa các scene cùng bối cảnh.
  - Multi-Plane Parallax (0.8x BG, 1.0x Midground, 1.25x FG) tương thích hoàn toàn với các chuyển động máy mới.
- **Non-Goals**:
  - Không can thiệp hoặc làm gián đoạn tiến trình render đang chạy trên VPS (`JP_EP0003_hamaoka_data_fraud`).
  - Không gọi LLM frame-by-frame trong Chromium (chỉ can thiệp ở tầng Timeline Metadata Assembly trước render).
  - Không phá vỡ cấu trúc Hollywood Audio Spine B2.6 / B3 (Rule 120 Hard Gate).
  - Không sử dụng CSS transition hoặc backdropFilter gây sụt giảm FPS trên CPU VPS.

---

## 🎯 2. Yêu Cầu Kỹ Thuật (Requirements R1 - R6)
- **R1 (Frontier LLM Director Gate)**: Xây dựng hàm `llm_timeline_director_review()` trong `timeline_editor_agent.py` gọi `ModelGateway` (`gpt-6-astra` / `claude-opus-5`) phân tích 5 Beat story (`story.txt`) và scene list, trả về cấu trúc JSON chỉ đạo đạo diễn vi mô.
- **R2 (Resilient Hybrid Fallback & Merging)**: Tự động merge các chỉ đạo của LLM với các chốt chặn an toàn heuristic (Word-locked punches, Monotony breaker, Rule 136 regex cleanup). Timeout 35s bảo vệ tuyệt đối không nghẽn pipeline.
- **R3 (Continuous Storyboard Canvas in Remotion)**: Mở rộng `computeCameraTransform` trong `remotion/src/index.tsx` và `VoxParallaxLayer.tsx` hỗ trợ `continuous_drift`, `seamless_whip_pan`, `macro_orbit`, `cinematic_orbit` tạo nhịp chuyển cảnh mượt mà chuẩn Seedance 2.5 / Veo.
- **R4 (Assembly Pipeline Wiring)**: Cập nhật `build_remotion_props_data()` truyền đầy đủ `episode_id` và context vào `audit_and_optimize_timeline()`.
- **R5 (Automated Test Suites & Zero-Ghost)**: Bổ sung unit tests cho LLM Director & Heuristic Fallback trong `tests/test_timeline_editor_agent.py`, bảo đảm `pytest` pass 100%, `ghost_code_detector.py` 0 defects.
- **R6 (Council Quorum & Three-Way Physical Sync)**: Hoàn tất 3 Cặp Docs Pháp Lý, Quorum 4/4 Unanimous Pass, commit & push VPS ⇄ GitHub Actions CI (success) ⇄ Local Windows parity (Rule 126).

---

## 🔒 3. Khế Ước Giao Diện (Interface Contracts)
- **Timeline Editor Input Contract**:
  ```json
  {
    "scenes": [
      {
        "scene_id": "sc_01",
        "durationInFrames": 180,
        "narration": "...",
        "background": "...",
        "foreground": "...",
        "cameraMovement": "slow_push_in"
      }
    ],
    "whisper_words": [ { "word": "...", "start_ms": 0, "end_ms": 300 } ],
    "options": {
      "episode_id": "JP_EP0003_hamaoka_data_fraud",
      "enable_llm_director": true,
      "model": "gpt-6-astra"
    }
  }
  ```
- **Timeline Editor Output Contract (`remotion_props.json`)**:
  ```json
  {
    "scenes": [
      {
        "scene_id": "sc_01",
        "durationInFrames": 180,
        "cameraMovement": "continuous_drift",
        "tensionLevel": "high",
        "transition": "continuous_whip",
        "wordLockedPunches": [...],
        "forensicOverlay": {...},
        "speakerTag": "TÊN // VAI TRÒ"
      }
    ]
  }
  ```

---

## ⚖️ 4. Đánh Đổi Kiến Trúc & Rủi Ro (Rule 129 Trade-Offs)
- **Option A (Chỉ dùng Heuristic Rules)**: Nhanh (0.1s), không tốn token, nhưng thiếu tư duy cảm xúc và nhịp thở đạo diễn điện ảnh theo từng mạch truyện.
- **Option B (Frontier LLM Director + Heuristic Safety Gate - LỰA CHỌN TỐI ƯU)**: Gọi `gpt-6-astra` (hoặc `claude-opus-5`) thẩm định kịch bản và timeline trước khi render. Nếu API timeout (>35s) hoặc lỗi, tự động fallback ngay về Option A. Độ trễ assembly chấp nhận được (3-10s), đạt chất lượng đạo diễn đẳng cấp mà vẫn đảm bảo 100% độ tin cậy vận hành.
