# 📋 BẢNG THEO DÕI & ĐIỀU PHỐI LỖI HỢP NHẤT (REPORTS/ISSUES.MD)

> **Mục tiêu**: Single Source of Truth theo dõi mọi issue từ F1 đến F8, gắn mã định danh, mức độ nghiêm trọng, Phase xử lý và bằng chứng giải quyết (Resolution Evidence).
> **Trạng thái**: TẤT CẢ 45/45 ISSUES ĐÃ ĐƯỢC GIẢI QUYẾT TRIỆT ĐỂ (100% CLOSED).

| Mã Issue | Lớp Bệnh | Mức Độ | File Liên Quan | Mô Tả Tóm Tắt | Phase Khắc Phục | Trạng Thái | Bằng Chứng Giải Quyết |
| :---: | :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| **D-001** | F1 (Contract Drift) | **S1 (Blocker)** | `app/services/story_engine_b2.py` | LỆCH TỪ VỰNG: story_beats/narration vs scenes/sentence | Phase 1 & 2 | `CLOSED` | Chuẩn hóa `Scene` $\supset$ `Shot` trong `core/contracts/stages.py`, S03 xuất chuẩn schema 1.0.0 |
| **D-002** | F1 (Contract Drift) | **S1 (Blocker)** | `app/services/director_planner_b3.py` | XUNG ĐỘT PHONG CÁCH: Chroma Key tách lớp cũ vs Composite Seed | Phase 1 & 2 | `CLOSED` | Cách ly Chroma Key cũ vào `legacy/`, thay thế bằng Composite Seed `stages/s05_director_plan.py` |
| **D-003** | F1 (Contract Drift) | **S1 (Blocker)** | `scripts/run_vox_media_pipeline.py` | ĐA DẠNG KEY: scene có cả i2v_prompt, video_prompt, prompt | Phase 1 & 2 | `CLOSED` | Hợp nhất duy nhất `universal_video_prompt` (Prompt 3 chuẩn) trong `Shot` model |
| **D-004** | F1 (Contract Drift) | **S1 (Blocker)** | `scripts/flow_video_dispatcher.py` | BẤT ĐỒNG NHẤT REMOTION PROPS: Props cũ đọc BG/FG png | Phase 1 & 2 | `CLOSED` | Tạo `core/contracts/render_props.py`, xuất `remotion/src/generated/render-props.schema.json` 0% drift |
| **D-005** | F1 (Contract Drift) | **S1 (Blocker)** | `app/services/vox_critic_council.py` | THIẾU VÒNG TỰ SỬA: Feedback trả về chỉ để hiển thị | Phase 1 & 2 | `CLOSED` | Implement `CouncilDecision` (`APPROVED` / `REJECTED`) & Retry-loop trong `stages/s04_critic_script.py` |
| **P-001** | F2 (Path Entropy) | **S2 (Major)** | `conftest.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Khởi tạo Single Path Authority `core/paths.py` (`RunPaths.from_env()`) tự động thích ứng |
| **P-002** | F2 (Path Entropy) | **S2 (Major)** | `login_acc07.bat` | Hardcode profile local Windows | Phase 1 | `CLOSED` | Đưa vào cấu hình động theo profile trong `config/profiles/*.yaml` |
| **P-003** | F2 (Path Entropy) | **S2 (Major)** | `mcp_server.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Chuyển sang đọc qua `RunPaths` dynamic resolution |
| **P-004** | F2 (Path Entropy) | **S2 (Major)** | `mcp_server.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Chuyển sang đọc qua `RunPaths` dynamic resolution |
| **P-005** | F2 (Path Entropy) | **S2 (Major)** | `.agents/teamwork/.../check_base_tsc.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Đường dẫn được dynamicize theo repo root chuẩn |
| **P-006** | F2 (Path Entropy) | **S2 (Major)** | `.agents/teamwork/.../check_res.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Đường dẫn được dynamicize theo repo root chuẩn |
| **P-007** | F2 (Path Entropy) | **S2 (Major)** | `.agents/teamwork/.../inspect_props.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Quarantined vào `legacy/` |
| **P-008** | F2 (Path Entropy) | **S2 (Major)** | `.agents/teamwork/.../test_patch_compile.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Quarantined vào `legacy/` |
| **P-009** | F2 (Path Entropy) | **S2 (Major)** | `.agents/teamwork/.../test_tsc.py` | Hardcode đường dẫn tuyệt đối VPS | Phase 1 | `CLOSED` | Quarantined vào `legacy/` |
| **P-010** | F2 (Path Entropy) | **S2 (Major)** | `app/pipeline/run_episode.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Thay thế bởi `orchestrator/run_pipeline.py` sử dụng `RunPaths` |
| **P-011** | F2 (Path Entropy) | **S2 (Major)** | `app/pipeline/run_episode.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Thay thế bởi `orchestrator/run_pipeline.py` sử dụng `RunPaths` |
| **P-012** | F2 (Path Entropy) | **S2 (Major)** | `app/pipeline/run_episode.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Thay thế bởi `orchestrator/run_pipeline.py` sử dụng `RunPaths` |
| **P-013** | F2 (Path Entropy) | **S2 (Major)** | `app/pipeline/run_episode.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Thay thế bởi `orchestrator/run_pipeline.py` sử dụng `RunPaths` |
| **P-014** | F2 (Path Entropy) | **S2 (Major)** | `app/pipeline/run_episode.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Thay thế bởi `orchestrator/run_pipeline.py` sử dụng `RunPaths` |
| **P-015** | F2 (Path Entropy) | **S2 (Major)** | `app/pipeline/run_episode.py` | Hardcode kho lưu trữ tập phim VPS | Phase 1 | `CLOSED` | Thay thế bởi `orchestrator/run_pipeline.py` sử dụng `RunPaths` |
| **G-001** | F3 (Ghost Code) | **S2 (Major)** | `.agents/teamwork/.../inspect_props.py` | Tên file thử nghiệm cũ | Phase 4 | `CLOSED` | Di chuyển vào `legacy/`, inject `forbid_legacy()` |
| **G-002** | F3 (Ghost Code) | **S2 (Major)** | `.agents/teamwork/.../test_patch_compile.py` | Tên file thử nghiệm cũ | Phase 4 | `CLOSED` | Di chuyển vào `legacy/`, inject `forbid_legacy()` |
| **G-003** | F3 (Ghost Code) | **S2 (Major)** | `.agents/teamwork/.../test_resolve_src.py` | Tên file thử nghiệm cũ | Phase 4 | `CLOSED` | Di chuyển vào `legacy/`, inject `forbid_legacy()` |
| **G-004** | F3 (Ghost Code) | **S2 (Major)** | `.agents/teamwork/.../test_tsc.py` | Tên file thử nghiệm cũ | Phase 4 | `CLOSED` | Di chuyển vào `legacy/`, inject `forbid_legacy()` |
| **G-005** | F3 (Ghost Code) | **S2 (Major)** | `app/config.py` | In-degree = 0 | Phase 4 | `CLOSED` | Thay bằng `core/config.py` có profile-driven typing |
| **G-006** | F3 (Ghost Code) | **S2 (Major)** | `app/log_redact.py` | In-degree = 0 | Phase 4 | `CLOSED` | Thay bằng logging handler của `core/run_manifest.py` |
| **G-007** | F3 (Ghost Code) | **S2 (Major)** | `app/main.py` | In-degree = 0 | Phase 4 | `CLOSED` | Thay bằng `orchestrator/run_pipeline.py` single CLI authority |
| **G-008** | F3 (Ghost Code) | **S2 (Major)** | `app/tasks.py` | In-degree = 0 | Phase 4 | `CLOSED` | Celery dispatch được gói gọn theo Stage Shape `stages/` |
| **G-009** | F3 (Ghost Code) | **S2 (Major)** | `app/audit/deepseek_reasoner.py` | In-degree = 0 | Phase 4 | `CLOSED` | Tích hợp vào Boss 3-Tier Multi-Agent Harness (`boss_orchestrator.py`) |
| **G-010** | F3 (Ghost Code) | **S2 (Major)** | `app/services/b5_validate_safe_zone.py` | In-degree = 0 | Phase 4 | `CLOSED` | Thay bằng Gate QA 4 trục trong `stages/s06_critic_visual.py` & S11 |
| **G-011** | F3 (Ghost Code) | **S2 (Major)** | `app/services/bd_serp_budget.py` | In-degree = 0 | Phase 4 | `CLOSED` | Thay bằng `stages/s02_research.py` live grounding recon |
| **G-012** | F3 (Ghost Code) | **S2 (Major)** | `app/services/chapter_split.py` | In-degree = 0 | Phase 4 | `CLOSED` | Tích hợp Remotion ground-truth chapter sync trong S10 |
| **G-013** | F3 (Ghost Code) | **S2 (Major)** | `app/services/character_refs.py` | In-degree = 0 | Phase 4 | `CLOSED` | Di chuyển vào `legacy/` |
| **G-014** | F3 (Ghost Code) | **S2 (Major)** | `app/services/composite_generator.py` | In-degree = 0 | Phase 4 | `CLOSED` | Tích hợp vào `stages/s07_image_gen.py` |
| **G-015** | F3 (Ghost Code) | **S2 (Major)** | `app/services/cost_ledger.py` | In-degree = 0 | Phase 4 | `CLOSED` | Thay bằng Cost Ledger tích hợp trong `run_manifest.json` |
| **M-001** | F7 (Mock Leak) | **S1 (Blocker)** | `AGENTS.md` | Biến giả lập | Phase 1 | `CLOSED` | Thiết lập `core/no_mock.py` chặn triệt để mock data |
| **M-002** | F7 (Mock Leak) | **S1 (Blocker)** | `AGENTS.md` | Biến giả lập | Phase 1 | `CLOSED` | Thiết lập `core/no_mock.py` chặn triệt để mock data |
| **M-003** | F7 (Mock Leak) | **S1 (Blocker)** | `PIPELINE_CONTRACTS.md` | Biến giả lập | Phase 1 | `CLOSED` | Thiết lập Generic Contract Pattern Rule 128 |
| **M-004** | F7 (Mock Leak) | **S1 (Blocker)** | `ROADMAP.md` | Biến giả lập | Phase 1 | `CLOSED` | Thiết lập Zero-Mock Policy |
| **M-005** | F7 (Mock Leak) | **S1 (Blocker)** | `ROADMAP.md` | Biến giả lập | Phase 1 | `CLOSED` | Thiết lập Zero-Mock Policy |
| **M-006** | F7 (Mock Leak) | **S1 (Blocker)** | `.opencodereview/rule.json` | Biến giả lập | Phase 1 | `CLOSED` | Đưa vào OCR Rule Gate kiểm toán 0-Mock |
| **M-007** | F7 (Mock Leak) | **S1 (Blocker)** | `active_candidate/brain_input.json` | Biến giả lập | Phase 1 | `CLOSED` | Pipeline đọc live inputs từ S01/S02 |
| **M-008** | F7 (Mock Leak) | **S1 (Blocker)** | `active_candidate/seo_package.json` | Biến giả lập | Phase 1 | `CLOSED` | Sinh từ real-time YouTube Recon |
| **M-009** | F7 (Mock Leak) | **S1 (Blocker)** | `app/services/agq_fleet_manager.py` | Giá trị số dư ví giả lập | Phase 1 | `CLOSED` | Bắt buộc đọc từ Signed API, cấm hardcode fallback |
| **M-010** | F7 (Mock Leak) | **S1 (Blocker)** | `app/services/agq_fleet_manager.py` | Giá trị số dư ví giả lập | Phase 1 | `CLOSED` | Bắt buộc đọc từ Signed API, cấm hardcode fallback |
