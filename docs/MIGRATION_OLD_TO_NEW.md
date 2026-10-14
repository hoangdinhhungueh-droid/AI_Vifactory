# 🔄 BẢNG ĐỐI CHIẾU DI TRÚ TÊN CŨ ➔ TÊN CHUẨN (MIGRATION MAP)

> **Mục tiêu**: Hướng dẫn chuyển đổi toàn bộ từ vựng, hợp đồng dữ liệu và các script cũ sang chuẩn kiến trúc mới `AVF-STAB-001`.
> **Tuân thủ**: Rule 125 (Single Pipeline Version & Zero-Ghost Remnant), Rule 128 (Anti-Semantic Bias), Rule 132 (Decoupled Engine).

---

## 📌 I. BẢNG TỪ VỰNG DỮ LIỆU (DATA VOCABULARY)

| Khái Niệm | Tên Cũ Rải Rác (DEPRECATED) | Tên Chuẩn Duy Nhất (CANONICAL) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- | :--- |
| **Phân cảnh câu chuyện** | `beat`, `segment`, `story_scene`, `shotlist_item` | **`Scene`** | Toàn bộ kịch bản và phân cảnh đạo diễn |
| **Đoạn video tạo hình** | `clip`, `video_slice`, `i2v_unit` | **`Shot`** | Đơn vị sinh clip trên Google Flow |
| **Nội dung đọc thuyết minh**| `sentence`, `voice_text`, `spoken_script` | **`narration`** | Lời đọc kịch bản và Edge-TTS |
| **Tiêu đề phân cảnh** | `bilingual_headline`, `editorial_title`, `title_overlay` | **`headline`** | Tiêu đề chữ 1-4 từ phong cách Vox |
| **Prompt sinh video I2V** | `i2v_prompt`, `video_prompt`, `prompt` | **`universal_video_prompt`** | Universal Video Prompt cho Google Flow |
| **Ảnh tĩnh hạt giống** | `images`, `flat_seeds`, `composite_image` | **`composite_seeds`** | Thư mục và file ảnh tĩnh đưa vào I2V |
| **Video clip thô** | `vids`, `videos`, `clips` | **`video_clips`** | File clip MP4 tải về từ Google Flow |

---

## 🗂️ II. BẢNG ĐỐI CHIẾU ĐIỀU PHỐI (FILE DISPOSITION TABLE)

| File / Module Cũ | Hành Động Xử Lý (Disposition) | File Đích / Luồng Chuẩn Thay Thế | Giải Trình Lý Do & Khế Ước |
| :--- | :---: | :--- | :--- |
| `scripts/produce_episode.py` | **QUARANTINED** | `orchestrator/run_pipeline.py` | Luồng cũ không có state machine và checkpoint SHA256; chuyển vào `legacy/` có guard `forbid_legacy()`. |
| `scripts/produce_episode_hg1.py` | **QUARANTINED** | `orchestrator/run_pipeline.py` | Entrypoint cũ bypass các cổng kiểm duyệt chất lượng; chuyển vào `legacy/`. |
| `scripts/forge_vox_director_plan.py` | **QUARANTINED** | `stages/s05_director_plan.py` | Chứa dữ liệu hardcode cụ thể (`KR_EP0007`) vi phạm Rule 128; chuyển vào `legacy/`. |
| `scripts/trigger_video_generation.py` | **QUARANTINED** | `stages/s08_video_gen.py` | Script rời rạc thiếu Circuit Breaker; chuyển vào `legacy/`. |
| `app/templates/hg2_telegram_format_v2.py`| **QUARANTINED** | `core/contracts/` & Telegram Gate | File phiên bản `_v2` vi phạm Rule 125 Single Truth; chuyển vào `legacy/`. |
| `scripts/audit_youtube_video_v2.py` | **QUARANTINED** | `stages/s11_qc.py` | Script phiên bản cũ; chuyển vào `legacy/`. |
| `scripts/audit_youtube_video_v3.py` | **QUARANTINED** | `stages/s11_qc.py` | Script phiên bản cũ; chuyển vào `legacy/`. |
| `scripts/orchestrator/dual_model_chunk_auditor_v2.py` | **QUARANTINED** | `stages/s04_critic_script.py` | Script phiên bản cũ; chuyển vào `legacy/`. |
| `app/services/director_planner_b3.py`| **SHIM / FACADE** | `stages/s05_director_plan.py` | Toàn bộ luồng sinh plan đạo diễn mới chuyển 100% sang `stages/s05_director_plan.py`. File này chỉ lưu giữ các hàm tiện ích (`detect_forensic_overlay`, `resolve_market_redacted_terms`) để bảo toàn tính tương thích ngược cho test runner. |
| `app/services/video_gen.py` | **ADAPTER** | `stages/s08_video_gen.py` | Đóng vai trò adapter tương thích ngược; luồng chính gọi `s08_video_gen.py`. |
| `remotion/src/index.tsx` | **SOT BRIDGE** | `core/contracts/render_props.py` | Đọc `render-props.schema.json` xuất trực tiếp từ Pydantic v2 contract; 0% schema drift. |
