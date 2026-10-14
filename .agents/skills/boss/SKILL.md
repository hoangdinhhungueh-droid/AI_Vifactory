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
> **KỶ LUẬT BẮT BUỘC (MANDATORY)**: Worker Gemini CẤM TUYỆT ĐỐI tự ý báo cáo hoàn thành cho Người Dùng khi Boss Claude Opus 5.5 chưa thẩm định và phê duyệt. Ngay khi hoàn tất code và test kỹ thuật, Worker BẮT BUỘC PHẢI TỰ ĐỘNG GỬI payload bằng chứng pháp y sang Boss Claude Opus 5.5 qua HHTech API mà không cần đợi User nhắc nhở.

1. **Lệnh Thẩm Định Tự Động**:
   ```bash
   python scripts/orchestrator/boss_orchestrator.py --phase audit --commit-range <BASE_COMMIT>..HEAD --task-id <TASK_ID>
   ```
2. **Tiêu Chuẩn Đánh Giá Khắt Khe (Zero-Compromise Quality Standard)**:
   - Mục tiêu: **10/10 điểm hoàn hảo** (hoặc đạt chuẩn tối đa không tì vết, tối thiểu $\ge 9.0/10.0$).
   - 0 lỗi Critical, 0 lỗi High, 0 tàn dư Ghost Code.
   - Bắt buộc đính kèm đầy đủ bằng chứng pháp y: GitHub Actions CI Run URL (`conclusion: success`), log pytest exit 0, Run Manifest live execution, SHA256 parity.
3. **Vòng Lặp Tự Sửa Lỗi Tự Động (Automated Self-Healing Loop - Tối đa 2 Vòng)**:
   - **Vòng 1**: Nếu Boss trả về `VERDICT: REVISE_REQUIRED`, Worker tự động bóc tách danh sách `revisions_needed`, lập tức sửa đổi code/hợp đồng/bằng chứng tương ứng và tự động nộp lại cho Boss thẩm định lần 2.
   - **Vòng 2**: Nếu Boss vẫn yêu cầu chỉnh sửa, Worker thực hiện lượt sửa cuối cùng và nộp thẩm định chốt chặn.
   - **Chốt chặn an toàn**: Nếu sau 2 vòng tự sửa Boss vẫn chưa ký duyệt `APPROVED`, Worker mới được dừng lại, xuất trình toàn bộ biên bản đối kháng của Boss kèm các phương án kỹ thuật để User ra quyết định tối cao.

### Bước 5: Báo Cáo Nghiệm Thu Duy Nhất Khi Có Dấu "APPROVED" (Single Truth Acceptance)
Chỉ khi Boss Claude Opus 5.5 chính thức ký **`VERDICT: APPROVED`**:
- Worker mới xuất bản Báo cáo nghiệm thu hoàn thiện gửi Người Dùng.
- Báo cáo phải trích dẫn rõ: Chữ ký thẩm định của Boss, điểm số, log HTTP 200 từ HHTech API, URL GitHub CI success, và hướng dẫn vận hành chuẩn.

