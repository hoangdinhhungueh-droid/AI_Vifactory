# 🧪 [TEST_HARNESS_PLAN] HYBRID_VOX_VEO_FORENSIC_PAPER_ANIMATION_PIPELINE

## 🎯 1. Chiến Lược Kiểm Thử (Test Strategy)
- **Mục tiêu**: Đảm bảo sự toàn vẹn của luồng B3 -> B6.5 kết hợp Veo 3.1 I2V Stop-Motion và Remotion Audio Spine.
- **Phạm vi bao phủ**:
  1. Python AST Compilation & Pytest Suite.
  2. B4.5 Composite Seed Generation (16:9 + 1:1 with 3D drop-shadow).
  3. B5.0 Empirical Visual Audit 4 Trục (Rule 122).
  4. Remotion Bundle & Still Render Check.
  5. 4-Layer Zero-Ghost Code Scan (Rule 125 & 134).
  6. Three-Way Physical Parity (VPS ⇄ GitHub ⇄ Local).

---

## 📊 2. Ma Trận Test Cases
| ID | Hạng Mục Kiểm Thử | Lệnh Thực Thi (Command) | Kết Quả Kỳ Vọng | Tiêu Chuẩn Nghiệm Thu |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Python AST Compilation | `python3 -m py_compile app/services/build_remotion_props.py app/services/unified_vox_director.py app/services/composite_generator.py scripts/flow_video_dispatcher.py` | Exit Code 0 | 100% Cú pháp chuẩn |
| **TC-02** | Unit & Neighbor Suite | `pytest tests/test_build_remotion_props.py tests/test_b3_vox_editorial.py -v` | 9/9 Passed, Exit 0 | Rule 134 Invariant Parity |
| **TC-03** | Composite Seed Integrity | `python -m app.services.composite_generator --episode-id EN_EP0004_amazon_ad_lawsuit` | 20/20 Seeds Generated | 1080p, drop-shadow, no distortion |
| **TC-04** | Live Veo 3.1 I2V Peel Test | Flow Video Dispatcher Playwright + CDP Stream Download | `veo_forensic_corner_peel_test.mp4` | 8s video, 0% photoreal humans |
| **TC-05** | Pixel-Level Visual Audit | `view_file` trên multi-timestamp frames (0.5s, 1.5s, 3.0s, 4.5s, 6.0s, 7.5s) | 4 Trục Đạt 10/10 PASS | Rule 122 Visual Audit Gate |
| **TC-06** | Remotion TypeScript Bundle | `cd remotion && npx remotion bundle src/index.tsx /tmp/bundle_test` | Bundling 100%, Exit 0 | 0 TS/Webpack errors |
| **TC-07** | Remotion Still Render | `npx remotion still src/index.tsx TwoLayerEpisode /tmp/frame_audit_300.jpg` | Rendered 1/1, Exit 0 | 1080p frame, Foleys & UI tags |
| **TC-08** | Automated 4-Layer Ghost Scan | `python3 scripts/orchestrator/ghost_code_detector.py` | 0 defects, Exit 0 | Rule 125 & 134 Veto Authority |
