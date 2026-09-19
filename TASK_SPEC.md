# 📐 [TASK_SPEC] INFRA_V7_AUTONOMOUS_FEEDBACK_LOOP — Closed-Loop Algorithmic Discovery Engine

## 📌 1. Bối Cảnh & Ranh Giới (Context & Boundaries)
- **Feature Title**: V7 Autonomous Closed-Loop Feedback Engine (An Ong YouTube Studio Suggested Videos Formula)
- **Primary Block Impacted**: `B11.0` (Analytics Feedback), `B1.0` (Trend Engine), `B1.5` (Competitor Recon)
- **In-Scope**:
  - `scripts/b11_channel_analytics.py`: Thêm `calculate_v7_benchmarks()` và `harvest_v7_suggested_candidates()`.
  - `scripts/b11_antigravity_engine.py`: Thêm `load_v7_pool()`, `save_v7_pool()`, `update_v7_pool()` và kết nối gặt tự động vào B11 loop.
  - `app/services/trend_engine_b1.py`: Thêm `fetch_pending_v7_candidates()`, nạp vào Competitive Scoring, truyền `anchor_video_id` sang B1.5, và `mark_v7_candidate_consumed()`.
  - `app/services/competitor_recon_b15.py`: Bổ sung `anchor_video_id` vào `run_b15()`.
  - `PIPELINE_CONTRACTS.md`: Cập nhật khế ước lưu trữ và chuyển trạng thái `data/v7_winning_pool.json`.
  - `tests/test_v7_feedback_loop.py`: 6 unit/integration test cases.
- **Non-Goals**:
  - Không sửa đổi cấu trúc kịch bản B2 (giữ nguyên 5 Beat Docudrama).
  - Không thay đổi logic render Remotion B6–B8.
  - Không tạo mock views/CTR hay giả lập video ảo khi chưa có data thật (Rule 118).

---

## 🎯 2. Yêu Cầu Kỹ Thuật (Requirements R1 - R5)
- **R1 (Closed-Loop Autonomous Engine)**: B11 định kỳ trích xuất video đề xuất đạt chuẩn thắng cuộc ➔ lưu trữ tại `data/v7_winning_pool.json` ➔ B1.0 tự động đọc và đưa vào vòng tuyển chọn đề tài.
- **R2 (3-Layer Clean Learning Gate)**:
  - Lớp 1: Lọc nhiễu thống kê (`views >= min_views`).
  - Lớp 2: Tiêu chuẩn kép V7 (`ctr_percent > benchmark_avg_ctr` VÀ `avd_seconds > benchmark_avg_avd`).
  - Lớp 3: Lọc ngách ngữ nghĩa (khớp Canonical Pillars, chặn `OFF_NICHE_KEYWORDS` regex).
- **R3 (Competitive Scoring Gate B1.0)**: Ứng viên V7 và ứng viên Google Trends RSS cạnh tranh công bằng qua `assess_keyword_video_viability()`; chỉ đề tài đạt điểm >= 8.0 mới được chọn.
- **R4 (B1.5 Targeted Recon)**: Khi đề tài V7 thắng, truyền `referring_video_id` làm `anchor_video_id` cho `run_b15()` để mổ xẻ trực tiếp video gốc và tìm Fatal Explanatory Vacuum.
- **R5 (Zero-Mock Fallback)**: Nếu pool rỗng hoặc chưa có số liệu thực tế, pipeline tự động fallback 100% về Google Trends RSS live mà không làm gián đoạn hệ thống.

---

## 🔒 3. Khế Ước Dữ Liệu (Interface Contracts)
- **Pool File**: `data/v7_winning_pool.json`
- **Candidate Schema**:
  - `candidate_id`: `V7_<MARKET>_<HEX>`
  - `referring_video_id`: YouTube Video ID của đối thủ đề xuất
  - `referring_title`: Tiêu đề video đối thủ
  - `ctr_percent`: Tỷ lệ chuyển đổi / CTR
  - `avd_seconds`: Thời lượng xem trung bình (Average View Duration)
  - `views_from_source`: Lượt xem từ nguồn đề xuất
  - `status`: `PENDING` ➔ `CONSUMED`
  - `consumed_by_episode`: Mã tập sản xuất (e.g. `<MARKET>_EP<XXXX>`)
  - `created_at` / `consumed_at`: Mốc thời gian chuẩn ISO-8601 UTC.
