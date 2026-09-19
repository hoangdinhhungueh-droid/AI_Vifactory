# 🛡️ ANTIGRAVITY OPERATIONAL CONSTITUTION (ALWAYS ON)

> **QUY TẮC BẤT BIẾN CẤP CAO NHẤT CỦA WORKSPACE AI VIDEO FACTORY (VF PIPELINE).**
> Mọi Agent/Subagent bắt buộc tuân thủ 18 Kỷ Luật Thép và cơ chế Định Tuyến Kỹ Năng (Progressive Disclosure) dưới đây:

---

## ⚖️ I. HIẾN PHÁP ĐIỀU LUẬT BẤT BIẾN (IRON LAWS)

1. **RULE 118 (Zero-Mock Data & Ask-Before-Deviating)**:
   - CẤM TUYỆT ĐỐI tạo mock data, số liệu giả định (Analytics, Views, CTR, RPM). Chưa có API/số liệu YouTube Studio thực tế thì bắt buộc để `null` và báo cáo rõ ràng.
   - Gặp lỗi kỹ thuật, rate-limit, hoặc thấy quy trình cần điều chỉnh: **DỪNG LẠI NGAY, NÊU RÕ VẤN ĐỀ VÀ HỎI Ý KIẾN USER TRƯỚC KHI THỰC HIỆN BẤT KỲ ĐIỀU GÌ LỆCH KHỎI CHỈ DẪN**. Cấm tự ý đổi luồng.

2. **RULE 119 (Strict Existing Codebase Execution Only)**:
   - CHỈ ĐƯỢC PHÉP thực thi trên các modules/scripts chuẩn trên VPS (`/root/video_factory`). Cấm tự ý viết shadow scripts hoặc script tạm bợ bypass hệ thống.
   - File tạm (test log, stdout, script patch...) BẮT BUỘC lưu tại `/tmp/` và dọn dẹp ngay sau khi xong việc qua `resource_recycler.py`. Cấm xả rác vào thư mục gốc.

3. **RULE 121 (Strict Verification Protocol)**:
   - Chỉ được xác nhận hoàn thành (PASS) khi có bằng chứng pháp y thực tế: In log HTTP `200 OK`, exit code `0`, hoặc trích dẫn trực tiếp `File Path` & `Line Numbers` đã sửa (`grep_search`/`view_file`). Cấm tuyệt đối nghiệm thu hình thức.

