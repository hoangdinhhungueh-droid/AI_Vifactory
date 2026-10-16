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
> 2. **Worker**: Gemini 3.8 Flash High (Phiên làm việc Antigravity hiện tại) — Đội thợ cày: Tốc độ cao, Context 1M+, Code nặng, Live Programmatic Test (Rule 127).
> 3. **24/7 VPS Drones**: Low-cost LLMs (`claude-v4.1-flash`, fallback `claude-6-luna`) qua HHTech API — Chạy ngầm 24/7 trên VPS (Celery, Cron, Telegram Bots) với chi phí gần bằng 0.

---

## ⚡ QUY TRÌNH THỰC THI BẮT BUỘC KHI GỌI LỆNH `/boss <YÊU CẦU>`

### Bước 1: Boss Opus 5.5 Lập Kế Hoạch (Phase 1: Planning)
> ⚠️ **KỶ LUẬT THÉP BẢO CHỨNG GỌI OPUS 5.5 (ZERO-MOCK MANDATE - Rule 118)**:
> Agent CẤM TUYỆT ĐỐI tự biên tự diễn kế hoạch trong cửa sổ chat.
> Agent BẮT BUỘC phải dùng công cụ `run_command` chạy CLI Engine gọi trực tiếp Opus 5.5 qua HHTech API:

```bash
python scripts/orchestrator/boss_orchestrator.py --phase plan --task "<Yêu cầu người dùng>"
```
- Phản hồi đầu tiên của Agent BẮT BUỘC phải trích dẫn:
  1. Live log HTTP 200 từ HHTech API, Model `claude-opus-5-5`, Latency, và Tokens.
  2. Đường dẫn file kế hoạch vật lý: `specs/boss_plans/TASK_<ID>_plan.md`.
  3. Tóm tắt định tuyến: `OFFLINE_LOCAL` (Antigravity build) hay `VPS_247` (chạy ngầm liên tục).

### Bước 2: Cổng Xác Nhận 1 Chạm (Interactive Venue Confirmation)
Agent hiển thị câu hỏi xác nhận qua công cụ `ask_question`:
- Trình bày tóm tắt nhận định của Boss và đề xuất (Offline Build vs 24/7 VPS).
- Người dùng bấm chọn 1 chạm để xác nhận hướng đi.

### Bước 3: Worker Gemini 3.8 Flash High Thực Thi (Phase 2: Execution)
- **Ai là Worker?** Chính là phiên làm việc Antigravity hiện tại (Gemini 3.8 Flash High).
- **Trách nhiệm của Worker**: Bám sát 100% từng bước DAG trong file `specs/boss_plans/TASK_<ID>_plan.md`:
  - **Nếu là OFFLINE_LOCAL**:
    1. Worker đọc các file liên quan, kiểm tra Blast Radius (Rule 138).
    2. Viết/sửa code nguyên tử (`replace_file_content` / `write_to_file`).
    3. Chạy kiểm thử sống: `python -m py_compile ...` và chạy trực tiếp hàm/test sống (Rule 127).
  - **Nếu là VPS_247**:
    1. Worker lấy boilerplate client chuẩn: `python scripts/orchestrator/boss_orchestrator.py --phase template_247`.
    2. Viết service script gọi `claude-v4.1-flash` (fallback `claude-6-luna`) qua HHTech API.
    3. Viết cấu hình Systemd / Celery Beat / Cron job.
    4. Kiểm thử cú pháp và runtime trước khi đồng bộ VPS (Rule 126).

---

### Bước 4: Tự Động Kích Hoạt Loop Thẩm Định Boss Opus 5.5 (Phase 3: Self-Healing Loop)
> ⚠️ **KỶ LUẬT THÉP BẮT BUỘC (ANTI-FAKE REPORTING & STATE MACHINE)**:
> 1. Worker CẤM TUYỆT ĐỐI tự phong cho mình điểm 10/10 hay tự ý báo cáo hoàn thành khi Boss Opus 5.5 chưa thẩm định.
> 2. Mọi kết quả thẩm định BẮT BUỘC lưu thành file vật lý: `specs/boss_audits/TASK_<ID>_audit_round_<N>.json`.
> 3. Agent BẮT BUỘC chạy lệnh điều phối vòng lặp:

```bash
python scripts/orchestrator/boss_orchestrator.py --phase loop-step --task-id <TASK_ID>
```

#### 🔄 Cơ Chế Xử Lý Theo Mã Exit Code Của Loop-Step:
- **Nếu Exit Code = 2 (`REVISE_REQUIRED`, Score < 10.0)**:
  - Script tự động tăng số vòng (`Round 1 -> Round 2`) và xuất ra danh sách checklist `revisions_needed`.
  - **Hành động bắt buộc của Worker**:
    1. Đọc danh sách checklist lỗi do Boss yêu cầu sửa.
    2. Sửa trực tiếp code vào đĩa cứng.
    3. Chạy lại kiểm thử `py_compile` và `pytest`.
    4. Chạy lại lệnh `python scripts/orchestrator/boss_orchestrator.py --phase loop-step --task-id <TASK_ID>` (Vòng 2).
- **Nếu Exit Code = 0 (`APPROVED`, Score 10.0/10.0)**:
  - Boss chính thức ký duyệt. Chuyển sang Bước 5 xuất bản nghiệm thu.
- **Nếu Exit Code = 1 (`FAILED_MAX_ROUNDS`)**:
  - Đã hết tối đa 2 vòng tự sửa mà Boss vẫn chưa duyệt 10/10.
  - Worker dừng lại, mở file `specs/boss_audits/TASK_<ID>_audit_round_2.json` và xuất trình toàn văn điểm bất đồng cho User quyết định.
  - *Ngoại lệ ủy quyền (Cap Extension Protocol - Boss Round 12 Item 8 & 12)*: Khi User cấp ủy quyền tiếp tục liên tục (ví dụ: `"Tiếp tục"`, `"tiếp tục"`, hoặc `"/boss đồng ý thực thi..."` như đã ghi nhận trong `BUNDLED_SCOPE_USER_APPROVAL.md`), cờ `--max-rounds` được mở rộng linh hoạt (`--max-rounds N` hoặc tiếp tục loop theo từng round đơn lẻ) để Agent và Boss tự sửa lặp lại cho tới khi đạt điểm tuyệt đối **`10.0 / 10.0 VERDICT: APPROVED`**, không thỏa hiệp chất lượng.

---

### Bước 5: Báo Cáo Nghiệm Thu Duy Nhất Khi Có Dấu "APPROVED" 10/10
Chỉ khi lệnh `loop-step` trả về Exit Code `0`:
1. Worker dùng `view_file` đọc trực tiếp file: `specs/boss_audits/TASK_<ID>_audit_round_<N>.json`.
2. Trích dẫn trong tin nhắn gửi Người Dùng:
   - File Audit Artifact: `specs/boss_audits/TASK_<ID>_audit_round_<N>.json`
   - Điểm số: Đúng `10.0 / 10.0`
   - Chữ ký thẩm định của Boss Opus 5.5
   - Tóm tắt các component đã audit và số vòng tự sửa đã vượt qua.
