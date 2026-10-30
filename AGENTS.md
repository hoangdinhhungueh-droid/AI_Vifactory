# 🛡️ ANTIGRAVITY OPERATIONAL CONSTITUTION (CANONICAL 2.0)

> **QUY TẮC BẤT BIẾN CẤP CAO NHẤT CỦA WORKSPACE AI VIDEO FACTORY (AVF-STAB-001).**
> Ràng buộc 100% Agent/Subagent. Hệ thống vận hành độc quyền trên **Canonical Pipeline 2.0 (S1–S11)** và **Vox Engine v3**.
> Mọi chỉ đạo điều phối quy về 1 cổng duy nhất: `/vf-pipeline-teamwork` (CLI lõi: `python -m orchestrator.run_pipeline`).

---

## 🏛️ I. THAM CHIẾU GLOBAL RULES (NẠP TỰ ĐỘNG MỖI PHIÊN)

Các hiến pháp phổ quát nạp tự động từ `~/.gemini/config/rules/` — AGENTS.md tuyệt đối không lặp lại nội dung:
- 🛡️ **R137 (Anti-Destructive Action & Zero-Drive-Wipe Iron Law)** (`anti_destructive_action_iron_law.md`): Bảo vệ dữ liệu Local & VPS. Phân tách Disconnect != Wipe; Blacklist lệnh tử thần (`Remove-Item -Recurse -Force`, `rm -rf`, `rmdir /s /q`); Cấm xóa đệ quy xuyên Symlink/Junction (`cmd /c rmdir`, `unlink`); Quy trình xóa 2 bước (Dry-run -> Phê duyệt).
- 🧠 **R129 (Autonomous Deep Reasoning & Crisp Inquiry Protocol)** (`autonomous_deep_inquiry.md`): Tự động bật suy luận First-Principles 3 bước (Intent & Blind-Spots -> Trade-Offs -> Clarification Threshold). Cổng phản vấn gọn gẽ 4 phần (Tóm tắt nhận định -> Trade-offs -> Khuyến nghị -> Câu hỏi trực diện). Kỷ luật chốt là code ngay (Atomic Commit on Agreement).
- 📊 **Truthful Reporting & Zero-Mock-Hallucination Iron Law** (`truthful_reporting_and_real_data_iron_law.md`): Áp dụng phổ quát (Universal Domain Scope). Cấm 100% số liệu mock (YouTube Views/CTR/RPM, Balance ví sàn, Telemetry máy chủ); chưa có credentials/dữ liệu thực bắt buộc để `null` + báo cáo trung thực.
- 📈 **Hệ Thống Phân Tích Định Lượng & Giao Dịch (Tham Chiếu Global)**:
  - 🚫 **Anti-Sycophancy, Independent Quant Logic & Clean Thinking** (`anti_sycophancy_and_clean_thinking_iron_law.md`): Kỷ luật SMC/ICT, Range/Chop, bảo vệ vốn tối cao, chống thiên kiến nhìn lại Hindsight.
  - 📈 **TradingView Pine Script v6 Standard** (`pine_script_v6_standard.md`): Bắt buộc `//@version=6`, cấm gọi hàm hiển thị/cảnh báo trong local scope, chuẩn màu built-in, quản lý bộ nhớ Box/Label/Line/Table.

---

## ⚖️ II. KỶ LUẬT THÉP CANONICAL PIPELINE 2.0 (VOX ENGINE V3)

### 1. Cụm A: Nghiệm Thu Thực Chứng & Zero-Mock (R118, R121, R123, R127)
- **R118 (Zero-Mock Data & Ask-Before-Deviating)**: CẤM TUYỆT ĐỐI tạo mock data, số liệu giả định (Analytics, Views, CTR, RPM). Chưa có API YouTube Studio thực tế bắt buộc để `null` và báo cáo rõ. Gặp lỗi kỹ thuật, rate-limit, hoặc cần điều chỉnh quy trình: **DỪNG LẠI NGAY, NÊU RÕ VẤN ĐỀ VÀ HỎI Ý KIẾN USER TRƯỚC KHI THỰC HIỆN BẤT KỲ ĐIỀU GÌ LỆCH KHỎI CHỈ DẪN**. Cấm tự ý đổi luồng.
- **R121 (Strict Verification Protocol)**: Chỉ được xác nhận hoàn thành (PASS) khi có bằng chứng pháp y thực tế: In log HTTP `200 OK`, exit code `0`, hoặc trích dẫn trực tiếp `File Path` & `Line Numbers` đã sửa (`grep_search`/`view_file`). Cấm tuyệt đối nghiệm thu hình thức.
- **R123 (Mandatory Real-Data Pipeline Testing)**: 100% kiểm thử pipeline (S1–S11) bắt buộc dùng dữ liệu live thời gian thực (Google Trends RSS live, YouTube Data API live, Notion live). CẤM TUYỆT ĐỐI dummy/synthetic seeds. Tin nhắn test Telegram chỉ gửi vào kênh test hoặc in ra console, trừ khi User yêu cầu rõ ràng nghiệm thu trên Telegram thật.
- **R127 (Anti-Tunnel-Vision & Mandatory Programmatic Runtime Execution Gate)**:
  + **Cấm Nghiệm Thu Qua `py_compile` Đơn Thuần**: `py_compile` chỉ bắt `SyntaxError`, không bắt được `NameError`/`ImportError`/`AttributeError`.
  + **Bắt Buộc Thực Thi Sống Hàm Sửa Đổi**: BẮT BUỘC chạy Python runtime thực thi trực tiếp hàm đã sửa (`python3 -c "from <module> import <func>; <func>(...)"`) trên VPS với input tối thiểu, in rõ output hoặc exit code `0`.
  + **Master E2E Smoke Gate**: Báo cáo nghiệm thu bắt buộc nêu rõ (1) Phạm vi đã sửa kèm bằng chứng thực thi; (2) Các module liên đới còn tồn đọng chưa sửa. Mọi can thiệp pipeline bắt buộc chạy `python3 /root/video_factory/scripts/e2e_pipeline_smoketest.py` đạt `ALL PIPELINE GATES PASSED`.

