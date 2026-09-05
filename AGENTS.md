# 🛡️ ANTIGRAVITY OPERATIONAL CONSTITUTION (ALWAYS ON)

> **QUY TẮC BẤT BIẾN CẤP CAO NHẤT CỦA WORKSPACE AI VIDEO FACTORY (VF PIPELINE).**
> Mọi Agent/Subagent bắt buộc tuân thủ 6 Kỷ Luật Thép và cơ chế Định Tuyến Kỹ Năng (Progressive Disclosure) dưới đây:

---

## ⚖️ I. HIẾN PHÁP 7 ĐIỀU LUẬT BẤT BIẾN (IRON LAWS)

1. **RULE 118 (Zero-Mock Data & Ask-Before-Deviating)**:
   - CẤM TUYỆT ĐỐI tự tạo mock data, số liệu giả định (Analytics, Views, CTR, RPM). Chưa có API/số liệu YouTube Studio thực tế thì bắt buộc để `null` và báo cáo rõ ràng.
   - Gặp lỗi kỹ thuật, rate-limit, hoặc thấy quy trình cần điều chỉnh: **DỪNG LẠI NGAY, NÊU RÕ VẤN ĐỀ VÀ HỎI Ý KIẾN USER TRƯỚC KHI THỰC HIỆN BẤT KỲ ĐIỀU GÌ LỆCH KHỎI CHỈ DẪN**. Cấm tự ý đổi luồng.
2. **RULE 119 (Strict Existing Codebase Execution Only)**:
   - CHỈ ĐƯỢC PHÉP thực thi trên các modules/scripts chuẩn trên VPS (`/root/video_factory`). Cấm tự ý viết shadow scripts hoặc script tạm bợ bypass hệ thống.
   - File tạm (test log, stdout, script patch...) BẮT BUỘC lưu tại `/tmp/` và dọn dẹp ngay sau khi xong việc. Cấm xả rác vào thư mục gốc.
3. **RULE 121 (Strict Verification Protocol)**:
   - Chỉ được xác nhận hoàn thành (PASS) khi có bằng chứng pháp y thực tế: In log HTTP `200 OK`, exit code `0`, hoặc trích dẫn trực tiếp `File Path` & `Line Numbers` đã sửa (`grep_search`/`view_file`). Cấm tuyệt đối nghiệm thu hình thức.
4. **RULE 122 (Pixel-Level Visual Audit Gate & Zero-Mock Score)**:
   - Nghiệm thu ảnh B4/B5/S7 BẮT BUỘC phải trích xuất frame/file ảnh thật và mở bằng `view_file` theo tiêu chuẩn 4 Trục:
     1. *UI & Artifact*: 0% dính thanh công cụ trình duyệt, nút bấm, watermark.
     2. *Alpha & Edge Integrity*: 0% thủng lỗ trên nhân vật/áo sơ mi/tóc; viền mịn, không lem magenta.
     3. *Style Conformance*: 100% đồ họa minh họa Stylized Graphic Novel Editorial Illustration có nét vẽ comic mực và cel-shading (Rule 116 & 435). CẤM ảnh chụp thật photorealistic.
     4. *Era Context*: Bối cảnh BG và trang phục FG khớp thời đại câu chuyện. CẤM lạc thời đại.
   - CẤM TUYỆT ĐỐI giả mạo điểm số (như hardcode 9.8). Điểm số phải từ phân tích thị giác thật.
5. **RULE 123 (Mandatory Real-Data Pipeline Testing)**:
   - 100% kiểm thử pipeline (B1–B11) bắt buộc dùng dữ liệu live thời gian thực (Google Trends RSS live, YouTube Data API live, Notion live). CẤM TUYỆT ĐỐI dummy/synthetic seeds.
   - Tin nhắn test Telegram chỉ gửi vào kênh test hoặc in ra console, trừ khi User yêu cầu rõ ràng nghiệm thu trên Telegram thật.
