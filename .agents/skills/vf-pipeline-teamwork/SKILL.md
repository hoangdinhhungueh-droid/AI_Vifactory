---
name: vf-pipeline-teamwork
description: >-
  Quy trình điều phối đội ngũ Multi-Agent 4 vai chuyên biệt cho AI Video Factory (VF Pipeline Hardening & Execution).
  Kích hoạt khi nhận các lệnh /teamwork:pipeline, /run:teamwork, /vf:teamwork, hoặc khi user yêu cầu kiểm thử,
  debug song song, thẩm định độc lập, chạy CI/CD quality gates và đồng bộ 3 chiều cho các bước B1 đến B11.
---

# 🛡️ VF Pipeline Multi-Agent Teamwork Skill (`/teamwork:pipeline`)

> **Phiên bản chuyên dụng cao cấp (Enhanced Teamwork Preview)** dành riêng cho dây chuyền sản xuất video tự động **AI Video Factory (VF Pipeline)**.
> Chuẩn hóa cấu trúc điều phối đội ngũ 4 vai độc lập, tích hợp chặt chẽ với CLI Runner `scripts/orchestrator/`, tuân thủ nghiêm ngặt **Kỷ Luật Thép Rule 118 – Rule 128** và bảo chứng đồng bộ 3 chiều (VPS ⇄ GitHub ⇄ Local).

---

## 🎯 I. CƠ CHẾ VẬN HÀNH & 4 VAI TRÒ ĐỘC LẬP (4 AUTONOMOUS ROLES)

Khi nhận lệnh `/teamwork:pipeline` hoặc khi cần kiểm thử/debug bất kỳ bước nào trong pipeline, Agent đóng vai trò **Điều Phối Viên (Orchestrator)** sẽ tự động kích hoạt hoặc mô phỏng đội ngũ 4 vai chuyên biệt:

```
                      ┌──────────────────────────────────────┐
                      │    VF TEAMWORK ORCHESTRATOR / RUNNER │
                      │      (scripts/orchestrator/runner)   │
                      └──────────────────┬───────────────────┘
                                         │
       ┌──────────────────┬──────────────┴───────────────┬──────────────────┐
       ▼                  ▼                              ▼                  ▼
┌──────────────┐  ┌──────────────┐              ┌──────────────┐  ┌──────────────────┐
│  PARALLEL    │  │  FORENSIC    │              │  CI QUALITY  │  │  THREE-WAY SYNC  │
│  DEBUGGERS   │  │  AUDITOR     │              │  GATEKEEPER  │  │  COORDINATOR     │
│  (Squad)     │  │ (Judge)      │              │ (CI/CD Gates)│  │ (Rule 126 & 127) │
└──────┬───────┘  └──────┬───────┘              └──────┬───────┘  └────────┬─────────┘
       │                 │                             │                   │
       ▼                 ▼                             ▼                   ▼
  Khắc phục mã     Thẩm định 12/12               ISO Neighbor       Biên dịch AST,
  lỗi trực tiếp    Story Gate, 9 trục            Testing [N-1,N,N+1]& test runtime sống,
  trên VPS đĩa     Director, 4 trục              Master E2E Smoke   commit & push git,
  cứng (/root)     Visual & Rule 128             Gate (7/7 Gates)   đối soát SHA256 100%
```

### 1. Parallel Debuggers Squad (Đội ngũ Kỹ sư Chữa Cháy Song Song)
- **Nhiệm vụ**: Chẩn đoán và sửa lỗi trực tiếp trên mã nguồn chuẩn tại VPS (`/root/video_factory`).
- **Phân rã theo Block**: Bóc tách theo từng khối chuyên môn (B1, B1.5, B2, B3, B3.5, B4, B5, B6, B7, B8, B10, B11).
- **Kỷ luật**: Tuyệt đối không tạo file rác ngoài `/tmp/` (Rule 119) và dọn sạch ngay sau khi chạy; không tạo script shadow bypass hệ thống.