### 2. Cụm B: Kỷ Luật Mã Nguồn, Kiến Trúc & Blast Radius (R119, R124, R125, R128, R132, R138, R139)
- **R119 (Strict Existing Codebase Execution Only)**: CHỈ ĐƯỢC PHÉP thực thi trên các modules/scripts chuẩn trên VPS (`/root/video_factory`). Cấm tự ý viết shadow scripts hoặc script tạm bợ bypass hệ thống. File tạm (test log, stdout, script patch...) BẮT BUỘC lưu tại `/tmp/` và dọn dẹp ngay sau khi xong việc qua `resource_recycler.py`. Cấm xả rác vào thư mục gốc.
- **R124 (Atomic Code-ification & Ask-When-Amnesic)**:
  + **Chốt là code ngay (Atomic Commit on Agreement)**: Ngay khi User phê duyệt giải pháp/kiến trúc, Agent BẮT BUỘC thực thi code hóa ngay trong tool call kế tiếp xuống đĩa (`replace_file_content` / `write_to_file`). Cấm nói suông rồi trôi mất.
  + **Quên là phải hỏi lại (Ask-When-Amnesic)**: Sau nén ngữ cảnh (compaction/truncation), nếu thiếu dữ kiện hoặc nghi ngờ trạng thái, BẮT BUỘC dừng lại hỏi User, cấm đoán mò nói bừa.
- **R125 (Single Pipeline Version & Zero-Ghost Remnant Mandate)**:
  + Khi cập nhật luồng mới: (1) BẮT BUỘC chạy test luồng mới (kiểm thử hợp đồng, neighbor-testing) đạt PASS; (2) BẮT BUỘC đổi trỏ toàn bộ caller sang luồng mới (`orchestrator.run_pipeline`); dọn sạch tàn dư, logic cũ, shadow code. Cấm để lại `.bak*`, `.backup*`, file dead scripts; (3) Single Truth: CẤM tồn tại song song 2 version trong cùng pipeline gây sai cấu trúc, trùng lặp hoặc bypass ngầm; (4) Zero-Ambiguity: CẤM để tồn tại docstring, comment cũ mâu thuẫn với code thực tế. Đồng bộ hóa 100% tài liệu nội hàm trong cùng commit.
  + **Automated 4-Layer Ghost Hunter Gate (VETO Authority)**: BẮT BUỘC chạy `scripts/orchestrator/ghost_code_detector.py` quét toàn bộ đĩa cứng vật lý (cả VPS và Local, bỏ qua blindness của .gitignore). Bất kỳ phát hiện nào về `.bak*`, orphan scripts, dead imports, hoặc bypass shadow code sẽ lập tức kích hoạt quyền VETO, trả exit code 1 và dừng toàn bộ CI/CD, runner, smoketest.
- **R128 (Anti-Semantic-Bias & Generic Contract Architecture Mandate)**:
  + **Cấm Hardcode Bias Đề Tài Trong Tài Liệu & Khế Ước**: CẤM TUYỆT ĐỐI đưa dữ liệu/tên tập/nhân vật cụ thể của một Episode vào khế ước (`PIPELINE_CONTRACTS.md`), system rules, prompt templates.
  + **Chuẩn Hóa Generic Contract Pattern**: Mọi schema bắt buộc dùng Generic Placeholders kèm type annotations (`"<MARKET>_EP<0000>_<topic_slug>"`, regex `^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$`, `"<FLOAT: 0.0 - 100.0>"`). Áp dụng phổ quát cho mọi thị trường (`EN`, `VN`, `JA`, `KO`...).
  + **Tách Biệt Schema và Example**: Ví dụ minh họa bắt buộc đặt trong block `[!NOTE]` riêng với cảnh báo cấm tái sử dụng giá trị cụ thể.
- **R132 (Strict Decoupled Engine & Pure Transmission Pipe Mandate)**:
  + **Code Là Ống Dẫn Thuần Túy (Pure Transmission Engine)**: Mã nguồn Python (`app/services/*`, `scripts/*`, `stages/*`) CHỈ chứa logic hạ tầng kỹ thuật: gọi API, trích xuất dữ liệu, định dạng JSON/Markdown, kiểm tra schema, render video. CẤM TUYỆT ĐỐI nhúng text prompt nghiệp vụ, văn phong kể chuyện, triết lý docudrama vào biến chuỗi trong code `.py`.
  + **Notion & Config Là Nguồn Tri Thức Duy Nhất**: Toàn bộ Prompt templates, nguyên lý 5 Beat, cấu trúc Hook, bài học S11 lưu trữ tại Notion SoT và nạp động qua `skill_loader.py` (caching 3600s, offline fallback `config/prompts/*.md`). Cổng CI Linter tự động chặn commit nếu phát hiện prompt văn phong bị hardcode vào Python.
- **R138 (Code-Graph Pre-Impact Check & Anti-Blind Editing Mandate)**:
  + **Cấm Tuyệt Đối Sửa Code Mù (No Blind Edits)**: Khi can thiệp vào các module cốt lõi, schema chung, hoặc hàm dùng chung (Shared Utilities): Agent BẮT BUỘC phải tra cứu Blast Radius thông qua GitNexus (`impact`) hoặc Antigravity CodeFlow TRƯỚC KHI chỉnh sửa file.
  + **Ngưỡng Cảnh Báo Rủi Ro**: Nếu một hàm/file có > 5 callers phụ thuộc hoặc Blast Radius > 20%: BẮT BUỘC thiết lập kế hoạch bảo toàn tương thích ngược (Backward Compatibility) hoặc refactor đồng bộ toàn bộ callers trong cùng một commit nguyên tử. Đồng bộ lại đồ thị mã nguồn sau khi thay đổi cấu trúc AST/module.
- **R139 (Disciplined Code-ification & Zero-Symptom Patching Mandate)**:
  + **Chuẩn Hóa "Vibe-to-Code" Thành Kỹ Thuật Có Kỷ Luật**: Mọi ý tưởng dạng tự nhiên khi chuyển thành mã nguồn bắt buộc phải có type annotations, docstring chuẩn hóa, xử lý boundary edge cases và kiểm thử biên. CẤM code theo cảm tính mà không gắn với khế ước.
  + **Cấm Sửa Triệu Chứng Bằng Try-Except Rỗng**: Khi gặp bug, CẤM TUYỆT ĐỐI bọc `try: ... except: pass` để che giấu lỗi runtime. BẮT BUỘC áp dụng quy trình 4 pha (Isolate -> Graph Trace -> Root-Cause Fix -> Anti-Regression Verify), truy vết đúng call chain để giải quyết tận gốc nguyên nhân.
  + **Chốt Chặn Kiểm Toán OCR Bắt Buộc**: Mọi đoạn code mới hoặc bản vá bug bắt buộc phải đạt `VERDICT: PASS (0 Critical / 0 High)` từ cổng kiểm toán tất định Alibaba Open Code Review trước khi đóng task.

