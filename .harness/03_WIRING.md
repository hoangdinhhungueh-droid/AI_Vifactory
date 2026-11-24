# 🔌 03_WIRING.md - SƠ ĐỒ ĐẤU NỐI PIPELINE (ANTI-ORPHAN CODE)

> **CHỐNG BỎ QUÊN TÍNH NĂNG & DỊCH VỤ MỒ CÔI.**
> Mọi stage code và service bắt buộc phải được gọi bởi orchestrator chính `orchestrator/run_pipeline.py`.
> Bất kỳ hàm nào không có caller hợp lệ sẽ bị `harness_guard.py check` đánh trượt ngay lập tức.

---

## 1. MA TRẬN ĐẤU NỐI THỰC THI (CALLER WIRING MATRIX)

| Feature ID | Service / Hàm | File Code | Caller File (Nơi gọi) | Vị trí / Điều kiện kích hoạt | Lệnh CLI Thực Thi Đích Danh |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[FT-301]` | `build_papertrails_timeline` | `app/services/papertrails_director.py` | `stages/s05_director_plan.py` | Kích hoạt tại S05 sau khi chốt kịch bản tại HG1 và có giọng đọc S09 | `python -m orchestrator.run_pipeline --only s05_director_plan` |
| `[FT-302]` | `render_papertrails_on_vps` | `app/services/papertrails_vps_bridge.py` | `stages/s08_video_gen.py` | Kích hoạt tại S08 để render Playwright WebGL2 Three.js frame-by-frame trên VPS | `python -m orchestrator.run_pipeline --only s08_video_gen` |
| `[FT-303]` | `run` | `stages/s10_render.py` | `orchestrator/run_pipeline.py` | Kích hoạt tại S10 để đóng gói master video MP4 và xuất bản phẩm | `python -m orchestrator.run_pipeline --only s10_render` |
| `[FT-205]` | `run` | `stages/s11_qc.py` | `orchestrator/run_pipeline.py` | Kích hoạt tại S11 để kiểm toán chất lượng và đồng bộ Chapter từ timeline.json | `python -m orchestrator.run_pipeline --only s11_qc` |

---

## 2. CALL-CHAIN FLOWCHART TỔNG THỂ (CANONICAL 2.0 PAPERTRAILS)

```mermaid
flowchart TD
    MAIN["orchestrator/run_pipeline.py:main()"] --> ORCH["orchestrator/run_pipeline.py:run_pipeline()"]
    
    ORCH --> S01["stages/s01_ideation.py:run()<br/>(Cào từ khóa live Google Trends RSS)"]
    S01 --> S02["stages/s02_research.py:run()<br/>(Chốt từ khóa, Grounding Table, Factual Hook)"]
    S02 --> S03["stages/s03_script.py:run()<br/>(Kịch bản điều tra docudrama 5-Beat)"]
    S03 --> S04["stages/s04_critic_script.py:run()<br/>(Phản biện kịch bản Astra 6 + Opus 5.5)"]
    S04 --> HG1{{"HUMAN GATE 1: Chốt Kịch bản & Khóa Story"}}
    
    HG1 --> S09["stages/s09_voice_tts.py:run()<br/>(Sinh giọng đọc ElevenLabs & Faster-Whisper Word Timestamps)"]
    
    S09 --> S05["[FT-301] stages/s05_director_plan.py:run()<br/>app/services/papertrails_director.py:build_papertrails_timeline()<br/>(Ánh xạ kịch bản sang timeline.json: Biome, 3D Prop, Camera 3D, Torn Subtitles)"]
    
    S05 --> S08["[FT-302] stages/s08_video_gen.py:run()<br/>app/services/papertrails_vps_bridge.py:render_papertrails_on_vps()<br/>(Playwright WebGL2 Three.js Frame-by-Frame Renderer trên VPS Linux)"]
    
    S08 --> S10["[FT-303] stages/s10_render.py:run()<br/>(Đóng gói final.mp4 1080p @ 30fps kèm Tactile Paper Flip SFX)"]
    
    S10 --> S11["[FT-205] stages/s11_qc.py:run()<br/>(Đồng bộ YouTube Chapters từ timeline.json & nghiệm thu 0ms drift)"]
```
