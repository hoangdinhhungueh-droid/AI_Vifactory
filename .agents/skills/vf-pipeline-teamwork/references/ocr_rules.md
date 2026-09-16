# 🔍 Open Code Review (OCR) Ruleset & Deep Reference

> **Tài liệu tham chiếu chuyên sâu (Progressive Disclosure Reference)** cho Skill `/vf-pipeline-teamwork`.
> Cung cấp quy chuẩn chi tiết về cấu hình `.opencodereview/rule.json`, cú pháp ruleset và các chế độ kiểm toán mã nguồn.

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
5. **Hiến Pháp Invariants**:
   - Chặn đứng vi phạm Rule 118 (Zero-Mock Data) và Rule 128 (Zero Semantic Bias).
   - Bắt buộc Exit Code 0 và Zero High/Critical Defect trên toàn bộ git diff.

---

## 🚀 III. DUAL-MODE EXECUTION

- **Delegation Mode (`ocr delegate`)**: OCR phân tích AST, bóc tách diff và phân giải ruleset, bàn giao cho Host Agent (Antigravity) suy luận sâu — hoàn toàn 0 tốn thêm API token rời.
- **Direct Mode (`ocr review`)**: Tự động hóa headless trên VPS thông qua OpenRouter / Gemini API gateway với context `-b / --background`.