6. **RULE 124 (Atomic Code-ification & Ask-When-Amnesic)**:
   - **Chốt là code ngay (Atomic Commit on Agreement)**: Ngay khi User phê duyệt giải pháp/kiến trúc, Agent BẮT BUỘC thực thi code hóa ngay trong tool call kế tiếp xuống đĩa (`replace_file_content` / `write_to_file`). Cấm nói suông rồi trôi mất.
   - **Quên là phải hỏi lại (Ask-When-Amnesic)**: Sau nén ngữ cảnh (compaction/truncation), nếu thiếu dữ kiện hoặc nghi ngờ trạng thái, BẮT BUỘC dừng lại hỏi User, cấm đoán mò nói bừa.
7. **RULE 125 (Single Pipeline Version & Zero-Ghost Remnant Mandate)**:
   - Khi thực hiện các bước trong pipeline hoặc bất kỳ task nào, nếu có cập nhật luồng mới:
     1. **Verification & ISO Testing**: BẮT BUỘC chạy test luồng mới (kiểm thử hợp đồng, neighbor-testing) đạt PASS trước khi kết luận hoàn thành.
     2. **Atomic Rewiring & Ghost Purge**: BẮT BUỘC đề xuất đè hoặc đổi trỏ toàn bộ caller trong pipeline sang luồng mới; dọn dẹp sạch sẽ toàn bộ tàn dư, logic cũ, shadow code.
     3. **Single Truth**: TUYỆT ĐỐI KHÔNG BAO GIỜ để tồn tại song song 2 version trong cùng một pipeline dẫn đến sai cấu trúc, trùng lặp (duplication) hoặc tàn dư bóng ma (ghost remnants/bypasses).

---

## 🗺️ II. MA TRẬN ĐỊNH TUYẾN KỸ NĂNG (PROGRESSIVE DISCLOSURE)

Thay vì nạp toàn bộ pipeline vào context ban đầu, Agent kích hoạt Skill chuyên môn hoặc nạp tài liệu tương ứng Just-in-Time khi nhận nhiệm vụ:

| Lệnh / Giai Đoạn | Nghiệp Vụ Trọng Tâm | Kỹ Năng / Tài Liệu SoT Nạp Vào | Quy Chuẩn Ràng Buộc |
| :--- | :--- | :--- | :--- |
| **SoT & Registry** | Tra cứu Database ID, Page ID, Schema DB | Skill `notion-sot-second-brain` | Progressive Querying 3 Tầng |
| **B1, B1.5, B2** | Trend RSS live, YouTube Recon, Kịch bản 5 Beat | `notion_sot_second_brain.md` (Pillar 2) & `tests/ci_neighbor_tester.py` | Rule 444 (An Ong Hook), 445 (5 Beat Docudrama), 446 (Native-First), 447 (CI/CD Neighbor-Testing) |
| **B3, B3.5** | Dynamic Director Plan & Prompt Forge | `PIPELINE_CONTRACTS.md` | Layer 1 BG (16:9) + Layer 2 FG (1:1) Prompt English |
| **B4, B5** (`/run:image`) | Sinh ảnh Gemini Web & Tách nền Chroma HSV | Skill `vf-image-gen` | Rule 116, 122 (Visual Audit 4 trục), Rule 435–439 |
| **B6, B7, B8** | TTS, Whisper Subtitles, Remotion Render CPU | `notion_sot_second_brain.md` (Media Production Hub) | Rule 120 (Karaoke millisecond sync, `durationInFrames` chuẩn timestamp) |
| **B10** | SEO Metadata, Synthetic Media, Gate 2 | `PIPELINE_CONTRACTS.md` | `status.containsSyntheticMedia: true`, Hero Thumbnail |
| **B11** (`/run:b11`) | Analytics 48h, Feedback Dreaming Loop | Skill `vf-b11-analytics` | Rule 113 (48h Law), Rule 440–442 |

---

## 🎯 III. NGUYÊN TẮC QUẢN TRỊ TÁC VỤ (TASK DISCIPLINE)
1. **Task-Level Contract**: Mọi nhiệm vụ lớn / Sprint bắt buộc neo theo file `ORIGINAL_REQUEST.md` (chứa User Request gốc, Requirements R1..Rn và Acceptance Criteria `[ ]`).
2. **Interface Contracts**: Khế ước dữ liệu JSON IN/OUT giữa các block và danh mục file trên VPS tra cứu tại `PIPELINE_CONTRACTS.md`.
