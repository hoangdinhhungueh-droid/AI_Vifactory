# 🛠️ [CHANGE_MANIFEST] INFRA_V7_AUTONOMOUS_FEEDBACK_LOOP — Closed-Loop Algorithmic Discovery Engine

## 📌 1. Trạng Thái Thực Thi (Execution Metadata)
- **Builder Agent**: Antigravity Multi-Agent Harness (Builder Role)
- **Thời điểm hoàn tất**: 2026-09-19T14:28:00+07:00
- **AST Py-Compile**: `EXIT CODE 0` (Tất cả 4 module đều đạt)
- **Ghost Hunter Gate (Rule 125)**: `EXIT CODE 0` (100% clean, 0 defects)

---

## 📝 2. Chi Tiết File Sửa Đổi (Line-Level Changes)

### 1. `scripts/b11_channel_analytics.py`
- **Mục đích sửa**: Bổ sung hàm tính mốc Benchmark dòng Tổng (`calculate_v7_benchmarks`) và hàm trích xuất, sàng lọc 3 lớp video đề xuất (`harvest_v7_suggested_candidates`).
- **Nội dung bổ sung**:
  - `calculate_v7_benchmarks(rows)`: Tính `avg_ctr` và `avg_avd` làm thước đo chuẩn từ dữ liệu dòng Tổng.
  - `harvest_v7_suggested_candidates(access_token, winning_video_ids, market, min_views, days)`: Query `RELATED_VIDEO` từ YouTube Analytics API v2, áp dụng bộ lọc 3 lớp (Views >= 10, Kép V7 CTR/AVD > Average, Lọc ngách ngữ nghĩa + chặn `OFF_NICHE_KEYWORDS`).
  - Thêm `import re` ở đầu file.
- **AST Py-Compile**: `EXIT CODE 0`

### 2. `scripts/b11_antigravity_engine.py`
- **Mục đích sửa**: Tích hợp V7 Harvester vào vòng lặp phân tích định kỳ và quản lý state pool `data/v7_winning_pool.json`.
- **Nội dung bổ sung**:
  - Định nghĩa `V7_POOL_FILE = os.path.join(DATA_DIR, "v7_winning_pool.json")`.
  - Các hàm tiện ích: `load_v7_pool`, `save_v7_pool`, `update_v7_pool` (hỗ trợ deduplication chống lặp video đối thủ).
  - Tích hợp gọi `harvest_v7_suggested_candidates` và cập nhật pool trong market processing loop.
- **AST Py-Compile**: `EXIT CODE 0`

### 3. `app/services/trend_engine_b1.py`
- **Mục đích sửa**: Tích hợp ứng viên từ V7 Pool vào vòng tuyển chọn đề tài chính với cơ chế Đấu thầu Điểm Khả Thi (Competitive Scoring).
- **Nội dung bổ sung**:
  - Hàm `fetch_pending_v7_candidates(market)` và `mark_v7_candidate_consumed(candidate_id, episode_id)`.
  - Nạp V7 candidates vào `fetch_live_trending_terms()` và ưu tiên đưa vào vòng thẩm định viability qua `assess_keyword_video_viability()`.
  - Truyền `anchor_video_id` sang B1.5 (`run_b15`) khi đề tài có nguồn gốc từ V7.
  - Đánh dấu `status: "CONSUMED"` trong `commit_trend_task()`.
- **AST Py-Compile**: `EXIT CODE 0`

### 4. `app/services/competitor_recon_b15.py`
- **Mục đích sửa**: Hỗ trợ tham số `anchor_video_id` trong hàm `run_b15()`.
- **Nội dung bổ sung & hiệu chỉnh**:
  - Bổ sung `anchor_video_id: Optional[str] = None` vào `run_b15`.
  - Tự động chèn video đối thủ V7 làm ứng viên hàng đầu trong danh sách phân tích của B1.5 ngay trước `select_competitors()`.
  - **Forensic Fix**: Tách khối `if anchor_video_id:` độc lập sau khối search/cache, khắc phục triệt để lỗi thụt lề tiềm ẩn vốn có thể gây bỏ qua logic trích xuất chi tiết video khi `anchor_video_id` là `None`.
- **AST Py-Compile**: `EXIT CODE 0`

### 5. `PIPELINE_CONTRACTS.md`
- **Mục đích sửa**: Cập nhật hợp đồng giao diện Mục 7 (`Khối B11 ➔ Khối B1.0/B1.5: V7 Autonomous Closed-Loop Feedback Engine`).
- **Nội dung bổ sung**: Generic JSON Schema cho `data/v7_winning_pool.json` và quy chuẩn chuyển trạng thái `PENDING` ➔ `CONSUMED`.

### 6. `tests/test_v7_feedback_loop.py` [NEW]
- **Mục đích**: Bộ unit & integration test toàn diện 6 test cases kiểm thử trọn vẹn logic tính benchmark, lọc 3 lớp, chống data poisoning, quản lý state pool, và fallback zero-mock.

---

## 🧹 3. Cam Kết Dọn Rác & Zero-Ghost (Rule 119 & 125)
- [x] Không để lại file tạm rác trong `/tmp/`.
- [x] Không tạo file `.bak*`, `.backup*`, file shadow code.
- [x] Đã đồng bộ comment/docstring nội hàm (Rule 125 Single Truth).
- [x] Đã vượt qua cổng kiểm toán vật lý `ghost_code_detector.py` với 0 defects.