4. **RULE 122 (Pixel-Level Visual Audit Gate & Zero-Mock Score)**:
   - Nghiệm thu ảnh B4/B5/S7 BẮT BUỘC phải trích xuất frame/file ảnh thật và mở bằng `view_file` theo tiêu chuẩn 4 Trục:
     1. *UI & Artifact*: 0% dính thanh công cụ trình duyệt, nút bấm, watermark.
     2. *Alpha & Edge Integrity*: 0% thủng lỗ trên nhân vật/áo/tóc; viền mịn, không lem magenta (#FF00FF).
     3. *Style Conformance*: 100% đồ họa minh họa Stylized Graphic Novel Editorial Illustration có nét vẽ comic mực và cel-shading (Rule 116 & 435). CẤM ảnh chụp thật photorealistic.
     4. *Era, Market & Ethnic Context*:
        - **Foreground (FG)**: Nhân chủng học (khuôn mặt, mắt, tóc, da) và trang phục phản ánh chuẩn 100% thị trường (JP -> Nhật, KR -> Hàn, VN -> Việt, US -> Âu/Mỹ). CẤM "Tây hóa" nhân vật Á Châu. Tư thế kịch tính (dynamic body posing, cấm dáng đứng đơ ảnh thẻ), biểu cảm vi mô sắc lạnh (no blank stare), chủ động tương tác với đạo cụ bản địa (triện đỏ hanko/ingam/mộc đỏ, thẻ sawonjeung...).
        - **Background (BG)**: Bối cảnh kiến trúc, nội thất, đô thị phản ánh đúng địa lý/văn hóa thị trường. CẤM chữ tiếng Anh/Latin trên biển hiệu, tường, bảng biểu ở thị trường bản địa (JP, KR, VN).
        - **Nhất Quán FG/BG**: Ánh sáng, góc chiếu và trang phục FG phải hòa hợp tuyệt đối với không gian BG.
   - CẤM TUYỆT ĐỐI giả mạo điểm số (như hardcode 9.8). Điểm số phải từ phân tích thị giác thật.

5. **RULE 123 (Mandatory Real-Data Pipeline Testing)**:
   - 100% kiểm thử pipeline (B1–B11) bắt buộc dùng dữ liệu live thời gian thực (Google Trends RSS live, YouTube Data API live, Notion live). CẤM TUYỆT ĐỐI dummy/synthetic seeds.
   - Tin nhắn test Telegram chỉ gửi vào kênh test hoặc in ra console, trừ khi User yêu cầu rõ ràng nghiệm thu trên Telegram thật.

6. **RULE 124 (Atomic Code-ification & Ask-When-Amnesic)**:
   - **Chốt là code ngay (Atomic Commit on Agreement)**: Ngay khi User phê duyệt giải pháp/kiến trúc, Agent BẮT BUỘC thực thi code hóa ngay trong tool call kế tiếp xuống đĩa (`replace_file_content` / `write_to_file`). Cấm nói suông rồi trôi mất.
   - **Quên là phải hỏi lại (Ask-When-Amnesic)**: Sau nén ngữ cảnh (compaction/truncation), nếu thiếu dữ kiện hoặc nghi ngờ trạng thái, BẮT BUỘC dừng lại hỏi User, cấm đoán mò nói bừa.

7. **RULE 125 (Single Pipeline Version & Zero-Ghost Remnant Mandate)**:
   - Khi thực hiện cập nhật luồng mới:
     1. **Verification & ISO Testing**: BẮT BUỘC chạy test luồng mới (kiểm thử hợp đồng, neighbor-testing) đạt PASS trước khi kết luận hoàn thành.
     2. **Atomic Rewiring & Ghost Purge**: BẮT BUỘC đổi trỏ toàn bộ caller sang luồng mới; dọn dẹp sạch sẽ toàn bộ tàn dư, logic cũ, shadow code. Cấm để lại file `.bak*`, `.backup*`, file dead scripts.
     3. **Single Truth**: CẤM tồn tại song song 2 version trong cùng một pipeline gây sai cấu trúc, trùng lặp hoặc bypass ngầm.
     4. **Zero-Ambiguity & Explicit Code Mandate**: CẤM để tồn tại docstring, comment, inline note cũ mâu thuẫn với code thực tế. Đồng bộ hóa 100% tài liệu nội hàm ngay trong cùng commit.
     5. **Automated 4-Layer Ghost Hunter Gate (VETO Authority)**: BẮT BUỘC chạy `scripts/orchestrator/ghost_code_detector.py` quét toàn bộ đĩa cứng vật lý (cả VPS và Local, bỏ qua blindness của .gitignore). Bất kỳ phát hiện nào về `.bak*`, orphan scripts, dead imports, hoặc bypass shadow code sẽ lập tức kích hoạt quyền VETO, trả exit code 1 và dừng toàn bộ CI/CD, runner, smoketest.

8. **RULE 126 (Three-Way Physical Sync & Zero-False-Success Mandate)**:
   - **Bảo chứng đồng bộ vật lý (VPS ⇄ GitHub ⇄ Local/Notion bit-for-bit)**:
     - CẤM TUYỆT ĐỐI chỉ sửa code ở local Windows rồi báo "Đã đồng bộ xong VPS". Mọi thay đổi bắt buộc ghi xuống đĩa cứng VPS (`/root/video_factory`), biên dịch `python3 -m py_compile` đạt exit code `0`, và in diff/log thực tế.
     - **MCP Recovery**: Nếu MCP `vf-factory` bị timeout/ngắt socket, BẮT BUỘC fallback sang runner chuẩn `scripts/vps_runner.py` (Fresh-Session Auto-Init + Cloudflare Token). Nếu vẫn mất kết nối -> DỪNG LẠI HỎI USER NGAY (Rule 118).
     - **Commit & Push từ VPS**: Thực thi `git -C /root/video_factory add <files> && git -C /root/video_factory commit -m "<msg>" && git -C /root/video_factory push origin main` lên repo GitHub. Bắt buộc đối soát `git status` trả về `working tree clean`.
     - **Cổng Bảo Chứng GitHub Actions CI Bắt Buộc**: Bắt buộc chạy `python scripts/watch_github_ci.py --commit <HEAD_SHA>` (hoặc `runner.py --mode sync`) theo dõi GitHub Actions Workflow Run cho đến khi `conclusion: success` (exit code 0). CẤM BÁO CÁO HOÀN TẤT KHI CI CHƯA PASS. Nếu CI fail, tải log lỗi về, tự fix và push lại.
     - **Đồng bộ ngược Local & Notion**: Cập nhật file tương ứng vào local Windows Workspace và Notion SoT, đối soát SHA256 đạt 100% bit-for-bit parity.

9. **RULE 127 (Anti-Tunnel-Vision & Mandatory Programmatic Runtime Execution Gate)**:
   - **Cấm Nghiệm Thu Qua `py_compile` Đơn Thuần**: `py_compile` chỉ bắt `SyntaxError`, không bắt được `NameError`/`ImportError`/`AttributeError`.
   - **Bắt Buộc Thực Thi Sống Hàm Sửa Đổi**: BẮT BUỘC chạy Python runtime thực thi trực tiếp hàm đã sửa (`python3 -c "from <module> import <func>; <func>(...)"`) trên VPS với input tối thiểu, in rõ output hoặc exit code `0`.
   - **Phân Định Rõ Ràng & Master E2E Smoke Gate**: Báo cáo nghiệm thu bắt buộc nêu rõ (1) Phạm vi đã sửa kèm bằng chứng thực thi; (2) Các module liên đới còn tồn đọng chưa sửa. Mọi can thiệp B1–B3.5 bắt buộc chạy `python3 /root/video_factory/scripts/e2e_pipeline_smoketest.py` đạt `ALL PIPELINE GATES PASSED`.

10. **RULE 128 (Anti-Semantic-Bias & Generic Contract Architecture Mandate)**:
    - **Cấm Hardcode Bias Đề Tài Trong Tài Liệu & Khế Ước**: CẤM TUYỆT ĐỐI đưa dữ liệu/tên tập/nhân vật cụ thể của một Episode vào khế ước (`PIPELINE_CONTRACTS.md`), system rules, prompt templates.
    - **Chuẩn Hóa Generic Contract Pattern**: Mọi schema bắt buộc dùng Generic Placeholders kèm type annotations (`"<MARKET>_EP<0000>_<topic_slug>"`, regex `^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$`, `"<FLOAT: 0.0 - 100.0>"`). Áp dụng phổ quát cho mọi thị trường (`EN`, `VN`, `JA`, `KO`...).
    - **Tách Biệt Schema và Example**: Ví dụ minh họa bắt buộc đặt trong block `[!NOTE]` riêng với cảnh báo cấm tái sử dụng giá trị cụ thể.

11. **RULE 129 (Autonomous Deep Reasoning & Proactive Clarification Gate - Chuẩn Phong Cách Claude)**:
    - **Tự Động Bật Mặc Định Trong Mọi Phiên Chat**: Kích hoạt tư duy First-Principles và suy luận đa chiều TRƯỚC KHI thực hiện bất kỳ lệnh can thiệp nào có tính kiến trúc, refactor, rẽ nhánh hoặc mơ hồ.
    - **Quy Trình 3 Bước**: (1) Bóc tách mục tiêu cốt lõi & Điểm mù (Intent & Blind-Spots); (2) Đánh giá 3 Trục Độc Lập (Kiến trúc & Khế ước, Hiệu năng VPS, Vận hành 3 chiều); (3) Phân tích Đánh đổi (Trade-offs: Option A vs Option B).
    - **Cổng Phản Vấn Chủ Động Gọn Gẽ**: Khi cần quyết định từ User, dừng lại ở cổng tham vấn gồm 4 phần: Tóm tắt Nhận định (1-2 câu) -> Ma trận Đánh đổi -> Khuyến nghị Chuyên môn -> Câu hỏi Chốt Trực Diện (dùng `ask_question` nếu là trắc nghiệm trực quan).
    - **Ranh Giới Chống Phiền Toái**: Bắt buộc hỏi khi thay đổi kiến trúc/rủi ro cao; cấm hỏi lắt nhắt khi lệnh đã rõ ràng 100% hoặc kiểm thử đơn thuần. Khi chốt là code ngay (Rule 124).

12. **RULE 130 (Factual Causal Integrity & Search-Intent Payoff Mandate)**:
    - **Cấm Bịa Đặt Mối Quan Hệ Nhân Quả & Twist Tiện Lợi**: Chuỗi nhân quả bắt buộc phân định 2 cấp:
      + *Level 1 (Primary Catalyst)*: Sự kiện/ngòi nổ thực tế khách quan có mốc thời gian và chủ thể rõ ràng.
      + *Level 2 (Transmission Mechanism)*: Phản ứng dây chuyền của cấu trúc hệ thống, thể chế hoặc thị trường. CẤM đánh tráo Level 2 thành Level 1 để tạo giật gân vô căn cứ.
    - **Factual High-Stakes Hook (0-60s, Rule 444)**: Cấu thành từ 3 thành tố: (1) Catalyst Event; (2) Quantitative Metric từ Grounding Table; (3) Core Systemic Paradox.
    - **Search-Intent Payoff & Anti-Bait-and-Switch**: Act I & II bắt buộc đối diện và giải mã trực tiếp từ khóa nóng mà người xem tìm kiếm. CẤM mượn từ khóa làm mồi nhử rồi thoái thác sang bài giảng lý thuyết chung chung.
    - **Áp Dụng Generic Cho 7 Trục Đề Tài Vàng & 3 Epochs**: Áp dụng chuẩn `<CATALYST_EVENT> -> <TRANSMISSION_MECHANISM> -> <CORE_SYSTEMIC_PARADOX> -> <DIRECT_SEARCH_PAYOFF>` trên cả 7 Trục. Phân loại nhịp thời gian (`MACRO_SAGA`, `MID_TACTICAL`, `FLASH_CRISIS`) và trích xuất bảng `causal_epochs`.

13. **RULE 131 (10X Beat Architecture & Editorial Signal Purity Mandate)**:
    - **Khử Nhiễu & Tách Biệt Prompt Nghiệp Vụ**: CẤM đưa tài liệu content marketing, social copy chung chung vào prompt kịch bản B2. B2 chỉ nhận nguyên lý điều tra, pacing docudrama và bài học B11.
    - **Cấu Trúc 5 Beat Docudrama**: Tuân thủ nghiêm ngặt cấu trúc 5 Beat (Beat 1 Cold Strike 0-20s -> Paradox 20-60s -> Ticking clock; Beat 2 False Narrative & Red Herring; Beat 3 Forensic Paper Trail & Pattern Interrupt 2-6 từ; Beat 4 Smoking Gun & Climax; Beat 5 Modern Mirror & Living Warning). Chi tiết kịch bản quản trị tập trung tại `config/prompts/b2_editorial_prompt.md` và Notion SoT theo Rule 133.
    - **Cấm Mở Đầu Bằng Câu Hỏi Giả Định ("Imagine...")**: Bắt buộc mở đầu trực diện bằng sự kiện ngòi nổ thực tế và con số lượng hóa từ Grounding Table trong 60 từ đầu.
    - **Căng Thẳng Con Người Trong Chiếc Bẫy Thể Chế**: Thể hiện áp lực thể chế qua con người bị mắc kẹt thực tế (người phụ trách vận hành, nhân viên thanh toán, cơ quan giám sát).

14. **RULE 132 (Strict Decoupled Engine & Pure Transmission Pipe Mandate)**:
    - **Code Là Ống Dẫn Thuần Túy (Pure Transmission Engine)**: Mã nguồn Python (`app/services/*`, `scripts/*`) CHỈ chứa logic hạ tầng kỹ thuật: gọi API, trích xuất dữ liệu, định dạng JSON/Markdown, kiểm tra schema, render video. CẤM TUYỆT ĐỐI nhúng text prompt nghiệp vụ, văn phong kể chuyện, triết lý docudrama vào biến chuỗi trong code `.py`.
    - **Notion & Config Là Nguồn Tri Thức Duy Nhất**: Toàn bộ Prompt templates, nguyên lý 5 Beat, cấu trúc Hook, bài học B11 lưu trữ tại Notion SoT và nạp động qua `skill_loader.py` (caching 3600s, offline fallback `config/prompts/*.md`).
    - **Cổng CI Linter Khử Nhiễm Ngữ Nghĩa**: Tự động chặn commit nếu phát hiện prompt văn phong hoặc case study cụ thể bị hardcode vào code Python.

15. **RULE 133 (Notion AI Skill Delegation vs. Antigravity Operational Scope Mandate)**:
    - **Skill AI Notion Quản Trị Nghiệp Vụ Prompt & Kịch Bản/Đạo Diễn**: Mọi quy chuẩn nghiệp vụ Prompt Engineering, cấu trúc kịch bản (Rule 130, 131, 444), mỹ thuật B3/B3.5, bài học B11 BẮT BUỘC lưu trữ trên Notion SoT (`Skill AI` page `ac901989-2400-827e-bda2-8175dabdcf13`, `Content Engine Hub`, `Media Production Hub`) và `config/prompts/*.md`.
    - **AGENTS.md Chỉ Chứa Kỷ Luật Vận Hành Trực Tiếp Của Antigravity**: `AGENTS.md` CHỈ ghi nhận các Kỷ luật thép chi phối hành vi trực tiếp của Agent (Rule 118, 119, 121, 124, 126, 127, 129, 134...). CẤM TUYỆT ĐỐI đưa toàn văn nội dung prompt kể chuyện, hướng dẫn viết văn, hay chi tiết nghệ thuật tạo hình vào `AGENTS.md` gây lãng phí token nạp mỗi phiên chat và làm loãng khả năng tuân thủ kỷ luật thực thi.

16. **RULE 134 (Exact Parity, Full-Text Consistency & Adversarial Boundary Verification Gate)**:
    - **Cấm Nghiệm Thu Cục Bộ Bằng Smoke Test Đơn Thuần**: Smoke test chỉ chứng minh luồng chính không sập (happy path), không chứng minh hằng số cấu hình và tham số nghiệp vụ đã khớp 100%.
    - **Bắt Buộc Quét Nhất Quán Văn Bản Toàn Diện (Full-Text Consistency Sweep)**: Khi thay đổi bất kỳ hằng số cấu hình, ngưỡng điểm (`viability_score >= 8.0`), danh mục (7 Canonical Pillars), hoặc schema: BẮT BUỘC chạy tìm kiếm toàn diện (`grep_search`/`grep -rn`) trên toàn bộ codebase VPS và Workspace. CẤM để xảy ra lệch pha giá trị giữa các file.
    - **Kiểm Thử Đối Kháng Nghiệp Vụ Biên Trong CI**: Mọi bài test CI (`tests/ci_neighbor_tester.py`) BẮT BUỘC chứa các câu lệnh `assert` cụ thể kiểm tra sự đồng nhất giá trị hằng số, threshold, chuỗi cảnh báo và boundary context.
    - **Chốt Chặn Kiểm Toán Pháp Y Độc Lập Trước Khi Đồng Bộ**: Vai Forensic Auditor trong `/vf-pipeline-teamwork` bắt buộc quét đối kháng vi sai (Differential Audit Checklist). Đạt 100% CLEAR mới bàn giao cho Three-Way Sync Coordinator.

17. **RULE 135 (Ground-Truth Video Timeline Chapter Synchronization Mandate)**:
    - **Remotion Rendered Timeline Là Chân Lý Duy Nhất Cho YouTube Chapters**: Mốc thời gian chương hồi (`00:00`, `MM:SS`) trên YouTube Description BẮT BUỘC trích xuất từ `remotion_props.json` (tích lũy `durationInFrames / fps` của các scene thực tế đã đồng bộ Whisper word-level timestamps). CẤM tính mốc chapter từ độ dài lý thuyết, tỷ lệ % ước lượng thô, hay tổng thời lượng audio thô rời rạc.
    - **Tự Động Hóa Đồng Bộ Tại B10 Upload**: Pipeline BẮT BUỘC gọi hàm chuẩn hóa `sync_exact_chapters_from_remotion()`. Mốc bắt đầu luôn là `00:00`, tối thiểu 3 chapter, mỗi chapter cách nhau ít nhất 10 giây, tăng dần theo thời gian.

18. **RULE 136 (Zero-Asset-Leak & Pure Beat Header Mandate)**:
    - **Cấm Tuyệt Đối Rò Rỉ Mã Asset / Layer / Hash Lên Video**: Thẻ speaker tag / lower-third banner phụ đề trên video Remotion CẤM TUYỆT ĐỐI việc đọc hoặc fallback sang `foreground_reuse_key`, `background_reuse_key`, tên layer, đuôi file (`.png`), hay mã hash nội bộ. CẤM hardcode tiền tố nội bộ mang tính shadow code (như `"ARCHIVE X // "`) trong renderer component `index.tsx`.
    - **Chuẩn Hóa Thẻ Định Danh Phân Cảnh Phổ Quát**: Thẻ phụ đề chỉ được phép hiển thị 2 trường hợp: (1) Nhân vật đối thoại/phát biểu: `TÊN // VAI TRÒ`; (2) Thẻ nhịp Beat định danh: `BEAT <X>: <TIÊU ĐỀ BEAT>`. Áp dụng generic phổ quát cho mọi thị trường (EN, JP, KR, VN...).

---

## 🗺️ II. MA TRẬN ĐỊNH TUYẾN KỸ NĂNG (PROGRESSIVE DISCLOSURE)

Thay vì nạp toàn bộ pipeline vào context ban đầu, Agent kích hoạt Skill chuyên môn hoặc nạp tài liệu tương ứng Just-in-Time khi nhận nhiệm vụ:

| Lệnh / Giai Đoạn | Nghiệp Vụ Trọng Tâm | Kỹ Năng / Tài Liệu SoT Nạp Vào | Quy Chuẩn Ràng Buộc |
| :--- | :--- | :--- | :--- |
| **SoT & Registry** | Tra cứu Database ID, Page ID, Schema DB | Skill `notion-sot-second-brain` | Progressive Querying 3 Tầng |
| **B1, B1.5, B2** | Trend RSS live, YouTube Recon, Kịch bản 5 Beat | `notion_sot_second_brain.md` & `tests/ci_neighbor_tester.py` | Rule 444 (An Ong Hook), 445 (5 Beat Docudrama), 446 (Native-First), 447 (Neighbor-Testing) |
| **B2.6 / B3_AUDIO** | Hollywood Audio Spine, Beat-Level Edge-TTS, Word Karaoke, Subtitles SRT (`app/services/beat_tts_engine.py`) | `notion_sot_second_brain.md` (Media Production Hub) & `PIPELINE_CONTRACTS.md` | Rule 120 (Karaoke millisecond sync, `durationInFrames` chuẩn timestamp, Hard Gate) |
| **B3, B3.5** | Dynamic Director Plan (Timecode-Locked) & Prompt Forge | `PIPELINE_CONTRACTS.md` | Layer 1 BG (16:9) + Layer 2 FG (1:1) Prompt English, Rule 120 Hard Gate |
| **B4, B5** (`/run:image`) | Sinh ảnh Gemini Web & Tách nền Chroma HSV | Skill `vf-image-gen` | Rule 116, 122 (Visual Audit 4 trục), Rule 435–439 |
| **B6, B7, B8** | Remotion Master Video Render CPU, BGM Cinematic Ducking, Video QA Audit | `notion_sot_second_brain.md` (Media Production Hub) | Rule 120, Rule 135 (Remotion chapters), Rule 136 (Clean speaker tags) |
| **B10** | SEO Metadata, Synthetic Media, Gate 2 | `PIPELINE_CONTRACTS.md` | `status.containsSyntheticMedia: true`, Hero Thumbnail, Rule 135 Chapters |
| **B11** (`/run:b11`) | Analytics 48h, Feedback Dreaming Loop | Skill `vf-b11-analytics` | Rule 113 (48h Law), Rule 440–442 |
| **Teamwork Pipeline** (`/vf-pipeline-teamwork`) | Hội Đồng Multi-Agent Harness 4 vai (Architect, Builder, QA Test Harness, Adversarial Auditor - strictly review) & 3 Cặp Docs | Skill `vf-pipeline-teamwork` & `scripts/orchestrator/` | Rule 118, 119, 121, 124, 125, 126, 127, 128, 129, 134 |

---

## 🎯 III. NGUYÊN TẮC QUẢN TRỊ TÁC VỤ (TASK DISCIPLINE)
1. **Task-Level Contract**: Mọi nhiệm vụ lớn / Sprint bắt buộc neo theo file `ORIGINAL_REQUEST.md` (chứa User Request gốc, Requirements R1..Rn và Acceptance Criteria `[ ]`).
2. **Interface Contracts**: Khế ước dữ liệu JSON IN/OUT giữa các block và danh mục file trên VPS tra cứu tại `PIPELINE_CONTRACTS.md`.
3. **Autonomous Clarification Protocol**: Mọi tác vụ có tính đa chiều, rẽ nhánh kỹ thuật hoặc mơ hồ bắt buộc kích hoạt Cổng Phản Vấn Chủ Động (Rule 129), suy luận sâu và làm rõ với User trước khi triển khai sâu.
