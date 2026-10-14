---
name: boss
description: >-
  Three-tier Multi-Agent Harness uniting Boss Claude Opus 5.5 via HHTech API,
  Worker Gemini 3.8 Flash High in Antigravity, and 24/7 VPS Drones with ultra-low-cost
  LLMs (claude-v4.1-flash & claude-6-luna). Triggers: "/boss", "boss plan", "gọi boss",
  "boss giao việc", "3-tier harness".
---

# 👔 BOSS ORCHESTRATOR SKILL (`/boss`)

> **Hệ thống Điều phối 3 Tầng Tối Ưu Quota & Chi Phí (Three-Tier Trust & Efficiency Harness):**
> 1. **Boss**: Claude Opus 5.5 gọi live qua HHTech API (`https://hhtechapi.com/v1`) — Não to: Brainstorm, Spec, Task DAG, Supervisory Audit.
> 2. **Worker**: Gemini 3.8 Flash High (Model mặc định Antigravity) — Đội thợ cày: Tốc độ cao, Context 1M+, Code nặng, Live Programmatic Test (Rule 127).
> 3. **24/7 VPS Drones**: Low-cost LLMs (`claude-v4.1-flash`, fallback `claude-6-luna`) qua HHTech API — Chạy ngầm 24/7 trên VPS (Celery, Cron, Telegram Bots) với chi phí gần bằng 0.

---

## ⚡ QUY TRÌNH THỰC THI KHI GỌI LỆNH `/boss <YÊU CẦU>`

### Bước 1: Boss Opus 5.5 Lập Kế Hoạch (Phase 1: Planning)
Agent chạy CLI Engine gọi trực tiếp Opus 5.5 qua HHTech API:
```bash
python scripts/orchestrator/boss_orchestrator.py --phase plan --task "<Yêu cầu người dùng>"
```
- In rõ live log HTTP 200 từ HHTech API.
- Tự động nhận diện tín hiệu tác vụ:
  - Nếu có tín hiệu chạy ngầm (`cron`, `daemon`, `bot telegram`, `cào dữ liệu`, `realtime`, `khi tắt máy`): Đề xuất `VPS_247`.
  - Nếu là code, refactor, bug, tối ưu, test trong IDE: Đề xuất `OFFLINE_LOCAL`.
- Xuất bản kế hoạch chi tiết xuống `specs/boss_plans/TASK_<ID>_plan.md`.

### Bước 2: Cổng Xác Nhận 1 Chạm (Interactive Venue Confirmation)
Agent hiển thị câu hỏi xác nhận qua công cụ `ask_question`:
- Trình bày tóm tắt nhận định của Boss và đề xuất (Offline Build vs 24/7 VPS).
- Người dùng bấm chọn 1 chạm để xác nhận hướng đi.

### Bước 3: Worker Gemini 3.8 Flash High Thực Thi (Phase 2: Execution)
- **Nếu là OFFLINE_LOCAL**:
  1. Worker đọc các file liên quan, kiểm tra Blast Radius (Rule 138).
  2. Viết/sửa code nguyên tử (`replace_file_content` / `write_to_file`).
  3. Chạy kiểm thử sống: `python3 -m py_compile ...` và chạy trực tiếp hàm sống (Rule 127).
- **Nếu là VPS_247**:
  1. Worker lấy boilerplate client chuẩn: `python scripts/orchestrator/boss_orchestrator.py --phase template_247`.
  2. Viết service script cấu hình gọi `claude-v4.1-flash` (fallback `claude-6-luna`) qua HHTech API.
  3. Viết cấu hình Systemd / Celery Beat / Cron job.
  4. Kiểm thử cú pháp và runtime trước khi đồng bộ VPS (Rule 126).

