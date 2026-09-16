---
name: vf-pipeline-teamwork
description: >-
  Quy trình điều phối đội ngũ Multi-Agent 4 vai chuyên biệt cho AI Video Factory (VF Pipeline Hardening & Execution).
  Tích hợp động cơ Alibaba Open Code Review (OCR Engine) kiểm toán mã nguồn xác định ở mức line-level diff.
  Kích hoạt khi nhận các lệnh /vf-pipeline-teamwork, /teamwork:pipeline, /run:teamwork, /vf:teamwork, hoặc khi user yêu cầu kiểm thử,
  debug song song, review code, thẩm định độc lập, chạy toàn trình CI/CD quality gates và đồng bộ 3 chiều cho các bước B1 đến B11.
---

# 🛡️ VF Pipeline Multi-Agent Teamwork Skill (`/vf-pipeline-teamwork`)

> **Phiên bản Hợp Nhất Toàn Diện (All-in-One Multi-Agent CI/CD Engine)** dành riêng cho dây chuyền sản xuất video tự động **AI Video Factory (VF Pipeline)**.
> Tích hợp sâu động cơ **Alibaba Open Code Review (OCR Engine)**, chuẩn hóa cấu trúc điều phối đội ngũ 4 vai độc lập, tích hợp chặt chẽ với CLI Runner `scripts/orchestrator/runner.py`, tuân thủ nghiêm ngặt **Kỷ Luật Thép Rule 118 – Rule 134** và bảo chứng đồng bộ 3 chiều (VPS ⇄ GitHub ⇄ Local bit-for-bit).

---

## 🎯 I. CƠ CHẾ VẬN HÀNH & 4 VAI TRÒ ĐỘC LẬP (4 AUTONOMOUS ROLES)

Khi nhận lệnh `/vf-pipeline-teamwork` (hoặc `/teamwork:pipeline`), Agent đóng vai trò **Điều Phối Viên (Orchestrator)** sẽ tự động kích hoạt hoặc mô phỏng đội ngũ 4 vai chuyên biệt:

```
                      ┌─────────────────────────────────────────────────────────┐
                      │        VF TEAMWORK MASTER ORCHESTRATOR                  │
                      │         (scripts/orchestrator/runner.py)                │
                      └────────────────────────────┬────────────────────────────┘
                                                   │
         ┌─────────────────────┬───────────────────┴───────────────────┬─────────────────────┐
         ▼                     ▼                                       ▼                     ▼
┌──────────────────┐  ┌───────────────────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ 1. PARALLEL      │  │ 2. FORENSIC AUDITOR & OCR JUDGE   │  │ 3. CI/CD QUALITY   │  │ 4. THREE-WAY SYNC  │
│    DEBUGGERS     │  │    (Dual Code & Story Forensics)  │  │    GATEKEEPER      │  │    COORDINATOR     │
│    SQUAD         │  │    - Story/Director/Visual Audit  │  │    - ISO Tester    │  │    - PyCompile AST │
│                  │  │    - [OCR] Line-Level Diff Review │  │    - Master Smoke  │  │    - Live Runtime  │
│                  │  │    - [OCR] Rule.json Enforcement  │  │    - [OCR] CodeGate│  │    - Git Push & CI │
└────────┬─────────┘  └─────────────────┬─────────────────┘  └─────────┬──────────┘  └─────────┬──────────┘
         │                              │                              │                       │
         ▼                              ▼                              ▼                       ▼
    Sửa mã lỗi VPS               Bắt 0% lỗi bảo mật,            Chặn đứng nếu có        Bảo chứng đồng bộ
    chuẩn đĩa cứng               memory leak, race condition,   defect High/Critical,   VPS ⇄ GitHub ⇄
    (B1.0 ➔ B11.0)               Rule 118-134 vi phạm           bảo đảm 100% Pass       Local bit-for-bit
```

### 1. Parallel Debuggers Squad (Đội ngũ Kỹ sư Chữa Cháy Song Song)
- **Nhiệm vụ**: Chẩn đoán và sửa lỗi trực tiếp trên mã nguồn chuẩn tại đĩa cứng VPS (`/root/video_factory`).
- **Phân rã theo Block**: Bóc tách theo từng khối chuyên môn (B1, B1.5, B2, B3, B3.5, B4, B5, B6, B7, B8, B10, B11).
- **Kỷ luật**: Tuyệt đối không tạo file rác ngoài `/tmp/` (Rule 119) và dọn sạch ngay sau khi chạy; không tạo script shadow bypass hệ thống; không để tồn tại file backup `.bak*` (Rule 125).

