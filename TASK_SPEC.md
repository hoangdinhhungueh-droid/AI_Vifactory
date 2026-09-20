# 📐 [TASK_SPEC] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR_COUNCIL

## 📌 1. Bối Cảnh & Ranh Giới (Context & Boundaries)
- **Feature Title**: AI Senior Post-Production Editor (Timeline Assembly LLM Gate) & Vox 2.5D Parallax Cinematic Canvas
- **Primary Blocks Impacted**:
  - `B6.0` (`app/services/timeline_editor_agent.py` [MỚI]): Agent Đạo diễn Hậu kỳ LLM nhận định song song trong khâu dựng.
  - `B6.5` (`app/services/build_remotion_props.py` & `scripts/build_remotion_props.py`): Tích hợp Timeline Editor Gate với cơ chế Graceful Fallback.
  - `B7.0` (`remotion/src/components/vox/VoxAtmosphericLighting.tsx` [MỚI]): Ánh sáng điện ảnh & hạt bụi không gian (Dust Motes & Light Sweeps 12fps).
  - `B7.1` (`remotion/src/components/vox/VoxParallaxLayer.tsx` [MỚI]): Chiều sâu lập thể 2.5D Multi-Plane Parallax (BG 0.8x, Midground 1.0x, FG 1.25x).
  - `B7.2` (`remotion/src/index.tsx`): Tích hợp Atmospheric Lighting & 2.5D Parallax vào `TwoLayerEpisode`.
- **In-Scope**:
  - Tự động hóa đánh giá nhịp dựng (Pacing Audit): phát hiện dead air > 4.0s không có biến đổi thị giác để tự động chêm micro-motion hoặc đổi góc máy.
  - Khóa góc máy theo từ khóa giọng nói thực tế (Word-Locked Camera Punch) dựa trên Whisper word-level timestamps (`whisper_segments.json`).
  - Khử triệt để sự đơn điệu thị giác (Visual Monotony Breaker): tự động chuyển hướng khi có > 2 cảnh cùng dùng 1 loại overlay liên tiếp.
  - Bổ sung hiệu ứng 2.5D Parallax và Atmospheric Lighting đạt chuẩn điện ảnh (như Seedance/Veo) mà vẫn giữ 100% độ sắc nét pháp y và tính nhẹ nhàng trên CPU VPS (Rule 119, Rule 120, Rule 122).
  - Lập đủ bộ 3 Cặp Docs Pháp Lý Hội Đồng theo `/vf-pipeline-teamwork` và nghiệm thu Three-Way Sync (Rule 126).
- **Non-Goals**:
  - Không thay thế Remotion bằng mô hình video diffusion (Veo/Seedance) để tránh ảo giác chữ số (Rule 130).
  - Không gọi LLM frame-by-frame trong lúc render Chromium (chỉ can thiệp ở tầng Timeline Metadata Assembly trước render).
  - Không phá vỡ cấu trúc Audio Spine B2.6 / B3 (Rule 120 Hard Gate).
  - Không sử dụng CSS `transition`, `@keyframes` hay `backdropFilter: blur()` gây sụt giảm FPS.

---

## 🎯 2. Yêu Cầu Kỹ Thuật (Requirements R1 - R6)
- **R1 (AI Timeline Editor Module)**: Xây dựng `app/services/timeline_editor_agent.py` nhận `director_plan.json`, `whisper_segments.json`, `images/manifest.json`. Tự động phân tích pacing, đề xuất tinh chỉnh nhịp cắt, chèn micro-SFX cues và word-locked camera punches.
- **R2 (Assembly Integration & Graceful Fallback)**: Tích hợp vào `build_remotion_props.py`. Nếu cờ `--enable-ai-editor` được bật (mặc định cho sản xuất), gọi Editor Agent; nếu LLM gặp timeout hoặc rate-limit, tự động fallback về deterministic mapping без lỗi (Rule 118).
- **R3 (Vox Atmospheric Lighting Component)**: Xây dựng `remotion/src/components/vox/VoxAtmosphericLighting.tsx` render hạt bụi ánh sáng điện ảnh (Cinema Dust Motes 12fps) và tia sáng mềm (Volumetric Light Sweep) bằng pure Remotion math (`useCurrentFrame` + `interpolate`).
- **R4 (Vox 2.5D Multi-Plane Parallax Layer)**: Xây dựng `remotion/src/components/vox/VoxParallaxLayer.tsx` hỗ trợ 3 tầng độ sâu dịch chuyển vi sai theo camera Remotion: Background Canvas (0.8x), Evidence Prop (1.0x), Foreground Cutout (1.25x).
- **R5 (Integration & Anti-OOM Guard)**: Tích hợp an toàn vào `TwoLayerEpisode` trong `remotion/src/index.tsx`, duy trì kiểm thử `npx remotion bundle` đạt Exit Code 0, tiêu thụ RAM Chromium $\le$ 1GB.
- **R6 (Council Quorum & Three-Way Physical Sync)**: Hoàn thiện hồ sơ Hội đồng 4 vai, chạy `ghost_code_detector.py` đạt 0 defects, test suites pass 100%, đồng bộ VPS ⇄ GitHub ⇄ Local (Rule 126).

---

## 🔒 3. Khế Ước Dữ Liệu (Interface Contracts)
- **Timeline Editor Input Contract**:
  ```json
  {
    "director_plan": { "scenes": [...] },
    "whisper_segments": [ { "start_ms": 0, "end_ms": 2500, "word": "The", "confidence": 0.98 }, ... ],
    "image_manifest": [ { "reuse_key": "...", "local_path": "..." } ]
  }
  ```
- **Timeline Editor Output Contract (Enhanced `remotion_props.json`)**:
  ```json
  {
    "scenes": [
      {
        "durationInFrames": 242,
        "cameraMovement": "slow_push_in",
        "tensionLevel": "high",
        "wordLockedPunches": [
          { "word": "FRAUD", "frame_offset": 84, "camera": "snap_zoom", "sfx_cue": "stamp_slam" }
        ],
        "forensicOverlay": {
          "type": "kinetic_counter",
          "layout": "full_bleed_focus",
          "parallaxDepth": "midground",
          "atmosphericDust": true
        }
      }
    ]
  }
  ```