### Bước 4: Tự Động Kích Hoạt Boss Opus 5.5 Thẩm Định & Vòng Lặp Tự Sửa Lỗi (Phase 3: Mandatory Auto-Audit & Self-Healing Loop)
> **KỶ LUẬT THÉP BẮT BUỘC (ZERO-NARRATIVE & RAW EVIDENCE INJECTION)**:
> 1. Worker Gemini CẤM TUYỆT ĐỐI tự ý báo cáo hoa mỹ cho Người Dùng khi Boss Claude Opus 5.5 chưa thẩm định và phê duyệt.
> 2. CẤM TUYỆT ĐỐI Worker tự bịa lời văn tóm tắt ("nói đỡ") trong digest gửi cho Boss. Boss Claude Opus 5.5 BẮT BUỘC phải soi thẳng vào **DỮ LIỆU THÔ VẬT LÝ TRỰC TIẾP TỪ GIT VÀ VPS**:
>    - Raw `git diff --stat <BASE>..HEAD` (toàn văn không cắt xén).
>    - Raw Tree Byte Parity: `git ls-files -z | sha256sum`.
>    - Raw stdout & exit code thực tế của `pytest`, `e2e_pipeline_smoketest.py`, `ghost_scan.py` trên VPS.
>    - Raw `ffprobe` JSON stream/format của file video thực tế trên VPS.
>    - Raw GitHub Actions API JSON (`status`, `conclusion`, `html_url`).
> 3. Worker tự động gửi toàn bộ bằng chứng thô này thẳng sang Boss Opus 5.5 qua HHTech API ngay khi hoàn thành code, hoàn toàn tự động không cần User yêu cầu.

1. **Lệnh Thẩm Định Tự Động**:
   ```bash
   python scripts/orchestrator/boss_orchestrator.py --phase audit --commit-range <BASE_COMMIT>..HEAD --task-id <TASK_ID>
   ```
2. **Tiêu Chuẩn Đánh Giá Khắt Khe (Zero-Compromise 10/10 Quality Mandate)**:
   - **Mục tiêu bất di bất dịch: Đúng 10/10 điểm hoàn hảo (`score == 10.0` & `VERDICT: APPROVED`)**. Tuyệt đối không thỏa hiệp với điểm 8.x hay 9.x.
   - 0 lỗi Critical, 0 lỗi High, 0 warning không rõ nguồn gốc, 0 tàn dư Ghost Code.
   - Bắt buộc đính kèm đầy đủ bằng chứng pháp y: GitHub Actions CI Run URL (`conclusion: success`), log pytest exit 0, Run Manifest live execution, SHA256 parity, ffprobe telemetry.
3. **Vòng Lặp Tự Sửa Lỗi Tự Động (Automated Self-Healing Loop - Tối đa 2 Vòng)**:
   - **Vòng 1**: Nếu Boss trả về `VERDICT: REVISE_REQUIRED` hoặc `score < 10.0`, Worker tự động bóc tách danh sách `revisions_needed`, lập tức sửa đổi code/hợp đồng/bằng chứng tương ứng trên đĩa, chạy kiểm thử sống, đồng bộ và tự động nộp lại cho Boss thẩm định lần 2.
   - **Vòng 2**: Nếu Boss vẫn chưa chấm 10/10, Worker thực hiện lượt hoàn thiện triệt để cuối cùng và nộp thẩm định chốt chặn.
   - **Chốt chặn an toàn**: Nếu sau 2 vòng tự sửa Boss vẫn chưa ký duyệt 10/10 `APPROVED`, Worker mới được dừng lại, xuất trình toàn văn biên bản đối kháng của Boss kèm các phương án kỹ thuật để User ra quyết định tối cao.

### Bước 5: Báo Cáo Nghiệm Thu Duy Nhất Khi Có Dấu "APPROVED" 10/10 (Single Truth Acceptance)
Chỉ khi Boss Claude Opus 5.5 chính thức ký **`VERDICT: APPROVED` (Điểm 10/10)**:
- Worker mới xuất bản Báo cáo nghiệm thu hoàn thiện gửi Người Dùng.
- Báo cáo phải trích dẫn rõ: Chữ ký thẩm định của Boss, điểm số 10/10, log HTTP 200 từ HHTech API, URL GitHub CI success, và hướng dẫn vận hành chuẩn.