### 3. Cụm C: Đồng Bộ 3 Chiều Vật Lý & Nhất Quán Hệ Thống (R126, R134)
- **R126 (Three-Way Physical Sync & Zero-False-Success Mandate)**:
  + **Bảo chứng đồng bộ vật lý (VPS ⇄ GitHub ⇄ Local/Notion bit-for-bit)**:
    - CẤM TUYỆT ĐỐI chỉ sửa code ở local Windows rồi báo "Đã đồng bộ xong VPS". Mọi thay đổi bắt buộc ghi xuống đĩa cứng VPS (`/root/video_factory`), biên dịch `python3 -m py_compile` đạt exit code `0`, và in diff/log thực tế.
    - **MCP Recovery**: Nếu MCP `vf-factory` bị timeout/ngắt socket, BẮT BUỘC fallback sang runner chuẩn `scripts/vps_runner.py` (Fresh-Session Auto-Init + Cloudflare Token). Nếu vẫn mất kết nối -> DỪNG LẠI HỎI USER NGAY (Rule 118).
    - **Commit & Push từ VPS**: Thực thi `git -C /root/video_factory add <files> && git -C /root/video_factory commit -m "<msg>" && git -C /root/video_factory push origin main` lên repo GitHub. Bắt buộc đối soát `git status` trả về `working tree clean`.
    - **Cổng Bảo Chứng GitHub Actions CI Bắt Buộc**: Bắt buộc chạy `python scripts/watch_github_ci.py --commit <HEAD_SHA>` (hoặc `runner.py --mode sync`) theo dõi GitHub Actions Workflow Run cho đến khi `conclusion: success` (exit code 0). CẤM BÁO CÁO HOÀN TẤT KHI CI CHƯA PASS. Nếu CI fail, tải log lỗi về, tự fix và push lại.
    - **Đồng bộ ngược Local & Notion**: Cập nhật file tương ứng vào local Windows Workspace và Notion SoT, đối soát SHA256 đạt 100% bit-for-bit parity.
- **R134 (Exact Parity, Full-Text Consistency & Adversarial Boundary Verification Gate)**:
  + **Cấm Nghiệm Thu Cục Bộ Bằng Smoke Test Đơn Thuần**: Smoke test chỉ chứng minh luồng chính không sập, không chứng minh hằng số cấu hình và tham số nghiệp vụ đã khớp 100%.
  + **Bắt Buộc Quét Nhất Quán Văn Bản Toàn Diện (Full-Text Consistency Sweep)**: Khi thay đổi bất kỳ hằng số cấu hình, ngưỡng điểm (`viability_score >= 8.0`), danh mục (7 Canonical Pillars), hoặc schema: BẮT BUỘC chạy tìm kiếm toàn diện (`grep_search`/`grep -rn`) trên toàn bộ codebase VPS và Workspace. CẤM để xảy ra lệch pha giá trị giữa các file.
  + **Kiểm Thử Đối Kháng Nghiệp Vụ Biên Trong CI**: Mọi bài test CI (`tests/ci_neighbor_tester.py`) BẮT BUỘC chứa các câu lệnh `assert` cụ thể kiểm tra sự đồng nhất giá trị hằng số, threshold, chuỗi cảnh báo và boundary context. Chốt chặn kiểm toán pháp y độc lặp trong `/vf-pipeline-teamwork` bắt buộc quét đối kháng vi sai (Differential Audit Checklist), đạt 100% CLEAR mới bàn giao cho Three-Way Sync Coordinator.

### 4. Cụm D: Chuẩn Mực Đạo Diễn Vox Engine v3 & Visual Audit (R120, R122, R130, R131, R133, R135, R136, R140, R141, R142, R143)
- **R120 & R135 (Ground-Truth Video Timeline Chapter Synchronization Mandate)**:
  + **Remotion Rendered Timeline Là Chân Lý Duy Nhất Cho YouTube Chapters**: Mốc thời gian chương hồi (`00:00`, `MM:SS`) trên YouTube Description BẮT BUỘC trích xuất từ `remotion_props.json` (tích lũy `durationInFrames / fps` của các Scene thực tế đã đồng bộ Whisper word-level timestamps). CẤM tính mốc chapter từ độ dài lý thuyết, tỷ lệ % ước lượng thô, hay tổng thời lượng audio thô rời rạc. Karaoke millisecond sync đạt độ trôi lệch 0ms drift.
  + **Tự Động Hóa Đồng Bộ Tại S10/S11 Upload**: Pipeline BẮT BUỘC gọi hàm chuẩn hóa `sync_exact_chapters_from_remotion()`. Mốc bắt đầu luôn là `00:00`, tối thiểu 3 chapter, mỗi chapter cách nhau ít nhất 10 giây, tăng dần theo thời gian.
- **R122 (Pixel-Level Visual Audit Gate & Zero-Mock Score)**:
  + Nghiệm thu ảnh S7 BẮT BUỘC trích xuất frame/file ảnh thật và mở bằng `view_file` theo tiêu chuẩn 4 Trục:
    1. *UI & Artifact*: 0% dính thanh công cụ trình duyệt, nút bấm, watermark.
    2. *Alpha & Edge Integrity*: 0% thủng lỗ trên chi tiết tài liệu/đạo cụ; viền cắt giấy sắc cạnh, không lem màu nền.
    3. *Style Conformance*: 100% đồ họa minh họa Stylized Graphic Novel Editorial Illustration nét comic mực, kết hợp giấy báo cũ ngả vàng `#F4F1EA`. CẤM ảnh chụp thật photorealistic hoặc 3D CGI bóng bẩy.
    4. *Era, Market & Ethnic Context*: Chữ viết trên tài liệu, con dấu, bản đồ phản ánh đúng địa lý/văn hóa thị trường (JP, KR, VN, US). CẤM chữ tiếng Anh/Latin trên biển hiệu, tường, tài liệu ở thị trường bản địa (JP, KR, VN). Ánh sáng, góc chiếu đổ bóng hòa hợp tuyệt đối với không gian bàn tài liệu.
  + CẤM TUYỆT ĐỐI giả mạo điểm số (như hardcode 9.8). Điểm số phải từ phân tích thị giác thật.
