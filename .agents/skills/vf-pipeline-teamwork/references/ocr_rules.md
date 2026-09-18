# 🔍 Open Code Review (OCR) Ruleset & Deep Reference

> **Tài liệu tham chiếu chuyên sâu (Progressive Disclosure Reference)** cho Skill `/vf-pipeline-teamwork`.
> Cung cấp quy chuẩn chi tiết về cấu hình `.opencodereview/rule.json`, cú pháp ruleset và các tiêu chuẩn kiểm toán đối kháng dành cho **Adversarial Forensic Auditor (Vai 4 - Strictly Review-Only)**.

---

## ⚙️ I. CẤU TRÚC FILE LUẬT TÙY BIẾN (`.opencodereview/rule.json`)

Hệ thống sử dụng file luật tùy biến `.opencodereview/rule.json` đặt tại thư mục gốc repository:
- **Tự động áp dụng**: Khi chạy `runner.py --mode review` hoặc `ocr review`, engine tự động nạp `.opencodereview/rule.json` và hợp nhất (`merge_system_rule: true`) với tập luật hệ thống của ngôn ngữ.
- **Thêm luật mới**: Khai báo thêm pattern vào mảng `rules`:
  ```json
  {
    "path": "path/to/module/**/*.py",
    "rule": "Quy tắc kiểm soát nghiệp vụ riêng cho module...",
    "merge_system_rule": true
  }
  ```
- **Kiểm tra luật đã nạp**:
  ```bash
  ocr rules check path/to/file.py
  ```

---

## 🎯 II. BỘ TIÊU CHÍ BẢO MẬT & BẢO TOÀN TÀI NGUYÊN (OCR RULES INVARIANTS)

Adversarial Forensic Auditor sử dụng bộ tiêu chí này để rà soát tĩnh và ban hành phán quyết trong `FORENSIC_VERDICT.md`:

1. **Memory & Buffer Management**:
   - Chặn memory leaks trong xử lý buffer Sharp / Remotion canvas (B7).
   - Giải phóng bộ nhớ Pillow/OpenCV matrix sau khi xử lý (B5).
2. **Resource & Descriptor Leaks**:
   - Chặn unclosed file descriptors trong audio streaming EdgeTTS / Whisper (B6).
   - Đóng toàn bộ subprocess pipes của ffmpeg / whisper / chrome headless.
3. **Concurrency & Race Conditions**:
   - Chặn race condition trong multi-process concurrency / subprocesses (Orchestrator).
4. **Encoding & Error Handling**:
   - Bắt buộc UTF-8 encoding trên 100% thao tác I/O.
   - Cấm bare `except:` và silent `pass`.
5. **Hiến Pháp Invariants & Quyền VETO**:
   - Chặn đứng vi phạm Rule 118 (Zero-Mock Data) và Rule 128 (Zero Semantic Bias).
   - **Quy tắc VETO**: Nếu tồn tại bất kỳ vi phạm `CRITICAL` hoặc `HIGH`, Auditor bắt buộc kích hoạt quyền **VETO**, cấm tuyệt đối việc merge code hoặc mở cổng Three-Way Sync.

---

## 🛡️ III. NGUYÊN TẮC VẬN HÀNH CỦA ADVERSARIAL AUDITOR (RED TEAM MANDATE)

1. **Strictly Review-Only (Tuyệt Đối Cấm Sửa Code)**:
   - Auditor là quan tòa độc lập, không phải thợ sửa mã. Cấm tuyệt đối việc Auditor tự ý viết code vá lỗi thay cho Builder.
   - Mọi khuyết tật phát hiện được phải trích dẫn chính xác `file:line` kèm phân tích nguyên nhân và yêu cầu khắc phục để trả về cho Builder trong vòng lặp Remediation Loop.
2. **Thẩm Định Độc Lập Trong Luồng Đồng Thời (Simultaneous Verification)**:
   - Auditor vận hành song song với QA Test Harness. Không hạ thấp tiêu chuẩn chỉ vì các bài unit/neighbor tests đã chạy thành công.
   - Tập trung phát hiện các lỗ hổng kiến trúc, nợ kỹ thuật và nguy cơ hồi quy mà test case động có thể bỏ sót.

---

## 🚀 IV. DUAL-MODE EXECUTION

- **Delegation Mode (`ocr delegate`)**: OCR phân tích AST, bóc tách diff và phân giải ruleset, bàn giao cho Host Agent (Antigravity) suy luận sâu — hoàn toàn 0 tốn thêm API token rời.
- **Direct Mode (`ocr review`)**: Tự động hóa headless trên VPS thông qua OpenRouter / Gemini API gateway với context `-b / --background`.
