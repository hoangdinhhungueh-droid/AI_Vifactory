# 🧪 [TEST_HARNESS_PLAN] INFRA_V7_AUTONOMOUS_FEEDBACK_LOOP

## 🎯 1. Chiến Lược Kiểm Thử (Test Strategy)
- **Phạm vi bao phủ**:
  1. Kiểm thử Unit thuật toán tính toán mốc Benchmark V7 (`avg_ctr`, `avg_avd`).
  2. Kiểm thử Bộ lọc Sạch 3 Lớp (Khử nhiễu views < 10, Lọc kép vượt benchmark, Lọc ngách ngữ nghĩa chống video rác/nhạc/game).
  3. Kiểm thử Khế ước lưu trữ, cập nhật và deduplication của `data/v7_winning_pool.json`.
  4. Kiểm thử Chuyển trạng thái `PENDING` ➔ `CONSUMED` khi B1.0 cam kết sản xuất đề tài.
  5. Kiểm thử Invariant Rule 118 Zero-Mock: Kênh mới hoặc pool trống phải trả về rỗng và tự động fallback về Google Trends RSS 100%.
  6. Kiểm thử ISO Neighbor-Testing [Block 1.0, Block 1.5] đảm bảo không gây hồi quy (regressions).
  7. Kiểm thử 4-Layer Ghost Code Hunter (Rule 125).

---

## 📊 2. Ma Trận Test Cases

| ID | Hạng Mục Kiểm Thử | Lệnh Thực Thi (Command) | Kết Quả Kỳ Vọng | Ngưỡng Timeout |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Benchmark Empty Edge Case | `pytest tests/test_v7_feedback_loop.py -k test_calculate_v7_benchmarks_empty` | avg_ctr=0.0, avg_avd=0.0, Exit 0 | 10s |
| **TC-02** | Benchmark Sample Calculation | `pytest tests/test_v7_feedback_loop.py -k test_calculate_v7_benchmarks_sample` | avg_ctr=6.0, avg_avd=7.29, Exit 0 | 10s |
| **TC-03** | 3-Layer Clean Learning Filter | `pytest tests/test_v7_feedback_loop.py -k test_v7_harvesting_three_layer_filter` | Chỉ video đạt chuẩn và đúng ngách mới PASS, Exit 0 | 15s |
| **TC-04** | Pool Persistence & Deduplication | `pytest tests/test_v7_feedback_loop.py -k test_v7_pool_save_load_update` | Deduplication 100%, Exit 0 | 15s |
| **TC-05** | B1 State Transition (Consumed) | `pytest tests/test_v7_feedback_loop.py -k test_v7_b1_candidate_consumption` | PENDING ➔ CONSUMED, Exit 0 | 15s |
| **TC-06** | Zero-Mock Fallback (Rule 118) | `pytest tests/test_v7_feedback_loop.py -k test_v7_zero_mock_empty_fallback` | Trả về `[]` sạch sẽ, Exit 0 | 10s |
| **TC-07** | ISO Neighbor-Testing Block 1.0/1.5 | `python tests/ci_neighbor_tester.py --block 1.0` | ALL PASSED, Exit 0 | 60s |
| **TC-08** | Ghost Code & Invariant Parity | `python scripts/orchestrator/ghost_code_detector.py` | ZERO GHOSTS, Exit 0 | 30s |
| **TC-09** | Live Runtime Execution Gate | `python -c "from scripts.b11_channel_analytics import calculate_v7_benchmarks; print('OK')"` | Exit 0 (Rule 127) | 10s |