- **R130 (Factual Causal Integrity & Search-Intent Payoff Mandate)**:
  + **Cấm Bịa Đặt Mối Quan Hệ Nhân Quả & Twist Tiện Lợi**: Chuỗi nhân quả bắt buộc phân định 2 cấp: *Level 1 (Primary Catalyst)*: Sự kiện/ngòi nổ thực tế khách quan có mốc thời gian và chủ thể rõ ràng; *Level 2 (Transmission Mechanism)*: Phản ứng dây chuyền của cấu trúc hệ thống, thể chế hoặc thị trường. CẤM đánh tráo Level 2 thành Level 1.
  + **Factual High-Stakes Hook (0-60s, Rule 444)**: (1) Catalyst Event; (2) Quantitative Metric từ Grounding Table; (3) Core Systemic Paradox.
  + **Search-Intent Payoff & Anti-Bait-and-Switch**: Act I & II bắt buộc đối diện và giải mã trực tiếp từ khóa nóng mà người xem tìm kiếm. CẤM mượn từ khóa làm mồi nhử rồi thoái thác sang bài giảng lý thuyết chung chung. Áp dụng generic cho 7 Trục Đề Tài Vàng & 3 Epochs (`<CATALYST_EVENT> -> <TRANSMISSION_MECHANISM> -> <CORE_SYSTEMIC_PARADOX> -> <DIRECT_SEARCH_PAYOFF>`), phân loại nhịp thời gian (`MACRO_SAGA`, `MID_TACTICAL`, `FLASH_CRISIS`) và trích xuất bảng `causal_epochs`.
- **R131 (10X Beat Architecture & Editorial Signal Purity Mandate)**:
  + **Khử Nhiễu & Tách Biệt Prompt Nghiệp Vụ**: CẤM đưa tài liệu content marketing, social copy chung chung vào prompt kịch bản S3. S3 chỉ nhận nguyên lý điều tra, pacing docudrama và bài học S11.
  + **Cấu Trúc 5 Beat Docudrama**: Tuân thủ nghiêm ngặt 5 Beat (Beat 1 Cold Strike 0-20s -> Paradox 20-60s -> Ticking clock; Beat 2 False Narrative & Red Herring; Beat 3 Forensic Paper Trail & Pattern Interrupt 2-6 từ; Beat 4 Smoking Gun & Climax; Beat 5 Modern Mirror & Living Warning). Quản trị tập trung tại `config/prompts/b2_editorial_prompt.md` và Notion SoT.
  + **Cấm Mở Đầu Bằng Câu Hỏi Giả Định ("Imagine...")**: Bắt buộc mở đầu trực diện bằng sự kiện ngòi nổ thực tế và con số lượng hóa từ Grounding Table trong 60 từ đầu. Thể hiện áp lực thể chế qua con người bị mắc kẹt thực tế.
- **R133 (Notion AI Skill Delegation vs. Antigravity Operational Scope Mandate)**:
  + **Skill AI Notion Quản Trị Nghiệp Vụ Prompt & Kịch Bản/Đạo Diễn**: Mọi quy chuẩn nghiệp vụ Prompt Engineering, cấu trúc kịch bản (Rule 130, 131, 444), mỹ thuật S5/S7, bài học S11 BẮT BUỘC lưu trữ trên Notion SoT (`Skill AI` page `ac901989-2400-827e-bda2-8175dabdcf13`, `Content Engine Hub`, `Media Production Hub`) và `config/prompts/*.md`.
  + **AGENTS.md Chỉ Chứa Kỷ Luật Vận Hành Trực Tiếp Của Antigravity**: `AGENTS.md` CHỈ ghi nhận các Kỷ luật thép chi phối hành vi trực tiếp của Agent (Rule 118, 119, 121, 124, 126, 127, 134...). CẤM TUYỆT ĐỐI đưa toàn văn nội dung prompt kể chuyện, hướng dẫn viết văn, hay chi tiết nghệ thuật tạo hình vào `AGENTS.md` gây lãng phí token nạp mỗi phiên chat và làm loãng khả năng tuân thủ kỷ luật thực thi.
- **R136 (Zero-Asset-Leak & Pure Beat Header Mandate)**:
  + **Cấm Tuyệt Đối Rò Rỉ Mã Asset / Layer / Hash Lên Video**: Thẻ speaker tag / lower-third banner phụ đề trên video Remotion CẤM TUYỆT ĐỐI việc đọc hoặc fallback sang `foreground_reuse_key`, `background_reuse_key`, tên layer, đuôi file (`.png`), hay mã hash nội bộ. CẤM hardcode tiền tố nội bộ mang tính shadow code (như `"ARCHIVE X // "`) trong renderer component `index.tsx`.
  + **Chuẩn Hóa Thẻ Định Danh Phân Cảnh Phổ Quát**: Thẻ phụ đề chỉ được phép hiển thị 2 trường hợp: (1) Nhân vật đối thoại/phát biểu: `TÊN // VAI TRÒ`; (2) Thẻ nhịp Beat định danh: `BEAT <X>: <TIÊU ĐỀ BEAT>`. Áp dụng generic phổ quát cho mọi thị trường (EN, JP, KR, VN...).
