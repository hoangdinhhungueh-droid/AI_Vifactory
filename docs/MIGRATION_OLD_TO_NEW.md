# 🔄 BẢNG ĐỐI CHIẾU DI TRÚ TÊN CŨ ➔ TÊN CHUẨN (MIGRATION MAP)

> **Mục tiêu**: Hướng dẫn chuyển đổi toàn bộ từ vựng và script cũ sang chuẩn kiến trúc mới `AVF-STAB-001`.

---

## 📌 I. BẢNG TỪ VỰNG DỮ LIỆU (DATA VOCABULARY)

| Khái Niệm | Tên Cũ Rải Rác (DEPRECATED) | Tên Chuẩn Duy Nhất (CANONICAL) | Phạm Vi Áp Dụng |
| :--- | :--- | :--- | :--- |
| **Phân cảnh câu chuyện** | `beat`, `segment`, `story_scene`, `shotlist_item` | **`Scene`** | Toàn bộ kịch bản và phân cảnh đạo diễn |
| **Đoạn video tạo hình** | `clip`, `video_slice`, `i2v_unit` | **`Shot`** | Đơn vị sinh clip trên Google Flow |
| **Nội dung đọc thuyết minh**| `sentence`, `voice_text`, `spoken_script` | **`narration`** | Lời đọc kịch bản và Edge-TTS |
| **Tiêu đề phân cảnh** | `bilingual_headline`, `editorial_title`, `title_overlay` | **`headline`** | Tiêu đề chữ 1-4 từ phong cách Vox |
| **Prompt sinh video I2V** | `i2v_prompt`, `video_prompt`, `prompt` | **`visual_prompt`** | Universal Video Prompt cho Google Flow |
| **Ảnh tĩnh hạt giống** | `images`, `flat_seeds`, `composite_image` | **`composite_seeds`** | Thư mục và file ảnh tĩnh đưa vào I2V |
| **Video clip thô** | `vids`, `videos`, `clips` | **`video_clips`** | File clip MP4 tải về từ Google Flow |

---

## 🗂️ II. BẢNG ĐỐI CHIẾU MODULE & SCRIPTS

| Module / Script Cũ | Trạng Thái Mới | Giải Pháp / File Thay Thế Chuẩn |
| :--- | :---: | :--- |
| `scripts/run_vox_media_pipeline.py` | **Nâng cấp** | Tích hợp làm Engine nền tảng cho `orchestrator/run_pipeline.py`. |
| `scripts/forge_vox_director_plan.py` | **Quarantine** | Di chuyển vào `legacy/` (Do hardcode KR_EP0007). Thay bằng `stages/s05_director_plan.py`. |
| `app/services/director_planner_b3.py`| **Quarantine** | Di chuyển vào `legacy/` (Do dùng phong cách cũ Chroma Key #FF00FF). |
| `scripts/produce_episode_hg1.py` | **Quarantine** | Di chuyển vào `legacy/`. Luồng mới chạy qua Orchestrator chuẩn. |
| `app/services/vox_critic_council.py` | **Kế thừa** | Đóng gói thành `stages/s04_critic_script.py` và `stages/s06_critic_visual.py`. |
| `scripts/flow_video_dispatcher.py` | **Gia cố** | Nâng cấp filelock đa tiến trình và cơ chế Circuit Breaker 7 tài khoản. |