### 2. Independent Forensic Auditor (Kiểm Toán Viên Pháp Y Độc Lập - Audit as Judge)
- **Nhiệm vụ**: Thẩm định khách quan chất lượng đầu ra với tâm thế không tin tưởng (Zero Trust).
- **Bộ tiêu chí pháp y**:
  - *Story Gate*: Đánh giá 12 tiêu chí NLP kịch bản, Rule 444 Hook, 5-Beat Docudrama.
  - *Director Plan*: 9 trục kỹ thuật (`scene_coverage`, `5beat_structure`, `fg_bg_prompts`, `reuse_keys`, `safe_zone`, `duration`, `camera_tension`, `narration`, `semantic_relevance`).
  - *Visual Audit*: Tiêu chuẩn 4 trục Rule 122 (0% tech leak, 0% stuttering, 100% Cel-shaded FG trên nền #FF00FF magenta chroma key, 16:9 cinematic BG).
  - *Rule 128 Anti-Semantic-Bias*: Thẩm định ma trận đa miền (Cross-Domain Matrix), cấm rò rỉ ngữ cảnh/từ vựng giữa các tập phim khác nhau.
- **Kỷ luật**: Zero-Mock Score (Rule 118) — Cấm hardcode điểm số; phải in log và dữ liệu đo lường thực tế.

### 3. CI/CD Quality Gatekeeper (Người Giữ Cửa Chất Lượng CI/CD)
- **Nhiệm vụ**: Tự động kích hoạt các chốt chặn kiểm thử tự động trước khi cho phép chuyển giao:
  - Chạy kiểm thử láng giềng liên khối ISO Neighbor-Testing `tests/ci_neighbor_tester.py` theo quy tắc `[N-1, N, N+1]`.
  - Chạy Master E2E Smoke Gate `scripts/e2e_pipeline_smoketest.py` kiểm tra toàn diện 7 Gate.
  - Chạy bộ Unit Tests Pytest tương ứng của từng Block (`tests/test_*.py`).
- **Kỷ luật**: Chỉ đóng dấu phê duyệt khi 100% các bài test trả về Exit Code `0`.

### 4. Three-Way Physical Sync Coordinator (Điều Phối Viên Đồng Bộ Vật Lý 3 Chiều)
- **Nhiệm vụ**: Bảo chứng đồng bộ dữ liệu tuyệt đối giữa 3 thực thể: **VPS ⇄ GitHub ⇄ Local/Notion**.
- **Quy trình 6 bước bắt buộc**:
  1. Biên dịch AST `python3 -m py_compile` toàn bộ file Python trên VPS.
  2. Thực thi kiểm thử runtime sống hàm sửa đổi (Rule 127: `python3 -c "from <module> import <func>; <func>(...)"`).
  3. Git Commit & Push trực tiếp từ VPS lên GitHub `hoangdinhhungueh-droid/AI_Vifactory.git`, kiểm tra `working tree clean`.
  4. **Cổng Bảo Chứng GitHub Actions CI Bắt Buộc (Mandatory CI Gate)**: Chạy `python scripts/watch_github_ci.py --commit <HEAD_SHA>` theo dõi cho đến khi GitHub Actions trả về `conclusion: success`. CẤM TUYỆT ĐỐI báo cáo thành công khi CI chưa PASS.
  5. Đồng bộ ngược file về Local Windows Workspace, đối soát SHA256 đạt 100% bit-for-bit parity.
  6. Quét sạch file tạm: `find /root/video_factory -name '*.bak*' -o -name '*.backup*'` trả về 0 file (Rule 125).

---

## ⚡ II. CÚ PHÁP KÍCH HOẠT & CÁCH SỬ DỤNG (INVOCATION RUNBOOK)

### 1. Kích hoạt trong Chat UI Antigravity (`/teamwork:pipeline`)

Khi bạn nhập lệnh `/teamwork:pipeline` trong phiên chat, Agent sẽ tự động phân tích tham số và định tuyến:

```markdown
# Cú pháp chuẩn:
/teamwork:pipeline [blocks] [task_id] [options]

# Ví dụ 1: Chạy full đội 4 vai debug và kiểm thử Block 1.0 đến 3.5
/teamwork:pipeline 1.0..3.5 task:KR_EP0001_pesticide-container-trust

# Ví dụ 2: Kiểm thử và thẩm định riêng Block 4.0 (Sinh ảnh) và Block 5.0 (Visual Audit)
/teamwork:pipeline 4.0,5.0 task:EN_EP0260_macro_liquidity

# Ví dụ 3: Kích hoạt chế độ kiểm toán độc lập cho toàn bộ kịch bản và đạo diễn
/teamwork:pipeline audit task:KR_EP0001_pesticide-container-trust

# Ví dụ 4: Chạy kiểm thử CI/CD và Master Smoke Gate
/teamwork:pipeline ci
```

---

### 2. Kích hoạt qua Dòng Lệnh CLI trên VPS (`scripts/orchestrator/runner.py`)

Hệ thống có thể chạy độc lập, tự động trên VPS thông qua CLI Runner tiêu chuẩn:

| Mục Đích | Lệnh Thực Thi Trên VPS |
| :--- | :--- |
| **Chạy Pipeline hoàn chỉnh** | `python3 scripts/orchestrator/runner.py --mode pipeline --blocks 1.0..3.5 --task-id <EP_ID>` |
| **Chạy Dry-Run (Không tốn token)** | `python3 scripts/orchestrator/runner.py --mode pipeline --blocks 1.0..3.5 --dry-run` |
| **Chạy 1 Block đơn lẻ** | `python3 scripts/orchestrator/runner.py --mode block --blocks 2.0 --task-id <EP_ID>` |
| **Chạy Forensic Audit** | `python3 scripts/orchestrator/runner.py --mode audit --task-id <EP_ID>` |
| **Chạy CI Quality Gate** | `python3 scripts/orchestrator/runner.py --mode ci` |
| **Kiểm tra Đồng bộ 3 Chiều** | `python3 scripts/orchestrator/runner.py --mode sync` |
| **Dọn sạch rác `/tmp/` (Rule 119)** | `python3 scripts/orchestrator/runner.py --cleanup-tmp` |

*Ghi chú*: Từ máy Windows, bạn có thể gọi từ xa lên VPS bất cứ lúc nào:
```powershell
python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode audit --task-id <EP_ID>"
```

---

## 🗺️ III. MA TRẬN MAPPING CHUYÊN BIỆT THEO TỪNG BƯỚC PIPELINE (B1 ➔ B11)

Dưới đây là bảng phân nhiệm cụ thể cho đội ngũ Multi-Agent khi thực thi từng bước trong pipeline:

| Block | Tên Bước | Nhiệm Vụ Debugger Squad | Tiêu Chuẩn Forensic Auditor | Chốt Chặn CI Gatekeeper |
| :--- | :--- | :--- | :--- | :--- |
| **B1.0** | **Trend Gate & Discovery** | Dynamic Episode Numbering tịnh tiến tự động (`EN_EP0260+`, Rule 117); nạp Google Trends RSS live; Wikipedia Reality Anchor. | Kiểm tra độ dài prompt rules (<1,200 chars), 0 prompt contamination. | `pytest tests/test_trend_gate_b1.py`<br>`ci_neighbor_tester.py --block 1.0` |
| **B1.5** | **YouTube Competitor Recon** | Two-Pass Recon; trích xuất Fatal Explanatory Vacuum; bóc tách top comment YouTube; Blue Ocean gap mapping. | Không lặp duplicate call B1.5 trong produce; thẻ `competitor_intel_card.json` đầy đủ schema. | `pytest tests/test_competitor_recon_b15.py` |
| **B2.0** | **5-Beat Docudrama Story** | Sinh kịch bản 1,800–2,200 từ theo cấu trúc 5 Beat Docudrama (Rule 445); An Ong Hook (Rule 444); triệt tiêu nhãn `GPT-5.6-Sol`. | **Story Gate 12/12 Criteria**: open loops, pacing, hook shock < 60 words, banned phrases. | `ci_neighbor_tester.py --block 1.0`<br>(Kiểm tra [B1 -> B1.5 -> B2]) |
| **B3.0** | **Art Director & Breakdown** | Phân rã 35–55 scenes; trích xuất Universal Dynamic Context & Character Ensemble (Rule 128); non-destructive brain deep-merge. | **Director Audit 9 Trục**: điểm số >= 8.0/10; 0% rò rỉ phòng server sang nông nghiệp; bối cảnh era anchor chuẩn. | `ci_neighbor_tester.py --block 3.0`<br>`pytest tests/test_director_planner_b3.py` |
| **B3.5** | **Prompt Forge & Anti-Stutter** | Forging Layer 1 BG (16:9) + Layer 2 FG (#FF00FF flat chroma key); khử lặp từ kép (anti-stuttering regex); nén prompt < 1k tokens. | **Visual Prompt Audit**: 0% tech leaks, 0% stuttering, 100% Cel-shaded Graphic Novel FG. | `pytest tests/test_prompt_forge.py`<br>Gate 6 in Smoke Gate |
| **B4.0** | **Gemini Pro Web Image Gen** | Chrome Automation profile; sinh ảnh hàng loạt Zero Cost; 100% định dạng `.png`; lưu trữ `/var/vf/episodes/<ep>/assets/`. | Đối soát số lượng ảnh BG/FG khớp 100% với `prompts_forge.json`; không bị thiếu asset. | Kiểm tra HTTP `200 OK` khi tải và lưu file ảnh thực tế. |
| **B5.0** | **Visual Audit HSV Chroma Gate** | Tự động tách nền HSV Chroma Key; kiểm tra viền mượt; phát hiện thủng áo/thủng tóc nhân vật. | **Rule 122 Visual Audit 4 Trục**: UI artifact = 0%, alpha integrity = 100%, style graphic novel cel-shaded. | `python3 app/audit/visual_audit_b5.py` |
| **B6.0** | **TTS Voice & Subtitles** | Sinh voice EdgeTTS / ElevenLabs; chạy Whisper bóc tách word-level timestamps; chuẩn hóa format subtitle SRT/VTT. | Đối soát **Rule 120**: Karaoke millisecond sync; không lệch audio duration so với director plan. | Kiểm tra file `.mp3` và `.srt` tồn tại, audio playable > 0 bytes. |
| **B7.0** | **Remotion Video Render** | Gắn kết Layer 1 BG + Layer 2 FG + Audio + Subtitles vào React Remotion Canvas; render MP4 CPU trên VPS. | Khung hình 1080x1920 (Shorts) hoặc 1920x1080 (Long); tốc độ khung hình 30fps; không bị đen frame. | Render smoke test scene đầu tiên đạt exit code 0. |
| **B8.0** | **Quality Gate 2** | Kiểm tra toàn diện video thành phẩm: độ khớp tiếng, âm lượng nhạc nền (BGM ducking), vị trí safe-zone phụ đề. | Thẩm định video hoàn chỉnh đạt tiêu chuẩn xuất bản kênh chính thức. | `e2e_pipeline_smoketest.py` Gate 7 |
| **B10.0**| **SEO Metadata & Upload** | Đóng gói Title, Description, Tags, Hero Thumbnail, cấu hình `status.containsSyntheticMedia: true`. | Tiêu chuẩn đóng gói bao bì video YouTube chuẩn SEO; không chứa từ khóa cấm. | Kiểm tra JSON metadata hợp lệ theo YouTube Data API v3 schema. |
| **B11.0**| **Analytics 48h Dreaming** | Quét số liệu YouTube Studio API sau 48h (Rule 113); phân tích AVD/Retention drop-off; tổng hợp 3 Action Items cải tiến. | Phân tích số liệu thật (Zero-Mock Rule 118); đồng bộ tri thức vào Notion Skill Learning Loop. | `python scripts/b11_antigravity_engine.py --routine` |

---

## 🔧 IV. HƯỚNG DẪN MỞ RỘNG (PLUG-AND-PLAY CHO CÁC KHỐI MỚI)

Để mở rộng hoặc gắn thêm bất kỳ module nào vào hệ thống điều phối, chỉ cần 2 thao tác chuẩn:

1. **Khai báo Contract trong `scripts/orchestrator/task_partitioner.py`**:
   Thêm định nghĩa `StageContract` vào `PIPELINE_STAGES` với:
   - `input_files`: Danh sách file đầu vào bắt buộc.
   - `output_files`: Danh sách file đầu ra cam kết tạo ra.
   - `command_template`: Lệnh thực thi Python chuẩn trên VPS.
2. **Khai báo Quality Gate trong `scripts/e2e_pipeline_smoketest.py`**:
   Thêm hàm kiểm tra Gate tương ứng để Master Smoke Gate tự động bảo vệ tính toàn vẹn của pipeline.

---

## ⚖️ V. HIẾN PHÁP BẮT BUỘC KHI CHẠY SKILL NÀY (KỶ LUẬT THÉP)

Mọi Agent/Subagent tham gia vào Skill này **BẮT BUỘC TUÂN THỦ 6 ĐIỀU RĂNG**:
1. **Rule 118 (Zero-Mock Data)**: Cấm tuyệt đối dữ liệu giả, điểm số bịa đặt. Số liệu phải đo lường từ log runtime thật.
2. **Rule 119 (Tự động thu hồi `/tmp/`)**: Mọi file tạm, sandbox worker bắt buộc dọn dẹp sạch sẽ qua `resource_recycler.py`.
3. **Rule 121 (Bằng chứng pháp y)**: Chỉ xác nhận PASS khi in log HTTP `200 OK`, Exit Code `0`, hoặc trích dẫn File/Line cụ thể.
4. **Rule 126 (Đồng bộ vật lý 3 chiều)**: Mọi sửa đổi phải nằm trên đĩa cứng VPS, commit & push git, và khớp SHA256 với local.
5. **Rule 127 (Thực thi runtime hàm sống)**: Cấm nghiệm thu chỉ bằng `py_compile`; bắt buộc gọi hàm thực tế không văng Exception.
6. **Rule 128 (Chống thiên kiến dữ liệu)**: Cấm hardcode tên tập, nhân vật, bối cảnh cục bộ vào schema chung của hệ thống.