- **R140 (Object-to-Object Kinetic Coupling & Narrative Sub-Director Mandate - Vox Engine v3)**:
  + **Cấm Khái Niệm Trừu Tượng & Slideshow Vô Hồn Vào Prompt**: CẤM TUYỆT ĐỐI viết prompt cho tầng sinh ảnh và video bằng câu chuyện trừu tượng hoặc liệt kê các object xuất hiện rời rạc độc lập (Layer 1 rơi, Layer 2 trượt vào, camera đứng yên) gây cảm giác slideshow vô hồn.
  + **Phân Loại 7 Họ Tương Tác Nhân Quả Xúc Giác ($H_1 
ightarrow H_7$)**: Mọi ý niệm kịch bản bắt buộc chuyển thể thành tương tác cơ học vật lý có điểm chạm (Contact Dynamics) và để lại tồn dư (Residue) trên mặt bàn giấy báo cũ (#F4F1EA):
    * $H_1$ (Impact / Percussion): Con dấu mộc đỏ / khối chì dập mạnh -> giấy lún, mực loang, tài liệu nảy 1-2 frame, camera giật nhẹ.
    * $H_2$ (Constraint / Clamp): Thước cặp caliper / compa / kẹp giấy kẹp siết mục tiêu -> mép giấy nhăn, vạch vernier giật quá đà rồi khóa số đo.
    * $H_3$ (Sever / Cut / Tear): Kéo kim loại / dao trổ cắt xé -> mảnh giấy nhỏ tách rời rơi xoay có độ nảy, để lộ lớp chứng cứ tầng dưới.
    * $H_4$ (Tether / Tension): Ghim đồng cắm phập, sợi chỉ đỏ (red evidence yarn) kéo căng -> hai đối tượng bị kéo nghiêng về nhau, chỉ rung dao động tắt dần.
    * $H_5$ (Optical / Refraction): Kính lúp trượt qua -> vùng chữ bên dưới phóng to $1.4	imes$, méo cong rìa (barrel distortion), lộ chữ in nhỏ li ti.
    * $H_6$ (Mark / Ink Transfer): Bút dạ quang neon quét -> thớ giấy thấm mực và bừng sáng phát quang neon, kích hoạt xung sáng chạy dọc đường dẫn.
    * $H_7$ (Displace / Unfold): Lực xô đẩy ma sát -> chồng ảnh xòe quạt, bản đồ bung mở nếp gấp (pop-up unfold).
  + **Khung Scene Sub-Director Plan Nở Từ 4 Thì Gốc Ra 4..7 Micro-Beats Linh Hoạt**:
    * 4 Thì Gốc: $P_1$: Setup -> $P_2$: Mechanical Tension -> $P_3$: Causal Escalation -> $P_4$: Living Hold 12fps. Nở câu đơn giản: 4 - 5 beats; câu phức hợp (2-3 vế, từ nối "nhưng", "tuy nhiên", con số): 6 - 7 beats.
    * **Luật Chuyển Giao Nhân Quả (Causal Handoff Law)**: Target hoặc Tồn dư của Beat $n$ BẮT BUỘC phải là Source hoặc Target của Beat $n+1$. Chuỗi chuyển động là một dây xích khép kín.
  + **Tốc Độ Stop-Motion Bứt Tốc (Snappy Stop-Motion Physics $\le 0.4s$ & Anti-Slowdown Invariant)**: Cử động xuất hiện, va chạm, dập dấu, kéo thước, cắt xé BẮT BUỘC bứt tốc dứt khoát trong $0.2s - 0.4s$ ($6 - 12	ext{ frames}$ ở 30fps) với gia tốc nhảy cóc (step motion curve). Khóa Cứng Bất Động (Dead-Stop Hold): Ngay sau va chạm, vật thể BẮT BUỘC đứng im bất động 100% tại chỗ cho đến hết thì hoặc cut chuyển cảnh, CHỈ duy trì vi rung bóng đổ/thớ giấy $\le 2	ext{px}$ ở 12fps ("on twos"). CẤM TUYỆT ĐỐI kéo dãn chuyển động chậm chạp dàn trải đều qua suốt 5–8s (Anti-Slowdown).
  + **Đồng Bộ Tuyệt Đối Với Whisper Word Timestamps ($0	ext{ms}$ Drift Invariant)**: Mốc thời gian của từng Micro-Beat và Layer Remotion BẮT BUỘC neo cứng vào từ phát âm thực tế trong Voiceover (`whisper_word_timestamps`). CẤM nén, giãn, scale hoặc clamp giả tạo làm sai lệch phụ đề, âm thanh và chuyển động thị giác. Độ trôi lệch (drift) tối đa cho phép là $0	ext{ms}$.
  + **Cú Pháp Động Từ Liên Hợp Nhân Quả Trong Prompt I2V (Causal Compound Verb Syntax)**: BẮT BUỘC dùng cú pháp: `[SOURCE] + [contact_verb] + [TARGET], causing [TARGET] to [physical_reaction], leaving [residue].` Tuyệt đối không liệt kê rời rạc. Duy trì vi rung stop-motion 12fps (on twos) và nhịp thở bóng đổ $\le 2	ext{px}$ đến tận cut chuyển cảnh. CẤM ĐÓNG BĂNG KHUNG HÌNH (freeze frame).
  + **Kỷ Luật Triển Khai Toàn Diện Trên Luồng Gốc (Root Pipeline Deployment Mandate)**: Phân rã động học $H_1 
ightarrow H_7$, 4..7 micro-beats và cú pháp prompt liên hợp BẮT BUỘC nạp và thực thi trực tiếp trên:
    * `stages/s05_director_plan.py`
    * `app/services/unified_vox_director.py`
    * `app/services/director_planner_b3.py`
    * `app/services/vox_automated_director.py`
    * `scripts/generate_vox_b3_director.py`
    Mọi output Scene ở tầng Đạo Diễn luồng chính BẮT BUỘC chứa `scene_sub_director_plan` (schema v3) và `universal_video_prompt`. CẤM TUYỆT ĐỐI bypass hoặc sinh kịch bản thô thiếu kế hoạch phân rã cơ học xúc giác.
- **R141 (Mandatory Concrete Visual Audit Table & Clickable Forensic Evidence Gate)**:
  + **Cấm Báo Cáo Suông (Zero-Vague-Reporting Mandate)**: Khi báo cáo kết quả sinh ảnh S7, thẩm định thị giác hoặc qua cổng Human Gate: CẤM TUYỆT ĐỐI chỉ thông báo số lượng chung chung.
  + **Bắt Buộc Bảng Thẩm Định Thực Chứng Kèm Link Click Mở Xem Ảnh Trực Tiếp (Clickable Evidence Table)**: Báo cáo S7 bắt buộc trình bày Forensic Visual Report Table trích xuất tối thiểu 4–6 Scene đại diện kèm 5 trường:
    1. *Scene ID & Stage* (ví dụ: `SCENE_01` · `S07_IMAGE`).
    2. *Clickable File Link*: Markdown link chuẩn file:// (`[composite_SCENE_XX.png](file:///...)`) mở xem ảnh thật full resolution.
    3. *Vật Thể Xúc Giác & Đạo Cụ (Rule 140 Objects)*: Hồ sơ gấp mép, triện đỏ Hanko, thước cặp caliper, kéo kim loại, USB khóa cứng, cọc tiền giấy...
    4. *Phân Rã Động Học 4 Thì ($S_1 
ightarrow S_4$)*: Entry/Drop -> Impact/Stamp -> Vector/Growth -> Hold $\le 2	ext{px}$.
    5. *Điểm Thẩm Định Visual Audit*: Phân giải 2560x1440, HSV clean, black frame %, text-free %, Điểm visual audit (e.g., 9.8/10), trạng thái APPROVED.
  + **Bảo Chứng Thư Viện HTML**: Bắt buộc đính kèm link mở trực tiếp file `review_gallery.html` (`[review_gallery.html](file:///...)`).
- **R142 (Anti-Generic-AI-Visual & Forensic Journalistic Decomposition Mandate)**:
  + **Cấm Hình Tượng AI Mockup Vô Hồn (Zero-Generic-AI Mandate)**: CẤM TUYỆT ĐỐI tầng đạo diễn S5 và prompt sinh ra hình tượng AI sáo rỗng vô hồn: thanh tìm kiếm mockup trắng trơn, thẻ đánh số rỗng `01`/`02`, bàn họp stock photo, biểu đồ mũi tên bay lơ lửng, phòng 3D CGI bóng bẩy.
  + **Quy Chuẩn Chuyển Thể Pháp Y Báo Chí Điều Tra Vox (Forensic Evidence Dossier Desk)**: Mọi ý niệm kịch bản bắt buộc chuyển thể dưới lăng kính Bàn Giám Định Chứng Cứ Pháp Y Của Cơ Quan Điều Tra đặt trên nền giấy báo cũ ngả vàng `#F4F1EA`: Tấn công mạng/Phishing (văn bản Keigo dán nhãn Trojan, ổ cứng kim loại khóa đồng, sao kê bôi đen redacted ledger, tin nhắn tống tiền Dark Web kèm thẻ đếm ngược); Xu hướng bùng nổ (console an ninh JPCERT, vệt bút dạ quang neon, thẻ xu hướng đỏ, văn bản khuyến cáo mộc đỏ); Xúc tác thể chế/Nhân vật (hồ sơ rò rỉ đài truyền hình, ảnh halftone đen trắng, con dấu mộc đỏ, triện cá nhân Hanko gạch chéo vô hiệu). Chi tiết minh họa quản trị tập trung tại Notion SoT và `config/prompts/vox_b3_*.md`.
- **R143 (Mandatory Clickable Video Demo Audit Table & Anti-Duplicate Dispatch Gate)**:
  + **Cấm Báo Cáo Video Bằng Miệng (Zero-Verbal-Video-Reporting Mandate)**: Sau khi hoàn thành sinh video demo hoặc full luồng: BẮT BUỘC xuất bảng nghiệm thu pháp y trực quan gồm: Scene ID, Clickable Video Link file:// (`[clip_scene_XX.mp4](file:///...)`), Clickable Mid-frame Preview (`[clip_scene_XX_mid.png](file:///...)`), Đạo cụ xúc giác thực tế, Động học 4 thì I2V, Thời lượng thực tế (s), Dung lượng file (KB), và Điểm thẩm định thị giác.
  + **Chốt Chặn Chống Trùng Lặp Video (Anti-Duplicate Dispatch Gate)**: Bắt buộc kiểm tra hash SHA-256 và visual fingerprint giữa các Shot clips. Nếu 2 clip có kích thước giống nhau hoặc visual frame trùng khớp -> VETO lập tức, cấm báo cáo PASS và tự động chạy lại Scene bị thiếu.
  + **Bảo Chứng Thư Viện Video Tương Tác**: Bắt buộc tạo và đính kèm link mở trực tiếp file `demo_video_gallery.html` (`[demo_video_gallery.html](file:///...)`) có trình phát video HTML5.

---

## ⚡ III. HỆ THỐNG ĐIỀU PHỐI 1-LỆNH THỐNG NHẤT (`/vf-pipeline-teamwork`)

Toàn bộ các tác vụ vận hành, lập kế hoạch, kiểm thử và deploy quy về một **Master Orchestrator Engine** duy nhất (`python -m orchestrator.run_pipeline`):

### 1. Bảng Định Tuyến 11 Giai Đoạn Canonical (S1–S11)
| Giai Đoạn Canonical | Stage ID | Lệnh Điều Phối `/vf-pipeline-teamwork` | CLI Lõi (`orchestrator.run_pipeline`) | Đầu Ra Chuẩn (StageArtifact) | Chốt Chặn Kiểm Tra (Gate) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **S1: Ideation** | `s01_ideation` | `/vf-pipeline-teamwork s1` | `python -m orchestrator.run_pipeline --only s01_ideation` | `{ topic, raw_term, viability_score, market, angle_brief }` | Score >= 8.0, cấm synthetic/mock (R118) |
| **S2: Research** | `s02_research` | `/vf-pipeline-teamwork s2` | `python -m orchestrator.run_pipeline --only s02_research` | `{ factsheet, grounding_sources, key_entities, competitor_gaps }` | Ít nhất 1 nguồn Ground Truth (R130) |
| **S3: Script** | `s03_script` | `/vf-pipeline-teamwork s3` | `python -m orchestrator.run_pipeline --only s03_script` | `{ beats: [5 Beat Docudrama], scenes: [Scene(scene_id, narration, duration)] }` | Đúng 5 Beat, cấm mở đầu "Imagine" (R131) |
| **S4: Critic Script** | `s04_critic_script` | `/vf-pipeline-teamwork s4` | `python -m orchestrator.run_pipeline --only s04_critic_script` | `CouncilDecision { verdict, aggregate_score, verdicts }` | Điểm >= 8.5/10.0 từ Astra 6 + Opus 5.5 |
| **S5: Director Plan** | `s05_director_plan` | `/vf-pipeline-teamwork s5` | `python -m orchestrator.run_pipeline --only s05_director_plan` | `{ scenes: [Scene(headline, visual_metaphor, color_accent, shots)] }` | Headline 1-4 từ, tactile paper cutout (R140) |
| **S6: Critic Visual** | `s06_critic_visual` | `/vf-pipeline-teamwork s6` | `python -m orchestrator.run_pipeline --only s06_critic_visual` | `CouncilDecision { verdict, aggregate_score }` | Điểm >= 8.5/10.0 về bố cục và màu sắc |
| **S7: Image Gen** | `s07_image_gen` | `/vf-pipeline-teamwork s7` | `python -m orchestrator.run_pipeline --only s07_image_gen` | `{ images: [seed_image_path] }` lưu tại `composite_seeds/` | Rule 122 Visual Audit (sạch chữ, nét comic) |
| **S8: Video Gen** | `s08_video_gen` | `/vf-pipeline-teamwork s8` | `python -m orchestrator.run_pipeline --only s08_video_gen` | `{ clips: [VideoAsset(shot_id, file_path, sha256)] }` | MP4 size > 100KB, xoay vòng 7 acc Google Flow |
| **S9: Voice TTS** | `s09_voice_tts` | `/vf-pipeline-teamwork s9` | `python -m orchestrator.run_pipeline --only s09_voice_tts` | `{ audio_file, subtitles: [KaraokeWord(word, start, end)] }` | R120 (Karaoke millisecond sync), R135 Whisper |
| **S10: Remotion** | `s10_render` | `/vf-pipeline-teamwork s10` | `python -m orchestrator.run_pipeline --only s10_render` | `final.mp4` trong `10_render/` | ffprobe xác nhận đủ video + audio stream (R135) |
| **S11: QC Final** | `s11_qc` | `/vf-pipeline-teamwork s11` | `python -m orchestrator.run_pipeline --only s11_qc` | `{ qc_verdict: "PASS", duration_sec, resolution }` | Video đạt chuẩn 1080p/4K, Feedback Dreaming |

### 2. Bảng Lệnh Vận Hành Toàn Luồng (CI/CD, Deploy & Governance)
| Lệnh Chat Thống Nhất | Lệnh CLI Tương Đương (`scripts/orchestrator/runner.py`) | Nghiệp Vụ & Kỹ Năng Nạp Vào (JIT) | Quy Chuẩn Ràng Buộc |
| :--- | :--- | :--- | :--- |
| `/vf-pipeline-teamwork prod` | `python -m orchestrator.run_pipeline --profile prod` | Sản xuất trọn gói 11 stages với profile chuẩn production | R118, R121, R125, R126, R140 |
| `/vf-pipeline-teamwork e2e` | `python -m orchestrator.run_pipeline --profile e2e_min` | Kiểm thử khép vòng tối thiểu (1 Scene, 1 Shot 5s, 1 account) | Low-Quota E2E Gate, Fail-Fast |
| `/vf-pipeline-teamwork resume` | `python -m orchestrator.run_pipeline --run-id <ID> --from <STAGE>` | Phục hồi và chạy tiếp từ stage gặp lỗi sau sự cố | Crash Resumption, `run_manifest.json` |
| `/vf-pipeline-teamwork plan` | `python3 scripts/orchestrator/runner.py --mode plan --task-id <EP_ID>` | Phase 0 Strategic Planner (`gpt-6.1-sol` / fallback `claude-sonnet-5`), Grill-Me | R124, R128, R129, 4 Trụ Cột Kế Hoạch |
| `/vf-pipeline-teamwork supervise` | `python3 scripts/orchestrator/runner.py --mode supervise --task-id <EP_ID>` | Supreme Architecture Supervisor (`claude-opus-5-5` Supreme Lock 1-Shot) | Cap <= 10000 in / <= 5000 out, Prompt Cache |
| `/clean-code` | `python scripts/code_hygiene_scanner.py` | Skill `clean-code`: Quy hoạch kiến trúc 4 trụ cột (Idea Vault Snapshot, Local Live-Tree Scan, Serena AST Phẫu thuật, Shadow Sync) | 4 Trụ Cột, R125 Single Version, R138 Blast Radius, R139 |
| `/vf-pipeline-teamwork review` | `python3 scripts/orchestrator/runner.py --mode review` | Alibaba Open Code Review Engine (`.opencodereview/rule.json`), Diff Review, AST Scan | R121, R139 (0 Critical / 0 High Defect Gate) |
| `/vf-pipeline-teamwork ci` | `python3 scripts/orchestrator/runner.py --mode ci` | Chạy bộ 3 CI Quality Gates (`ci_neighbor_tester.py`, `e2e_pipeline_smoketest.py`, OCR) | R121, R125, R127, R134 |
| `/vf-pipeline-teamwork sync` | `python3 scripts/orchestrator/runner.py --mode sync` | Đồng Bộ 3 Chiều (VPS ⇄ GitHub ⇄ Local), Git Safe Backup Checkpoint, CI Watcher | R126 (Bit-for-bit Parity, CI Green) |
| `/vf-pipeline-teamwork deploy` | `python3 scripts/orchestrator/runner.py --mode deploy --auto-rollback` | Triển khai 1-lệnh full luồng (`.github/workflows/ci.yml`, Git Backup + Push + CI Watcher) | R121, R126, Auto-Rollback Guard |
| `/vf-pipeline-teamwork sweep` | `python3 scripts/orchestrator/runner.py --mode sweep` | Quét & Dọn sạch tàn dư 5 điểm chạm (Lead Detective & Doer Sanitizer Pair) | R119, R125 (Zero-Ghost, Manifest) |
| `/vf-pipeline-teamwork health` | `python3 scripts/orchestrator/runner.py --mode health` | Giám sát 7 trục (`scripts/health-check.py`: DB, Redis, RAM, Workers, Ghost Code) | R119, R125, Zero-Mock Telemetry |
| `/vf-pipeline-teamwork report` | `python3 scripts/orchestrator/runner.py --mode report` | Xuất báo cáo trạng thái hệ thống Markdown & HTML Dashboard | `system_health_reporter.py` |
| `/vf-pipeline-teamwork memory` | `python3 scripts/orchestrator/runner.py --mode memory` | Kiểm định bộ nhớ dài hạn Vibe Coding (`ROADMAP.md`, `CHANGELOG.md`, `specs/`, `.agents/hooks.json`) | R124, `memory_governor.py --strict` |
| `/vf-pipeline-teamwork security`| `python3 scripts/orchestrator/runner.py --mode security` | Kiểm toán an ninh Cloudflare/Worker (`validate_findings.py`, `CLOUDFLARE-ECOSYSTEM.md`) | Skill `security-audit`, Zero Trust JWT |

### 3. Giao Diện Makefile & PowerShell Thống Nhất (Local Windows)
- `.\make.ps1 ci` / `.\make.ps1 deploy` / `.\make.ps1 sync` / `.\make.ps1 health` / `.\make.ps1 review` / `.\make.ps1 memory` / `.\make.ps1 clean`.
- Từ xa qua VPS Runner: `python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode <mode>"`.

---

## 🎯 IV. NGUYÊN TẮC QUẢN TRỊ TÁC VỤ (TASK DISCIPLINE)

1. **Task-Level Contract**: Mọi nhiệm vụ lớn / Sprint bắt buộc neo theo file `ORIGINAL_REQUEST.md` (chứa User Request gốc, Requirements R1..Rn và Acceptance Criteria `[ ]`).
2. **Interface Contracts**: Khế ước dữ liệu JSON IN/OUT giữa các stage và danh mục file trên VPS tra cứu tại `PIPELINE_CONTRACTS.md` và `docs/PIPELINE_CANONICAL.md`.
3. **Autonomous Clarification Protocol**: Mọi tác vụ có tính đa chiều, rẽ nhánh kỹ thuật hoặc mơ hồ bắt buộc kích hoạt Cổng Phản Vấn Chủ Động (Global Rule R129), suy luận sâu và làm rõ với User trước khi triển khai sâu.
4. **Vibe Coding Memory & Specification Traceability**:
   - Mọi thay đổi kiến trúc/tính năng bắt buộc tuân theo quy trình 2 bản vẽ: `specs/business_flow_template.md` (Business Flow) và `specs/design_spec_template.md` (Design Spec).
   - Bộ nhớ dự án bắt buộc neo vào `ROADMAP.md` (tiến độ pha, task checklists `[x]`) và `CHANGELOG.md` (chuẩn Keep a Changelog: `Added`, `Changed`, `Fixed`).
   - Trước khi kết thúc phiên hoặc commit, chạy `make memory` hoặc `python scripts/orchestrator/memory_governor.py --strict` để bảo chứng không mất ngữ cảnh (Anti-Amnesia).

---

## 🏗️ V. QUY CHUẨN HARNESS SYSTEM NGUYÊN TỬ (5 SUBSYSTEMS PRIMITIVES)

> **Kế thừa tinh hoa từ WalkingLabs (Learn Harness Engineering), Codex, Claude Code & DeepSeek:**
> *"Độ tin cậy đến từ Harness, không phải từ Model. Harness xây chiếc vòng kim cô bảo đảm AI làm việc chuẩn xác, không còn hên xui."*

### 1. Phân Hệ 1: Instructions Subsystem (Directory Page & Progressive Disclosure)
- **Directory Page Invariant (Codex Standard)**: `AGENTS.md` là mục lục điều hướng và khế ước bất biến, KHÔNG PHẢI bách khoa toàn thư. Kiến thức chuyên sâu đặt trong `docs/`, `config/prompts/` hoặc Notion SoT để nạp theo nhu cầu (JIT).
- **Startup Workflow 6 Bước Bắt Buộc (Trước khi code)**:
  1. `pwd`: Xác nhận đúng thư mục làm việc (Local hoặc `/root/video_factory`).
  2. `read`: Đọc `AGENTS.md` nắm vững các Kỷ luật Thép và định tuyến.
  3. `state`: Đọc `feature_list.json` hoặc `task_manifest.json` xem trạng thái tính năng hiện tại.
  4. `verify baseline`: Chạy kiểm tra nền tảng (`./init.sh` hoặc `python scripts/orchestrator/runner.py --mode ci --baseline`) xem hệ thống có đang xanh không. Nếu baseline đỏ -> Phải fix baseline trước khi thêm tính năng mới!
  5. `git log`: Kiểm tra 5 commit gần nhất (`git log --oneline -5`) để nắm ngữ cảnh kỹ thuật.
  6. `pick one`: Chỉ chọn ĐÚNG 1 feature chưa hoàn thành để thực thi.

### 2. Phân Hệ 2: State Subsystem (Persistent Disk-Backed Source of Truth)
- **Cấm Nhớ Mồm Trong Chat**: Toàn bộ tiến độ, phân nhánh, và kết quả thực thi bắt buộc lưu xuống đĩa cứng vật lý bằng cấu trúc JSON/Markdown (`feature_list.json`, `progress.md`, `runs/<run_id>/run_manifest.json`).
- **Two-Step Save Invariant**: Mọi ghi nhận trạng thái phải ghi chi tiết vào topic file/report trước, sau đó mới cập nhật pointer vào index/manifest. Nếu phiên chat bị ngắt đột ngột, trạng thái vẫn toàn vẹn và có thể khôi phục 100% trong phiên sau.
- **Model-Visible Means Logged (DeepSeek Invariant)**: Bất kỳ prompt, ngữ cảnh, hoặc output quan trọng nào model đọc/ghi đều phải được log vào session history (`logs/*.jsonl`) để có thể tái hiện lại quá trình suy luận.

### 3. Phân Hệ 3: Verification Subsystem (Fail-Fast & Anti-Premature Victory Gate)
- **Chống Tuyên Bố Chiến Thắng Sớm (Lecture 9 Law)**: CẤM TUYỆT ĐỐI agent tự đánh giá công việc của mình bằng lời nói chủ quan ("tôi nghĩ là ổn rồi", "chắc chắn đã xong").
- **Evidence-Based Completion (Definition of Done - DoD 4 Tiêu Chí)**:
  1. Đã triển khai xong đúng hành vi mục tiêu (Behavior Implemented).
  2. Đã chạy lệnh kiểm thử thực tế với chế độ Fail-Fast (`set -e` hoặc exit code `0`).
  3. In và ghi nhận bằng chứng pháp y (`evidence`: stdout, diff lines, HTTP 200, test passes) vào `feature_list.json` hoặc báo cáo nghiệm thu.
  4. Hệ thống vẫn khởi động lại sạch sẽ được (Restartable Clean State).

### 4. Phân Hệ 4: Scope Subsystem (One-Feature-At-A-Time & Blast Radius Control)
- **Nguyên Tắc 1 Tính Năng Mỗi Lần (One-Feature-At-A-Time)**: Mỗi phiên làm việc chỉ tập trung vào 1 feature/stage duy nhất. Cấm ôm đồm sửa lan man nhiều file không liên quan.
- **Dependency DAG**: Tuân thủ nghiêm ngặt quan hệ phụ thuộc (`dependencies: [...]`). Không triển khai tính năng khi các tính năng tiền đề chưa hoàn thành và chưa có verification evidence.
- **Blast Radius Enforcer**: Tuyệt đối không can thiệp vào các module ngoài phạm vi của task hiện tại trừ khi có sự phê duyệt rõ ràng từ User.

### 5. Phân Hệ 5: Session Lifecycle & Handoff Subsystem (Clean State & Cross-Session Continuity)
- **Quy Trình Kết Thúc Phiên (End-of-Session Routine)**:
  1. Cập nhật `progress.md` (What's Done, What's In Progress, What's Next, Blockers/Risks).
  2. Cập nhật `feature_list.json` với trạng thái mới (`completed`, `in-progress`) kèm `evidence`.
  3. Tạo commit Git mô tả chuẩn Conventional Commits.
  4. Thực hiện Two-Phase Eviction: Dọn sạch file scratch/tạm tại `/tmp/`, thu hồi zombie processes qua `resource_recycler.py`.
  5. Đảm bảo phiên tiếp theo (hoặc Agent khác) có thể khởi chạy ngay lập tức mà không cần hỏi lại từ đầu.