### 2. Independent Forensic Auditor & OCR Review Judge (Kiểm Toán Viên Kép: Kịch Bản & Mã Nguồn)
- **Nhiệm vụ**: Thẩm định khách quan chất lượng đầu ra với tâm thế không tin tưởng (Zero Trust).
- **Bộ tiêu chí pháp y nội dung**:
  - *Story Gate*: Đánh giá 12 tiêu chí NLP kịch bản, Rule 444 Hook, 5-Beat Docudrama.
  - *Director Plan*: 9 trục kỹ thuật (`scene_coverage`, `5beat_structure`, `fg_bg_prompts`, `reuse_keys`, `safe_zone`, `duration`, `camera_tension`, `narration`, `semantic_relevance`).
  - *Visual Audit*: Tiêu chuẩn 4 trục Rule 122 (0% tech leak, 0% stuttering, 100% Cel-shaded FG trên nền #FF00FF magenta chroma key, 16:9 cinematic BG).
  - *Rule 128 Anti-Semantic-Bias*: Thẩm định ma trận đa miền (Cross-Domain Matrix), cấm rò rỉ ngữ cảnh/từ vựng giữa các tập phim khác nhau.
  - *Rule 134 Pre-Sync Adversarial Sweep*: Quét đối soát nhất quán toàn văn (Full-Text Consistency Sweep) mọi hằng số cấu hình, tham số nghiệp vụ, threshold, và thông điệp cảnh báo trên 100% file liên đới.
- **Bộ tiêu chí kiểm toán mã nguồn (Alibaba OCR Engine)**:
  - *Độ chính xác Line-Level*: Đọc Git diff của các thay đổi (staged, unstaged, hoặc commit diff) với zero position drift.
  - *Quy chuẩn `.opencodereview/rule.json`*: Tự động đối soát tập luật riêng của AI Video Factory:
    * Chặn memory leaks trong xử lý buffer Sharp / Remotion canvas (B7).
    * Chặn unclosed file descriptors trong audio streaming EdgeTTS / Whisper (B6).
    * Chặn race condition trong multi-process concurrency / subprocesses (Orchestrator).
    * Bắt buộc UTF-8 encoding trên 100% thao tác I/O; cấm bare `except:` và silent `pass`.
    * Chặn đứng vi phạm Rule 118 (Zero-Mock Data) và Rule 128 (Zero Semantic Bias).
  - *Chế độ Hybrid (Dual Mode)*:
    * **Delegation Mode (`ocr delegate`)**: OCR phân tích AST, bóc tách diff và phân giải ruleset, bàn giao cho Host Agent (Antigravity) suy luận sâu — hoàn toàn 0 tốn thêm API token rời.
    * **Direct Mode (`ocr review`)**: Tự động hóa headless trên VPS thông qua OpenRouter / Gemini API gateway với context `-b / --background`.

### 3. CI/CD Quality Gatekeeper (Người Giữ Cửa Chất Lượng CI/CD)
- **Nhiệm vụ**: Tự động kích hoạt toàn bộ các chốt chặn kiểm thử tự động trước khi cho phép chuyển giao:
  - **Chốt 1**: Chạy kiểm thử láng giềng liên khối ISO Neighbor-Testing `tests/ci_neighbor_tester.py` theo quy tắc `[N-1, N, N+1]`.
  - **Chốt 2**: Chạy Master E2E Smoke Gate `scripts/e2e_pipeline_smoketest.py` kiểm tra toàn diện 7 Gate.
  - **Chốt 3 (MỚI - OCR Code Quality Gate)**: Quét toàn bộ mã nguồn thay đổi qua Alibaba Open Code Review. Bắt buộc đạt `Zero Critical / Zero High Defect`. Bất kỳ lỗi High/Critical nào sẽ kích hoạt Fail-Fast và trả về cho Squad Debugger sửa ngay.
- **Kỷ luật**: Chỉ đóng dấu phê duyệt khi 100% cả 3 chốt chặn đều trả về Exit Code `0`.

### 4. Three-Way Physical Sync Coordinator (Điều Phối Viên Đồng Bộ Vật Lý 3 Chiều)
- **Nhiệm vụ**: Bảo chứng đồng bộ dữ liệu tuyệt đối giữa 3 thực thể: **VPS ⇄ GitHub ⇄ Local/Notion**.
- **Quy trình 6 bước bắt buộc**:
  1. Biên dịch AST `python3 -m py_compile` toàn bộ file Python trên VPS.
  2. Thực thi kiểm thử runtime sống hàm sửa đổi (Rule 127: `python3 -c "from <module> import <func>; <func>(...)"`).
  3. **OCR Pre-Sync Gate**: Kiểm tra Git status và xác nhận diff uncommitted đạt `PASS` trên OCR Engine.
  4. Git Commit & Push trực tiếp từ VPS lên GitHub `hoangdinhhungueh-droid/AI_Vifactory.git`, kiểm tra `working tree clean`.
  5. **Cổng Bảo Chứng GitHub Actions CI Bắt Buộc (Mandatory CI Gate)**: Chạy `python scripts/watch_github_ci.py --commit <HEAD_SHA>` theo dõi cho đến khi GitHub Actions trả về `conclusion: success`. CẤM TUYỆT ĐỐI báo cáo thành công khi CI chưa PASS.
  6. Đồng bộ ngược file về Local Windows Workspace, đối soát SHA256 đạt 100% bit-for-bit parity. Quét sạch file tạm: `find /root/video_factory -name '*.bak*' -o -name '*.backup*'` trả về 0 file (Rule 125).

---

## ⚡ II. CÚ PHÁP KÍCH HOẠT & CÁCH SỬ DỤNG (INVOCATION RUNBOOK)

### 1. Kích hoạt trong Chat UI Antigravity (`/vf-pipeline-teamwork`)

Hệ thống hỗ trợ lệnh chuẩn `/vf-pipeline-teamwork` (cùng các alias `/teamwork:pipeline`, `/run:teamwork`, `/vf:teamwork`):

```markdown
# Cú pháp chuẩn:
/vf-pipeline-teamwork [action/blocks] [task_id] [options]

# 1. Kích hoạt Open Code Review (OCR) quét mã nguồn vừa sửa đổi:
/vf-pipeline-teamwork review

# 2. Chạy toàn trình CI/CD Quality Gates (ISO Tester + E2E Smoke + OCR Code Gate):
/vf-pipeline-teamwork ci

# 3. Kích hoạt quy trình Đồng Bộ Vật Lý 3 Chiều (VPS ⇄ GitHub ⇄ Local):
/vf-pipeline-teamwork sync

# 4. Chạy full đội 4 vai debug và kiểm thử Block 1.0 đến 3.5:
/vf-pipeline-teamwork 1.0..3.5 task:KR_EP0001_pesticide-container-trust

# 5. Kiểm thử và thẩm định riêng Block 4.0 (Sinh ảnh) và Block 5.0 (Visual Audit):
/vf-pipeline-teamwork 4.0,5.0 task:EN_EP0260_macro_liquidity

# 6. Kích hoạt chế độ kiểm toán độc lập toàn bộ kịch bản và đạo diễn:
/vf-pipeline-teamwork audit task:KR_EP0001_pesticide-container-trust
```

---

### 2. Kích hoạt qua Dòng Lệnh CLI trên VPS (`scripts/orchestrator/runner.py`)

Hệ thống có thể chạy độc lập, tự động trên VPS thông qua CLI Runner tiêu chuẩn:

| Mục Đích | Lệnh Thực Thi Trên VPS |
| :--- | :--- |
| **[MỚI] Chạy Code Review (OCR)** | `python3 scripts/orchestrator/runner.py --mode review` |
| **[MỚI] Chạy OCR Delegation Mode** | `python3 scripts/orchestrator/runner.py --mode review --ocr-mode delegate` |
| **Chạy Toàn Trình CI Quality Gates** | `python3 scripts/orchestrator/runner.py --mode ci` (Gồm ISO + Smoke + OCR Gate) |
| **Kiểm tra & Đồng bộ 3 Chiều** | `python3 scripts/orchestrator/runner.py --mode sync` (Gồm OCR Pre-Sync + CI Watcher) |
| **Chạy Pipeline hoàn chỉnh** | `python3 scripts/orchestrator/runner.py --mode pipeline --blocks 1.0..3.5 --task-id <EP_ID>` |
| **Chạy Dry-Run (Không tốn token)** | `python3 scripts/orchestrator/runner.py --mode pipeline --blocks 1.0..3.5 --dry-run` |
| **Chạy 1 Block đơn lẻ** | `python3 scripts/orchestrator/runner.py --mode block --blocks 2.0 --task-id <EP_ID>` |
| **Chạy Forensic Audit** | `python3 scripts/orchestrator/runner.py --mode audit --task-id <EP_ID>` |
| **Dọn sạch rác `/tmp/` (Rule 119)** | `python3 scripts/orchestrator/runner.py --cleanup-tmp` |

*Ghi chú*: Từ máy Windows, bạn có thể gọi từ xa lên VPS bất cứ lúc nào qua runner chuẩn:
```powershell
python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode review"
python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode ci"
```

---

## 🗺️ III. MA TRẬN MAPPING CHUYÊN BIỆT THEO TỪNG BƯỚC PIPELINE (B1 ➔ B11)

Dưới đây là bảng phân nhiệm cụ thể cho đội ngũ Multi-Agent khi thực thi từng bước trong pipeline, tích hợp trọng tâm kiểm toán mã nguồn OCR:

| Block | Tên Bước | Nhiệm Vụ Debugger Squad | Tiêu Chuẩn Forensic Auditor | Trọng Tâm OCR Code Review Focus | Chốt Chặn CI Gatekeeper |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **B1.0** | **Trend Gate & Discovery** | Dynamic Episode Numbering tịnh tiến tự động (`EN_EP0260+`, Rule 117); nạp Google Trends RSS live; Wikipedia Reality Anchor. | Kiểm tra độ dài prompt rules (<1,200 chars), 0 prompt contamination. | Kiểm tra regex parser, URL timeout, xử lý HTTP error không văng exception unhandled. | `pytest tests/test_trend_gate_b1.py`<br>`ci_neighbor_tester.py --block 1.0` |
| **B1.5** | **YouTube Competitor Recon** | Two-Pass Recon; trích xuất Fatal Explanatory Vacuum; bóc tách top comment YouTube; Blue Ocean gap mapping. | Không lặp duplicate call B1.5 trong produce; thẻ `competitor_intel_card.json` đầy đủ schema. | Đóng HTTP sessions, cấm rò rỉ API descriptors, an toàn JSON parsing. | `pytest tests/test_competitor_recon_b15.py` |
| **B2.0** | **5-Beat Docudrama Story** | Sinh kịch bản 1,800–2,200 từ theo cấu trúc 5 Beat Docudrama (Rule 445); An Ong Hook (Rule 444); triệt tiêu nhãn `GPT-5.6-Sol`. | **Story Gate 12/12 Criteria**: open loops, pacing, hook shock < 60 words, banned phrases. | **Rule 118 Zero-Mock Data**: Cấm tuyệt đối fake numbers trong text generator; UTF-8 write. | `ci_neighbor_tester.py --block 1.0`<br>(Kiểm tra [B1 -> B1.5 -> B2]) |
| **B3.0** | **Art Director & Breakdown** | Phân rã 35–55 scenes; trích xuất Universal Dynamic Context & Character Ensemble (Rule 128); non-destructive brain deep-merge. | **Director Audit 9 Trục**: điểm số >= 8.0/10; 0% rò rỉ phòng server sang nông nghiệp; bối cảnh era anchor chuẩn. | **Rule 128 Zero Semantic Bias**: Cấm hardcode tên tập/nhân vật vào breakdown schema. | `ci_neighbor_tester.py --block 3.0`<br>`pytest tests/test_director_planner_b3.py` |
| **B3.5** | **Prompt Forge & Anti-Stutter** | Forging Layer 1 BG (16:9) + Layer 2 FG (#FF00FF flat chroma key); khử lặp từ kép (anti-stuttering regex); nén prompt < 1k tokens. | **Visual Prompt Audit**: 0% tech leaks, 0% stuttering, 100% Cel-shaded Graphic Novel FG. | Regex performance (anti-ReDoS), xử lý boundary rỗng trên prompt tokens. | `pytest tests/test_prompt_forge.py`<br>Gate 6 in Smoke Gate |
| **B4.0** | **Gemini Pro Web Image Gen** | Chrome Automation profile; sinh ảnh hàng loạt Zero Cost; 100% định dạng `.png`; lưu trữ `/var/vf/episodes/<ep>/assets/`. | Đối soát số lượng ảnh BG/FG khớp 100% với `prompts_forge.json`; không bị thiếu asset. | Quản lý vòng đời trình duyệt Chrome; đóng zombie processes; dọn rác temp buffers. | Kiểm tra HTTP `200 OK` khi tải và lưu file ảnh thực tế. |
| **B5.0** | **Visual Audit HSV Chroma Gate** | Tự động tách nền HSV Chroma Key; kiểm tra viền mượt; phát hiện thủng áo/thủng tóc nhân vật. | **Rule 122 Visual Audit 4 Trục**: UI artifact = 0%, alpha integrity = 100%, style graphic novel cel-shaded. | Giải phóng bộ nhớ Pillow/OpenCV matrix sau khi xử lý; cấm memory leaks. | `python3 app/audit/visual_audit_b5.py` |
| **B6.0** | **TTS Voice & Subtitles** | Sinh voice EdgeTTS / ElevenLabs; chạy Whisper bóc tách word-level timestamps; chuẩn hóa format subtitle SRT/VTT. | Đối soát **Rule 120**: Karaoke millisecond sync; không lệch audio duration so với director plan. | **Resource Management**: Đóng subprocess pipes của ffmpeg/whisper; cấm rò rỉ file descriptors. | Kiểm tra file `.mp3` và `.srt` tồn tại, audio playable > 0 bytes. |
| **B7.0** | **Remotion Video Render** | Gắn kết Layer 1 BG + Layer 2 FG + Audio + Subtitles vào React Remotion Canvas; render MP4 CPU trên VPS. | Khung hình 1080x1920 (Shorts) hoặc 1920x1080 (Long); tốc độ khung hình 30fps; không bị đen frame. | **Remotion Anti-OOM**: Cặp `delayRender`/`continueRender` trong `try/finally`; giải phóng heavy image buffers. | Render smoke test scene đầu tiên đạt exit code 0. |
| **B8.0** | **Quality Gate 2** | Kiểm tra toàn diện video thành phẩm: độ khớp tiếng, âm lượng nhạc nền (BGM ducking), vị trí safe-zone phụ đề. | Thẩm định video hoàn chỉnh đạt tiêu chuẩn xuất bản kênh chính thức. | Xử lý audio normalization; an toàn ffmpeg subprocess; safe zone margin check. | `e2e_pipeline_smoketest.py` Gate 7 |
| **B10.0**| **SEO Metadata & Upload** | Đóng gói Title, Description, Tags, Hero Thumbnail, cấu hình `status.containsSyntheticMedia: true`. | Tiêu chuẩn đóng gói bao bì video YouTube chuẩn SEO; không chứa từ khóa cấm. | Schema validation theo YouTube Data API v3; an toàn sanitize chuỗi đầu vào. | Kiểm tra JSON metadata hợp lệ theo YouTube Data API v3 schema. |
| **B11.0**| **Analytics 48h Dreaming** | Quét số liệu YouTube Studio API sau 48h (Rule 113); phân tích AVD/Retention drop-off; tổng hợp 3 Action Items cải tiến. | Phân tích số liệu thật (Zero-Mock Rule 118); đồng bộ tri thức vào Notion Skill Learning Loop. | **Rule 118 Zero-Mock**: Missing metrics phải trả về `None`; cấm fallback sang hardcoded mock views. | `python scripts/b11_antigravity_engine.py --routine` |

---

## 🔧 IV. HƯỚNG DẪN MỞ RỘNG & QUY TẮC CUSTOM RULESET (`.opencodereview/rule.json`)

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

## ⚖️ V. HIẾN PHÁP BẮT BUỘC KHI CHẠY SKILL NÀY (KỶ LUẬT THÉP)

Mọi Agent/Subagent tham gia vào Skill này **BẮT BUỘC TUÂN THỦ 7 ĐIỀU RĂNG**:
1. **Rule 118 (Zero-Mock Data)**: Cấm tuyệt đối dữ liệu giả, điểm số bịa đặt. Số liệu phải đo lường từ log runtime thật.
2. **Rule 119 (Tự động thu hồi `/tmp/`)**: Mọi file tạm, sandbox worker bắt buộc dọn dẹp sạch sẽ qua `resource_recycler.py`.
3. **Rule 121 (Bằng chứng pháp y)**: Chỉ xác nhận PASS khi in log HTTP `200 OK`, Exit Code `0`, hoặc trích dẫn File/Line cụ thể.
4. **Rule 125 (Single Truth & Zero-Ghost)**: Cấm song song 2 version trong cùng 1 pipeline. Dọn sạch 100% file `.bak*`, shadow scripts.
5. **Rule 126 (Đồng bộ vật lý 3 chiều)**: Mọi sửa đổi phải nằm trên đĩa cứng VPS, commit & push git, CI Watcher completed `success`, và khớp SHA256 với local.
6. **Rule 127 (Thực thi runtime hàm sống)**: Cấm nghiệm thu chỉ bằng `py_compile`; bắt buộc gọi hàm thực tế không văng Exception.
7. **Rule OCR (Zero Critical/High Defect Gate)**: Cấm commit hoặc bàn giao bất kỳ dòng mã nào chứa lỗi phân loại `Critical` hoặc `High` từ Alibaba Open Code Review.
