# 🔌 03_WIRING.md - SƠ ĐỒ ĐẤU NỐI PIPELINE (ANTI-ORPHAN CODE)

> **CHỐNG BỎ QUÊN TÍNH NĂNG & DỊCH VỤ MỒ CÔI.**
> Mọi stage code và service bắt buộc phải được gọi bởi orchestrator chính `orchestrator/run_pipeline.py`.
> Bất kỳ hàm nào không có caller hợp lệ sẽ bị `harness_guard.py check` đánh trượt ngay lập tức.

---

## 1. MA TRẬN ĐẤU NỐI THỰC THI (CALLER WIRING MATRIX)

| Feature ID | Service / Hàm | File Code | Caller File (Nơi gọi) | Vị trí / Điều kiện kích hoạt | Lệnh CLI Thực Thi Đích Danh |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[FT-201]` | `generate_master_sheet_bundle` | `app/services/master_scene_sheet.py` | `stages/s07_image_gen.py` | Kích hoạt trong Stage S07 khi sinh tài sản thị giác phân cảnh | `python -m orchestrator.run_pipeline --only s07_image_gen` |
| `[FT-202]` | `run` | `stages/s05_director_plan.py` | `orchestrator/run_pipeline.py` | Kích hoạt tại Stage S05 sau khi kịch bản được phê duyệt | `python -m orchestrator.run_pipeline --only s05_director_plan` |
| `[FT-203]` | `run` | `stages/s08_video_gen.py` | `orchestrator/run_pipeline.py` | Kích hoạt tại Stage S08 để sinh các plate chất liệu xúc giác từ Omni | `python -m orchestrator.run_pipeline --only s08_video_gen` |
| `[FT-204]` | `run` | `stages/s10_render.py` | `orchestrator/run_pipeline.py` | Kích hoạt tại Stage S10 để kết xuất video tổng thành Remotion | `python -m orchestrator.run_pipeline --only s10_render` |
| `[FT-205]` | `run` | `stages/s11_qc.py` | `orchestrator/run_pipeline.py` | Kích hoạt tại Stage S11 để kiểm toán chất lượng và đồng bộ Chapter | `python -m orchestrator.run_pipeline --only s11_qc` |
| `[FT-206]` | `assign_scene_layout_blueprint` | `app/services/scene_layout_director.py` | `stages/s05_director_plan.py` | Kích hoạt tại S05/S10 để gán bố cục không gian bất đối xứng và topology dây nối riêng biệt | `python -m pytest tests/test_dynamic_layout_archetypes.py -v` |
| `[FT-207]` | `build_continuous_desk_world` | `app/services/desk_world_director.py` | `stages/s10_render.py` | Kích hoạt tại Stage S10 để kết xuất video hành trình camera qua bàn điều tra liên tục DeskWorld | `python -m pytest tests/test_desk_world_director.py -v` |

---

## 2. CALL-CHAIN FLOWCHART TỔNG THỂ & HẠ TẦNG BROWSER FLEET

```mermaid
flowchart TD
    MAIN["orchestrator/run_pipeline.py:main()"] --> ORCH["orchestrator/run_pipeline.py:run_pipeline()"]
    
    ORCH --> S05["[FT-202] stages/s05_director_plan.py:run()<br/>(Phân rã 5 tầng Prompt: Assembled Anchor, Hero Cutout, Tool, Stage, Motion Coupling)"]
    
    S05 --> S06["stages/s06_critic_visual.py:run()<br/>(DACL Visual Loop: Claude Opus 5.5 ⇄ GPT-6-Astra >= 8.0/10 -> Bắn Telegram HG2)"]
    
    S06 --> FLEET_IMG["scripts/gemini_browser_gen.py --episode &lt;EP_ID&gt; --acc all<br/>(Playwright xoay vòng 6 Chrome Profiles acc_01..acc_07 sinh ảnh seed thật 2560x1440)"]
    
    FLEET_IMG --> S07["stages/s07_image_gen.py:run()"]
    S07 --> MS["[FT-201] app/services/master_scene_sheet.py:generate_master_sheet_bundle()<br/>(Xác thực SHA256 ảnh seed + Cắt tách Alpha Layers: hero, stat, tool, stage)"]
    
    S07 --> FLEET_VID["scripts/flow_video_dispatcher.py --episode &lt;EP_ID&gt; --model omni<br/>(Google Flow 7 Acc I2V sinh living texture plates: paper grain, CRT scanlines)"]
    
    FLEET_VID --> S08["[FT-203] stages/s08_video_gen.py:run()<br/>(Kiểm định độ biến thiên pixel validate_video_motion_temporal_delta >= 0.5)"]
    
    S08 --> S09["stages/s09_voice_tts.py:run()<br/>(Tạo Audio ElevenLabs & Whisper Timestamps 0ms drift)"]
    
    S09 --> S10["[FT-204] stages/s10_render.py:run()<br/>(Remotion Master Director: Khung máy tính cố định 1920x1080,<br/>layer vào nhanh cùng 1 chiều X, vẽ chỉ đỏ khóa khớp 2 chủ thể)"]
    
    S10 --> S11["[FT-205] stages/s11_qc.py:run()<br/>(Đồng bộ YouTube Chapters từ Remotion Timeline thực tế)"]
```
