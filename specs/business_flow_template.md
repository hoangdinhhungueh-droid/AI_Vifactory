# 📐 BUSINESS FLOW SPECIFICATION TEMPLATE (STEP 1: PLAN)

> **Mục đích**: Bản đồ nghiệp vụ chuẩn xác trước khi viết bất kỳ dòng mã nguồn nào.  
> *Áp dụng theo Bước 1 của quy chuẩn Vibe Coding chuẩn (chống để AI đoán mò).*

---

## 1. TỔNG QUAN NGHIỆP VỤ (BUSINESS OBJECTIVE)
- **Tên tính năng / Module**: `<Tên module / feature>`
- **Mục tiêu cốt lõi**: `<Giải quyết vấn đề gì, mang lại giá trị gì>`
- **Người dùng / Tác nhân (Actors)**: `<User / Admin / Celery Worker / YouTube Bot / Webhook>`

---

## 2. LUỒNG DỮ LIỆU & HÀNH VI (END-TO-END FLOW)
1. **Trigger / Khởi phát**: `<Sự kiện gì kích hoạt luồng: CLI command, API request, Cron job, Queue message>`
2. **Xác thực đầu vào (Input Validation)**:
   - Các trường bắt buộc: `<field_name: type, validation rules>`
   - Điều kiện biên / Boundary conditions: `<limits, max size, supported markets>`
3. **Các bước xử lý tuần tự (Step-by-step Transformation)**:
   - Bước 1: `<Trích xuất dữ liệu thô>`
   - Bước 2: `<Biến đổi / Gọi LLM / Render>`
   - Bước 3: `<Kiểm toán chất lượng / Gate verification>`
4. **Đầu ra mong đợi (Expected Output Contract)**:
   - File path / Database table / JSON schema: `<schema contract>`

---

## 3. RÀNG BUỘC KỸ THUẬT & AN TOÀN (CONSTRAINTS)
- **Mạng & Quyền truy cập**: `<Private LAN vs Public WAN; port, endpoint>`
- **Bảo mật & Secrets**: `<Biến môi trường cần nạp; cấm hardcode credentials>`
- **Giới hạn tài nguyên (Budgets)**: `<Timeout, max RAM, max LLM token budget>`
- **Cơ chế Rollback khi có sự cố**: `<Fallback behavior nếu API lỗi hoặc mạng rớt>`
