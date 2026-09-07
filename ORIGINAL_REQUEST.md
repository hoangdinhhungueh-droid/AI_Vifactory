# 🎯 MASTER PROJECT SPECIFICATION & CONSOLIDATED ARCHITECTURE
# (SINGLE SOURCE OF TRUTH — MERGED FROM SESSIONS 1, 2, 3 & 4)

> **TÀI LIỆU KHẾ ƯỚC DỰ ÁN DUY NHẤT (RULE 124 & RULE 125)**
> Tổng hợp, cấu trúc hóa và hợp nhất toàn diện yêu cầu người dùng, phân tích pháp y, kế hoạch triển khai kỹ thuật và tiêu chí nghiệm thu từ 4 phiên làm việc liên tiếp.
> Toàn bộ các hạng mục trùng lặp đã được gom nhóm thành 6 Trụ Cột Kỹ Thuật (Master Pillars) để sửa chung 1 lần dứt điểm, đảm bảo không bỏ sót bất kỳ chi tiết nào ("Thừa còn hơn thiếu").

---

## 📜 I. LỊCH SỬ TIẾN TRÌNH & YÊU CẦU GỐC CỦA NGƯỜI DÙNG (CHRONOLOGICAL USER REQUESTS)

### 1. Phiên 1 (2026-09-05T12:14:05Z): Đồng bộ khế ước B1-B1.5-B2 & CI ISO Neighbor-Testing
<USER_REQUEST>
Rà soát và đồng bộ tuyệt đối khế ước dữ liệu IN/OUT từ Bước 1 (Trend Discovery) ➔ Bước 1.5 (Competitor Recon) ➔ Bước 2 (Story Engine 12–15 phút), dọn sạch rác và squash toàn bộ commit cũ thành 1 baseline duy nhất force-push lên GitHub `hoangdinhhungueh-droid/AI_Vifactory`, đồng thời đóng gói triển khai 3 Modular Blocks kèm bộ kiểm thử CI/CD ISO Neighbor-Testing (kiểm tra liên đới [N-1, N, N+1] khi bất kỳ block nào thay đổi).
</USER_REQUEST>

### 2. Phiên 2 (2026-09-05T20:45:00Z): Rà soát B1.5 ➔ B2 10x 5-Beat & Tái cấu trúc `competitor_recon_b15.py`
<USER_REQUEST>
1. Recheck lại: B1.5 -> B2 đã có 10x 5 nhịp cải tiến trước khi đưa cho Story rồi mà?
2. `competitor_recon_b15.py` -> cấu trúc lại triệt để code này theo đúng ruột tương ứng bên trong, tránh viết lan man, xóa bỏ comment cũ gây hiểu nhầm ("DATA COLLECTION ONLY"). Làm nổi bật rõ ràng phần `analyze_competitor_anatomy` lên.
</USER_REQUEST>

### 3. Phiên 3 (2026-09-06T04:30:00Z): Đại phẫu thuật Pháp y Toàn luồng (Sự cố Thẻ Telegram Adam Sandler)
<USER_REQUEST>
1. Tương tự như lỗi không tường minh ở `competitor_recon_b15.py`, rà soát xem đoạn code nào còn bị tương tự, conflict nhiều version thì báo cáo tôi trước. Gọi agent rà soát full code từ B1 -> B3 hiện tại. Thêm ý vào Rule 125 trong AGENTS.md về vấn đề cấm tuyệt đối sự không tường minh (Zero-Ambiguity Mandate).
2. Gọi agent review lỗi: với git đã commit ở bước 1 cào data cho đến human gate 1 với thông tin đang hiện như hiện tại, tôi cho rằng đang gặp vấn đề về cào và đánh số EP cũng như kết nối với notion - đây là lỗi kiến trúc nặng. Toàn bộ niche và đối thủ đều không đấu nối được. 5-Act Direction: kiểm tra đang dùng phiên bản mới 10x hay vẫn tàn dư.
3. Ghi nhận hiện trạng và đề xuất chỉnh sửa toàn bộ các bất đồng bộ, bug pipeline vào ORIGINAL_REQUEST.md - 06/09 debug bất đồng bộ - để tổng hợp sửa 1 lần.
</USER_REQUEST>

### 4. Phiên 4 (2026-09-06T06:12:00Z): Hợp nhất Kế hoạch Kỹ thuật & Nghiệm thu Triệt để
<USER_REQUEST>
Chuyển implementation_plan.md vào ORIGINAL_REQUEST.md luôn. Sau đó rà soát toàn bộ file ORIGINAL_REQUEST.md đang được tổng hợp từ 4 đoạn chat để cấu trúc lại, cái nào trùng và sửa chung 1 lần được thì cấu trúc, đảm bảo sửa hết toàn bộ, thừa còn hơn thiếu.
Sau đó gọi team audit ra check:
1. Checklist done.
2. Đảm bảo VPS - Notion - Git đồng bộ bản cuối cập nhật nhất, không còn bất đồng bộ.
</USER_REQUEST>

### 5. Phiên 5 (2026-09-06T08:03:51Z & 08:07:34Z): Điều Phối Multi-Agent Squad 4 Vai & Chỉ Thị Rule 128
<USER_REQUEST>
Xây dựng Framework điều phối Multi-Agent (Tooling / Runner) có khả năng tái sử dụng định kỳ, kết hợp điều phối đội Agent 4 vai thực hiện debug song song toàn bộ vấn đề từ B1 đến B3.5 trong ORIGINAL_REQUEST.md, kiểm toán pháp y độc lập, thực thi CI/CD Quality Gates và bảo chứng đồng bộ vật lý 3-Way (VPS ⇄ GitHub ⇄ Notion/Local).
[CHỈ THỊ KIẾN TRÚC CHIẾN LƯỢC — RULE 128]: Cấm tuyệt đối monkey-patching bias riêng cho từng Episode. Phải giải quyết ở gốc rễ cơ chế Universal Semantic Abstraction để dùng chung cho mọi Episode không phụ thuộc thể loại.
</USER_REQUEST>

### 6. Phiên 6 (2026-09-06T12:09:35Z): Kiểm Toán Chéo Đối Kháng & Xác Minh Đúng Sự Thật (Adversarial Forensic Audit Round 2)
<USER_REQUEST>
Thực hiện kiểm toán chéo độc lập và xác minh đúng sự thật (Adversarial Forensic Audit & Ground-Truth Verification) toàn bộ các hạng mục công việc mà Agent tiền nhiệm trong phiên "Resolving Agent Accountability Issues" (ID: `87517f5d-e6e7-4ba3-a422-68489d790286`) đã báo cáo hoàn tất trong file ORIGINAL_REQUEST.md. Xác minh đúng sự thật trên VPS (/root/video_factory), GitHub repo (hoangdinhhungueh-droid/AI_Vifactory.git), và Notion SoT theo các Kỷ luật thép (Rule 118, 121, 126, 127).
</USER_REQUEST>

### 7. Phiên 7 (2026-09-06T15:05:25Z): Kiểm Toán Đối Kháng Vòng 3 & Quality Gate Toàn Hệ Thống (Adversarial Forensic Audit Round 3)
<USER_REQUEST>
# Teamwork Project Prompt

> Requested team: Independent Adversarial Audit & Quality Gate Team (Round 3)

Thực hiện kiểm toán đối kháng vòng 3 (Adversarial Forensic Audit Round 3) độc lập và toàn diện trên toàn bộ hệ sinh thái AI Video Factory sau khi dọn sạch file trùng lặp và đồng bộ khế ước `ORIGINAL_REQUEST.md`. Xác minh đúng sự thật trên VPS (`/root/video_factory`), GitHub repo (`hoangdinhhungueh-droid/AI_Vifactory.git`), và Notion SoT theo Kỷ luật thép (Rule 118, 121, 125, 126, 127, 128, 129).

Working directory: c:\Users\hunghd2\Documents\antigravity\AI Video Factory
Integrity mode: development

## USER MANDATORY AUDIT DIRECTIVE
1. **Tuân thủ triệt để rule audit và framework đã xây dựng**: Sử dụng trực tiếp runner và các module kiểm soát trong `scripts/orchestrator/` (`runner.py`, `rule128_governor.py`, `resource_recycler.py`, `lifecycle_manager.py`), tuân thủ tuyệt đối các Kỷ luật thép (Rule 118, 121, 125, 126, 127, 128, 129).
2. **Tập trung vào `ORIGINAL_REQUEST.md` — Có task nào thì task đó phải đảm bảo DONE, phải có chứng minh, CẤM BÁO CÁO MÙ**:
   - Rà soát từng task một trong Mục IV của `ORIGINAL_REQUEST.md`:
     - Gói 1: AUDIT-G1.1 đến AUDIT-G1.6 (Docstrings, Comments, Logs & Purge GPT-5.6-Sol).
     - Gói 2: AUDIT-G2.1 đến AUDIT-G2.4 (Ghost Purge & Shadow Scripts Cleanup).
     - Gói 3: AUDIT-G3.1 đến AUDIT-G3.5 (Khớp nối hợp đồng `PIPELINE_CONTRACTS.md`).
     - Gói 4: AUDIT-G4.1 đến AUDIT-G4.2 (Sửa dứt điểm blocking CI/Tests).
     - Verification: AUDIT-VERIFY-1 đến AUDIT-VERIFY-5 (Kiểm chứng runtime, exit code, git commit).
     - Nhóm 2: AUDIT-PREV-1 đến AUDIT-PREV-5 (Dynamic Narrative Context, Character Ensemble, 35-55 dynamic scenes floor & coverage audit, Notion Dynamic DB Resolver `3d301989-2400-8162-9276-e380ff5efb35`, Trục kiểm toán 9).
     - Nhóm 3: ORCH-1 đến ORCH-VERIFY (Multi-Agent Orchestrator Framework).
   - Bất kỳ task nào tuyên bố PASS bắt buộc phải có bằng chứng pháp y tại chỗ: trích dẫn lệnh chạy runtime trên VPS, File Path, Line Numbers và Exit Code `0`. Tuyệt đối không chấp nhận báo cáo hình thức.

## Requirements

### R1. Comprehensive Codebase & Bug-Free Inspection (B1 ➔ B11)
- Rà soát toàn bộ các module đã refactor từ B1 đến B3.5, B4/B5, B10, B11.
- Kiểm tra độc lập xem còn tồn tại bug cú pháp, runtime exceptions, type mismatch, hoặc unhandled edge cases nào không.
- Rà soát nghiêm ngặt Rule 128 (Zero Semantic Bias — cấm hardcode domain/episode bias) và Rule 125 (Zero Ghost Remnant & Ambiguity) trên toàn bộ codebase.

### R2. Full-Spectrum Programmatic Runtime Execution Gate (Rule 121 & Rule 127)
- Thực thi kiểm thử runtime sống trên môi trường VPS `/root/video_factory` qua 6 cổng kiểm thử:
  1. `cd /root/video_factory && pytest tests/test_competitor_recon_b15.py tests/test_trend_gate_b1.py -v` (39/39 tests PASS).
  2. `cd /root/video_factory && python3 tests/ci_neighbor_tester.py --block 1.0` (Blocks 1.0, 1.5 PASS, Exit code 0).
  3. `cd /root/video_factory && python3 tests/ci_neighbor_tester.py --block 3.0` (Blocks 2.0, 3.0, 4.0 PASS, Exit code 0, Story Gate 12/12, Director Audit >= 8.0).
  4. `cd /root/video_factory && python3 scripts/e2e_pipeline_smoketest.py` (7/7 Gates PASS, in dòng `ALL PIPELINE GATES PASSED`).
  5. `cd /root/video_factory && pytest tests/test_orchestrator.py -v` (23/23 tests PASS).
  6. `cd /root/video_factory && pytest tests/test_adversarial_round3.py -v` (13/13 tests PASS).
- Kiểm tra tính chân thực của các bài test: cấm `assert True`, không mock số liệu, các điểm số (Story Gate, Director Plan) phải xuất phát từ thuật toán phân tích dữ liệu thực tế.

### R3. Three-Way Physical Sync & Cleanliness Audit (Rule 125 & Rule 126)
- Thẩm định tính toàn vẹn và đồng bộ 3 chiều (VPS `/root/video_factory` ⇄ GitHub repo `origin/main` ⇄ Local Windows Workspace `AI Video Factory`).
- Xác nhận checksum SHA256 của file khế ước `ORIGINAL_REQUEST.md` và `PIPELINE_CONTRACTS.md` khớp tuyệt đối giữa Local và VPS.
- Xác nhận file tàn dư trùng lặp `.agents/ORIGINAL_REQUEST.md` đã bị xóa bỏ hoàn toàn, chỉ còn duy nhất 1 bản Master Single Source of Truth tại thư mục gốc.
- Quét sạch 100% file rác backup (`*.bak*`, `*.backup*`) trên VPS, bảo đảm `git status` trên VPS trả về `working tree clean` và `up to date with origin/main`.

## Acceptance Criteria

### Test & Runtime Gates
- [ ] Toàn bộ 6 cổng kiểm thử runtime trên VPS trả về Exit Code `0` với bằng chứng in rõ ràng từ stdout/stderr.
- [ ] Không có assertion giả mạo (`assert True`, tautological pass) hay hàm test rỗng (`pass`).

### Zero-Ghost & Cleanliness
- [ ] `find /root/video_factory -name '*.bak*' -o -name '*.backup*'` trả về đúng 0 file trên VPS.
- [ ] Không còn file duplicate `.agents/ORIGINAL_REQUEST.md` trong workspace; duy nhất 1 file `ORIGINAL_REQUEST.md` tại root phản ánh 100% chính xác thực tế.
- [ ] `git -C /root/video_factory status` trả về `working tree clean` và commit HEAD khớp hoàn toàn với `origin/main`.

### Three-Way Sync Parity
- [ ] Checksum SHA256 của `ORIGINAL_REQUEST.md` giữa Windows Workspace và VPS `/root/video_factory` khớp tuyệt đối từng byte.
- [ ] Báo cáo kiểm toán Round 3 kết luận rõ ràng: hệ thống đã sẵn sàng 100%, không còn bug ngầm và tác động 3-way đã khép kín.
</USER_REQUEST>

---

## 🔍 II. BẢN ĐỒ PHÁP Y NGUYÊN NHÂN GỐC RỄ (FULL ROOT-CAUSE POST-MORTEM)

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        BẢN ĐỒ BẤT ĐỒNG BỘ & LỖI KIẾN TRÚC TOÀN PIPELINE                           │
├───────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. CHUỖI B1 ➔ B1.5 ➔ HUMAN GATE 1 (SỰ CỐ TELEGRAM EN_EP0001):                                     │
│    • Prompt Contamination 336k chars: hhtech_reasoner.py nhồi toàn bộ Notion Central Skill AI     │
│      (336.224 ký tự) vào LLM -> GPT-6-Astra bị ảo giác ngôi vị, từ chối phân tích và sinh:       │
│      "TẠM DỪNG — Skill registry unavailable...", khiến topic_name_vi, keyword, slug đều bị NULL. │
│    • Lỗi đánh số EP (Rule 117): trend_engine_b1.py gọi hàm ma _epnum.generate_episode_id          │
│      (không tồn tại trong episode_numbering.py) -> AttributeError bị except nuốt chửng ->         │
│      ép cứng fallback EN_EP0001_topic, đè nát kho số VPS (vốn đã sản xuất tới EN_EP0259/0260).   │
│    • Đứt gãy Niche & Đối thủ B1.5: Thứ tự ngược (B1 bắt LLM đoán gap trước khi B1.5 cào video).  │
│      Lệch key: B1.5 gán t_obj["competitor_gap"], nhưng Telegram Gate 1 đọc competitor_            │
│      differentiation_gap -> Toàn bộ kết quả cào thật từ B1.5 bị vứt bỏ trên Telegram!            │
│    • 5-Act Direction vs 10x 5-Beat: Ruột B2 đã có prompt 5-Beat Docudrama 10x, nhưng bị nhiễm    │
│      độc dữ liệu đầu vào từ B1 ("TẠM DỪNG..."), kèm tàn dư docstring ~1,200 words và nhãn Gate 1. │
│                                                                                                   │
│ 2. CHUỖI B2 ➔ B3 ➔ B3.5 (SỰ CỐ PROMPT & NOTION METADATA):                                         │
│    • Thẩm mỹ Prompt: 18 BG rò rỉ bối cảnh phòng máy chủ, silicon wafers; 10 FG trùng lặp 100%    │
│      (1,102 ký tự), lặp từ kép (stuttering), vắng bóng nhân vật thực tế của câu chuyện.          │
│    • Đấu nối Notion SoT: push_prompts_to_notion nuốt lỗi im lặng -> B4 query ra 0 prompts.       │
│      director_planner_b3.py ghi đè brain_input.json làm rớt mất story_gate_score: "12/12".       │
│                                                                                                   │
│ 3. TÀN DƯ BÓNG MA & QUY TẮC BẤT BIẾN RULE 125:                                                    │
│    • 10 file backup rác (*.bak_astra_migration, *.backup_*) xả rác trong thư mục code.           │
│    • 2 shadow scripts B3 (generate_50_scenes_*) bypass B3 và hardcode gpt-5.6-sol.                │
│    • Celery Task app/tasks/prompt_tasks.py gọi script ma không tồn tại prompt_forge_b3_5.py.      │
│    • B3 ghi file prompts.json trong khi Watcher/Poller chờ prompts_forge.json.                    │
│    • Docstrings / logs cũ mâu thuẫn: Vẫn ghi GPT-5.6-Sol tại hàng loạt service dù đã lên Astra.   │
│    • Hardcode số liệu giả lập (37, 18, 10, "12/12") trong exception handler của Watcher.          │
│                                                                                                   │
│ 4. LỖI CHẶN TRONG CI / TESTS (BLOCKING ISO TEST):                                                 │
│    • tests/ci_neighbor_tester.py:336 FAIL Block 3.0 do assert sai checks vs axis_scores.          │
│    • tests/ci_neighbor_tester.py FAIL Block 4.0 do lỗi type assumption trong prompt_forge.py.     │
│    • app/services/trend_gate_ai.py:807 thiếu class TrendViralityRequest gây crash NameError.      │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ III. KIẾN TRÚC HỢP NHẤT TOÀN HỆ THỐNG (6 MASTER PILLARS — SỬA CHUNG 1 LẦN)

### 🏛️ TRỤ CỘT 1: B1 Trend Engine & Strategic Reasoner (Rule 117, 118, 123)
1. **Triệt tiêu Prompt Contamination (336k chars)**:
   - File `app/services/skill_loader.py`: Xây dựng hàm `get_b1_strategic_rules()` chắt lọc tinh gọn (~1.200 ký tự) các quy chuẩn Rule 1-4 (Causal Mechanism), Rule 444 (An Ong Hook), Rule 118 (Zero-Mock), và Rule 445 (5-Beat Outline).
   - File `app/services/hhtech_reasoner.py`: Chuyển sang gọi `get_b1_strategic_rules()`. Tuyệt đối cấm tải 336k ký tự Notion Central Skills vào prompt LLM API, chấm dứt hoàn toàn hiện tượng GPT-6-Astra bị ảo giác và từ chối sinh dữ liệu ("TẠM DỪNG...").
2. **Chuẩn hóa Dynamic Episode Numbering (Rule 117)**:
   - File `app/services/trend_engine_b1.py:259`: Thay thế import ảo `_epnum.generate_episode_id` bằng hàm chuẩn `get_next_episode_id(market, slug)` từ `app.services.trend_gate_ai`.
   - Xóa bỏ fallback hardcode `EN_EP0001_topic`, đảm bảo cấp phát số tự động tịnh tiến theo kho số thực tế trên VPS (đang ở `EN_EP0259/0260`).
3. **Bổ sung Model Pydantic `TrendViralityRequest`**:
   - File `app/services/trend_gate_ai.py:807`: Bổ sung định nghĩa `class TrendViralityRequest(BaseModel): markets: list[str] | None = ["EN", "JP", "KR"], max_candidates: int = 1, auto_commit: bool = True, notify: bool = True` nhằm triệt tiêu lỗi `NameError` khi scan module.

---

### 🏛️ TRỤ CỘT 2: Tái Đấu Nối B1 ➔ B1.5 ➔ Human Gate 1 & Dữ Liệu Thực (Rule 123, 444, 445)
1. **Đấu nối liền mạch luồng thực thi**:
   - File `app/services/trend_engine_b1.py`:
     - Ngay sau khi B1 suy luận ra `search_specific_keyword` và `niche_angle_brief`, lập tức gọi B1.5 `recon_card = run_b15(task_id, recon_keyword, niche_brief)`.
     - Đồng bộ key: Gán `t_obj["competitor_differentiation_gap"] = recon_card["competitor_narrative_anatomy"]["fatal_explanatory_vacuum"]` và cập nhật lại tệp `pending_tasks/<task_id>.json`.
2. **Thẻ Telegram Gate 1 hiển thị dữ liệu cào thật**:
   - Tiêu đề nhãn: Đổi thành `• 5-Beat Docudrama:` theo đúng chuẩn Rule 445.
   - Hiển thị đầy đủ: Đề tài tiếng Việt, Search-Specific Key bản xứ, Cụm từ tìm kiếm tăng thật, Niche Brief, và Khoảng trống đối thủ (Blue Ocean Gap) cào thật từ YouTube Data API.
3. **Khử duplicate call B1.5 trong `scripts/produce_episode_hg1.py`**:
   - Kiểm tra nếu `competitor_intel_card.json` đã được B1 tạo ra và có kích thước hợp lệ (>100 bytes), tự động tái sử dụng, tránh cào đúp gây hao hụt quota YouTube API.
   - Sửa dòng thông báo usage thành `python scripts/produce_episode_hg1.py <task_id>`.

---

### 🏛️ TRỤ CỘT 3: Tuyệt Diệt Bóng Ma `GPT-5.6-Sol` & Zero-Ghost Mandate (Rule 125 & 125.4)
1. **Xóa sổ 100% tàn dư `GPT-5.6-Sol`**:
   - `app/services/hhtech_reasoner.py`: Cập nhật các hàm nội bộ (`reason_topic_niche`, `assess_keyword_video_viability`) gọi trực tiếp `call_gpt6_astra`.
   - `app/services/director_planner_b3.py`: Xóa import thừa `call_gpt56_sol` tại dòng 31; đổi log dòng 289 thành `Calling HHTech GPT-6-Astra for Hollywood Director Plan...`.
   - `app/services/story_engine_b2.py`: Cập nhật module docstring chuẩn 5-Beat Docudrama 1.800–2.200 từ; đổi nhãn đồng bộ Notion Story Library thành `[AG] {story_score_str} {story_verdict} (GPT-6-ASTRA)`. Dọn sạch dead code: `_reuse_slug`, `CPS_HARD_CAP`, `director_db_id`.
   - `app/services/telegram_buttons.py`: Đổi tin nhắn Gate 1 hiển thị chuẩn `GPT-6-Astra`.
   - `episode_images.py`, `scripts/run_prompt_forge.py`, `scripts/execute_b10_auto_seo_upload_gate2.py`, `send_live_sol_gate1.py`, `send_dynamic_gate1.py`: Đổi toàn bộ docstring và logs từ GPT-5.6-Sol sang GPT-6-Astra.
2. **Xóa sạch file rác và cô lập shadow scripts**:
   - Xóa vĩnh viễn 10 file backup rác `*.bak_astra_migration` và `*.backup_*` trên VPS.
   - Di chuyển 2 shadow scripts `scripts/generate_50_scenes_by_act.py` và `scripts/generate_50_scenes_parallel.py` vào `scripts/_deprecated/`.
   - Xóa file trùng lặp cũ `scripts/build_remotion_props.py` (giữ duy nhất bản chuẩn `app/services/build_remotion_props.py`).
3. **Chuẩn hóa Celery & File Watcher (Rule 118 & 119)**:
   - Sửa `app/tasks/prompt_tasks.py:57` trỏ đúng vào `scripts/run_prompt_forge.py --episode <episode_id>`.
   - Loại bỏ mock fallback `37, 18, 10, "12/12"` trong `scripts/watchers/prompts_forge_watcher.py`, trả về giá trị thực hoặc `0, 0, 0, "N/A"`.

---

### 🏛️ TRỤ CỘT 4: Kiến Trúc Thị Giác Phổ Quát B3/B3.5 & Xử Lý Gốc Rễ Đa Đề Tài (Rule 128: Zero-Domain-Bleed Mandate)
1. **Chuyển dịch mục tiêu từ "Vá cục bộ cho 1 Episode" sang "Xử lý gốc rễ phổ quát (Root-Cause Architecture)"**:
   - *Vấn đề cốt lõi*: Việc thêm riêng một archetype cụ thể (như "agriculture") hoặc fix riêng cho tập live `KR_EP0001` chỉ là giải pháp tình thế (EP-specific monkey patching). Nếu không xử lý ở gốc rễ cơ chế, các tập tiếp theo thuộc các chủ đề khác (y tế, khai khoáng, quân sự, văn hóa, kiến trúc...) sẽ tiếp tục bị rò rỉ bối cảnh hoặc rơi vào default sai lệch.
   - *Cơ chế gốc rễ phổ quát (Universal Semantic Context & Persona Extractor)*:
     - B3 Director Planner tự động đọc trực tiếp từ kịch bản B2 (`story.txt`) và bóc tách động 4 thành phần ngữ cảnh không phụ thuộc domain:
       1. `world_environment`: Môi trường vật lý thực tế của câu chuyện (địa hình, cảnh quan, khí hậu).
       2. `era_anchor`: Niên đại chính xác của sự việc (hiện đại, cổ đại, cận đại...) để ngăn chặn triệt để rò rỉ công nghệ/thời đại (Rule 122 & 128).
       3. `lighting_and_tone`: Bầu không khí thị giác và góc chiếu sáng tự nhiên tương ứng với biến cố tự sự.
       4. `dynamic_character_ensemble`: Trích xuất danh sách nhân vật/thực thể thực sự xuất hiện trong kịch bản (nạn nhân, nhân chứng, điều tra viên, chuyên gia...) cùng phục trang tương ứng, thay thế hoàn toàn danh sách vai diễn hardcode tĩnh.
2. **Universal Prompt Compiler & Anti-Stuttering Engine (B3.5)**:
   - Layer 1 BG: Luôn tổng hợp từ `setting_description` của B3 kết hợp với quy chuẩn an toàn thị giác (16:9, safe-zone bottom 20%, 0 foreground humans). Tuyệt đối không chứa bất kỳ từ khóa thiên vị ngầm nào (loại bỏ sạch mọi default relics "server racks, silicon wafers, modern glass offices").
   - Layer 2 FG: Luôn tổng hợp từ `character_description` của B3 kết hợp với quy chuẩn kỹ thuật (1:1, #FF00FF flat chroma key, stylized editorial graphic novel illustration).
   - Thuật toán làm sạch prompt phổ quát (Universal Anti-Stuttering Engine): Tự động khử trùng lặp token/cụm từ (n-gram deduplication), loại bỏ hoàn toàn hiện tượng lặp từ kép bất kể phong cách.
3. **Bảo tồn metadata không hủy diệt (Non-Destructive Deep Merge)**:
   - File `app/services/director_planner_b3.py`: Sử dụng deep merge cho `brain_input.json`. Đọc dữ liệu cũ từ B2 và chỉ cập nhật mảng `scenes`, bảo tồn nguyên vẹn `story_gate_score: "12/12"`, `market`, `topic`, `hook_3s`, `breakout_queries`.
4. **Khắc phục triệt để lỗi type assumption trong Prompt Forge Fallback**:
   - File `app/services/prompt_forge.py`: Hỗ trợ cả kiểu dữ liệu `str` lẫn `dict` cho `bg_meta` và `fg_meta`, triệt tiêu lỗi `AttributeError`. Nâng `max_tokens=4500` và auto-close JSON.
5. **Notion Prompt Sync & Self-Healing (Rule 120)**:
   - `push_prompts_to_notion` tự động khởi tạo subpage DB `Prompt Library — <episode_id>`, đồng bộ đủ 100% prompts và không nuốt lỗi.
   - B4 có cơ chế tự phục hồi (Self-Healing): nếu Notion rỗng nhưng local có `prompts_forge.json` hợp lệ, tự động đẩy lên Notion rồi mới sinh ảnh.

---

### 🏛️ TRỤ CỘT 5: Đồng Bộ Chuẩn Hóa Hợp Đồng Dữ Liệu `PIPELINE_CONTRACTS.md`
- **Block 1 ➔ Block 1.5**: Phản ánh đúng file lưu trữ là `/var/vf/pending_tasks/<task_id>.json` (kèm đồng bộ Notion Trend Brain).
- **Block 1.5 ➔ Block 2**: Cập nhật schema `competitor_intel_card.json` mô tả rõ cả 2 tầng: benchmarks ở root và 5 trụ cột narrative lồng trong `competitor_narrative_anatomy`.
- **Block 2 ➔ Block 3**: Cập nhật hợp đồng B2 output ra `/var/vf/episodes/<task_id>/story.txt` và `brain_input.json`.
- **Block 3 ➔ Block 3.5**: Thống nhất file visual prompt duy nhất là `prompts_forge.json` (kèm alias `prompts.json`).
- Đồng bộ hóa 100% giữa Local Antigravity Workspace và VPS `/root/video_factory/PIPELINE_CONTRACTS.md`.

---

### 🏛️ TRỤ CỘT 6: CI/CD ISO Neighbor-Testing & Three-Way Physical Sync (Rule 121, 126, 447)
1. **Sửa lỗi blocking trong CI Neighbor-Testing**:
   - `tests/ci_neighbor_tester.py:336`: Sửa `checks = audit_res.get("axis_scores") or audit_res.get("checks", {})`.
   - `app/audit/director_audit.py`: Thêm alias `"checks": axis_scores` vào return dict của `audit_director_plan`.
2. **Kiểm thử nghiệm thu ISO Neighbor-Testing đạt 100% PASS**:
   - `python3 tests/ci_neighbor_tester.py --block 1.0` ➔ Blocks [1.0, 1.5] PASS.
   - `python3 tests/ci_neighbor_tester.py --block 3.0` ➔ Blocks [2.0, 3.0, 4.0] PASS.
   - `pytest tests/test_competitor_recon_b15.py` ➔ 34/34 tests PASS (100%).
   - `pytest tests/test_trend_gate_b1.py` ➔ 5/5 tests PASS (100%).
3. **Three-Way Physical Sync (Rule 126)**:
   - Kiểm tra cú pháp toàn bộ file bằng `python3 -m py_compile` đạt exit code `0`.
   - Thực thi Git commit & push trực tiếp từ VPS lên GitHub `hoangdinhhungueh-droid/AI_Vifactory.git`.
   - Xác nhận `git status` trên VPS trả về `working tree clean`.

---

#### 🎯 IV. KHO LƯU TRỮ CÁC MỐC ĐÃ NGHIỆM THU PHÁP Y (CERTIFIED MILESTONES ARCHIVE — SESSIONS 1 TO 7)

> **CHỨNG THỰC PHÁP Y RUNTIME 100% PASS & ĐỒNG BỘ 3 CHIỀU (RULE 118, 121, 124, 126, 127, 128)**:
> - **Trạng thái tổng thể**: ✅ **TOÀN BỘ 31 HẠNG MỤC (AUDIT-G1..G4, AUDIT-PREV, ORCH, VÀ TASK-GOLIVE-1..4) ĐÃ ĐƯỢC AUDIT ĐỐI KHÁNG VÀ CI CI/CD CHỨNG THỰC 100% PASS**.
> - **Baseline Commits**: `7adde26` (Master Baseline) ➔ `ff79132` (Pillars 1-6) ➔ `4cda5fd` (Director Scene Floor) ➔ `856c021` (Golive Bridge, GitHub Actions CI Workflow 34056181759 Green).
> - **Tóm tắt 4 Task Go-Live hôm qua (2026-09-06)**:
>   - **TASK-GOLIVE-1 (Notion State Machine B1➔B3)**: ✅ Canonical 13 trường VF Trend Brain; State transitions tự động `Approved→Story` ➔ `Gate Passed` (Used) ➔ `Compiled` ➔ `Prompted` / `Produced`. Pytest `test_notion_state_machine.py` 5/5 PASS.
>   - **TASK-GOLIVE-2 (Safe Housekeeping & Cleanliness)**: ✅ Dọn sạch 111 file rác `/tmp/` trên VPS; working tree clean; 0 file `.bak*`.
>   - **TASK-GOLIVE-3 (Early SEO Forge B1.6 & 60s An Ong Hook)**: ✅ `seo_package_forge.py` sinh Title A/B, Description, 3 Hashtags, Tags, Hook 3s/60s; direct anchor vào B2 Act I; Zero-LLM B10; `test_b15_seo_package_forge.py` 6/6 PASS.
>   - **TASK-GOLIVE-4 (Bridge B3.5 ➔ Antigravity B4/B5 & Thumbnails)**: ✅ `prompt_forge.py` sinh Thumbnail A/B; Thẻ HG2 1-click copy; `gemini_browser_gen.py` xóa hardcode bối cảnh (Rule 128), audit pixel thật (Rule 122), đóng gói tar.gz base64 upload nguyên tử, marker `images_ready.json` kích hoạt B6; `test_b35_b4_bridge.py` 5/5 PASS.

---

## 🚀 VI. TIẾN TRÌNH CÔNG VIỆC HÔM NAY (2026-09-07 OPERATIONAL AUDIT & HARDENING)

> **Căn cứ yêu cầu người dùng ngày 2026-09-07**:
> 1. [x] **Kiểm toán báo cáo B4 & B5 từ phiên trước (`658d00a0-a568-406e-b554-11798f9554a7`)**: Làm rõ ranh giới giữa hoàn thành code cầu nối / unit test vs thực thi sinh ảnh sống thực tế trên Antigravity. Đã kiểm tra trình duyệt Chrome profile và chuẩn hóa quy trình chạy headless `gemini_browser_gen.py`.
> 2. [x] **Xử lý dứt điểm sự cố kho số Episode (`EN_EP0260`)**: Đã lưu trữ toàn bộ folder cũ sang `/var/vf/episodes/_archive/` và pending tasks cũ sang `_archive/`. Đã dọn sạch Notion Story Library, Director Plan và Prompt Library. Cập nhật dòng VF Trend Brain về `EN_EP0001_puka_contract_economics`. Kiểm thử `get_next_episode_id` trên VPS xác nhận kho số quay về chuẩn xác `EN_EP0001` (`max_num=1`).
> 3. [x] **Tinh gọn thông báo Telegram**: Loại bỏ thông báo trùng lặp `VF Daily Trend & Story Pipeline (B1 ➔ B3) — 1 Đề tài hoàn tất:` ở cuối script; chỉ giữ Human Gate 1 và Human Gate 2.
> 4. [x] **Tái cấu trúc Template Human Gate 2 & Skill `vf-image-gen`**: Tinh gọn thẻ HG2 thành bản tóm lược điều hành (Chủ đề, Đạo diễn Hollywood, Thống kê Scenes/BG/FG, Hook Thumbnail A/B) kèm khối lệnh 1-chạm:
>    ```
>    /vf-image-gen
>    /run:image --episode EN_EP0001_puka_contract_economics --headless
>    ```
>    Ủy quyền toàn bộ quy chuẩn kỹ thuật (2K DCI, #FF00FF Chroma HSV, 4-Trục Visual Audit Rule 122, Auto-Trigger `images_ready.json`) cho Skill `vf-image-gen`.
> 5. [x] **Tái tạo toàn diện Pipeline B1.5 ➔ B2 ➔ B3 ➔ B3.5 cho `EN_EP0001_puka_contract_economics`**:
>    - **B1.5**: YouTube Recon thực tế + 5 Trụ cột Narrative Anatomy qua GPT-6-Astra (`competitor_intel_card.json`, 16.5KB).
>    - **B1.6**: Gói SEO sớm & 60s An Ong Hook (`seo_package.json`, 2.9KB).
>    - **B2**: Kịch bản 5-Beat Docudrama 12–15 phút đạt chuẩn Story Gate 12/12 (`story.txt`, 14.9KB).
>    - **B3**: Kế hoạch đạo diễn 82 scenes chuẩn Sentence-Atomic Pacing (ngắt trọn vẹn câu, $\le 35$ từ/scene, Safe-Zone FG Left/Right), đồng bộ 82/82 scenes vào Child DB Scenes (`3d401989-2400-81a3-8618-d7078f65f98c`).
>    - **B3.5**: Prompt Forge 20 BG, 15 FG và 2 Hero Thumbnails (`prompts_forge.json`, 52KB), đồng bộ 37/37 prompts vào Prompt Library DB (`3d401989-2400-811a-ab14-c0854469b921`).
>    - **Human Gate 2**: Đã phát thẻ Telegram mới về Telegram (Message ID: `456`).
> 6. [x] **Three-Way Physical Sync & CI Verification (Rule 126)**:
>    - Pytest trên VPS: 10/10 tests PASS (`test_b35_b4_bridge.py`, `test_trend_gate_b1.py`).
>    - Commit VPS: `6f6b6f245de4e397e801db9a60031f6f08848067`.
>    - GitHub Actions CI Watcher: [Workflow Run 34086874750](https://github.com/hoangdinhhungueh-droid/AI_Vifactory/actions/runs/34086874750) đạt `conclusion: success` (exit code 0).

---

## 💎 VII. CẬP NHẬT TIẾN TRÌNH SẢN XUẤT & PHẪU THUẬT GỐC RỄ PIPELINE (2026-09-07 SESSION 8)

> **Căn cứ yêu cầu người dùng ngày 2026-09-07 (/vf-pipeline-teamwork /grill-me)**:
> 1. [x] **Nâng cấp toàn diện Skill `/vf-image-gen` & Playwright Automation**:
>    - Runbook `SKILL.md` chuẩn hóa quy trình tự động 7 bước (Đọc Task ID, Nạp nguyên lý không nhiễm độc prompt, Quét asset Notion/VPS, Sinh ảnh 2K DCI + #FF00FF Magenta, Audit song song 4 trục, Download ảnh gốc, Auto-trigger B6).
>    - `gemini_browser_gen.py`: Bổ sung bộ lọc task id thông minh, kiểm tra nhất quán B3.5 prompts vs B3 scenes, mặc định tự động handoff sang B6 `continue_after_images.py` khi B5 đạt PASS.
> 2. [x] **Phẫu thuật gốc rễ B1 Trend Discovery & B1.5 Competitor Recon (Sửa sai trend Puka Nacua)**:
>    - `hhtech_reasoner.py`: Xóa bỏ triệt để các ví dụ hardcode gây neo ngữ nghĩa (Rule 128) `Puka Nacua rookie contract`, `Livedoor stock fraud`, `Gramoxone`, thay thế bằng Generic Pattern Placeholders.
>    - `trend_engine_b1.py`: Tích hợp Google Trends Real-Time Rising / Breakout Queries qua `pytrends` trước khi autocomplete; Đảo thứ tự B1.5 Pre-Recon chạy trước `reason_topic_niche` để nạp đúng khoảng trống đối thủ (Fatal Explanatory Vacuum), thất vọng khán giả và top bình luận vào LLM.
> 3. [x] **Khắc phục Story Gate 12/12 cho mọi Episode**:
>    - `story_engine_b2.py`: Nâng ngưỡng kích hoạt Auto-Refine lên `< 12` (thay vì `< 10`), ép buộc Tiêu chí 9 (Hook Shock số liệu trong 60 từ đầu) và Tiêu chí 12 (Pattern Interrupt câu $\le 6$ từ ngắt nhịp) trong System Prompt.
>    - CI Neighbor Test Block 3.0 nghiệm thu thực tế: đạt tuyệt đối **12/12 (Words: 1519) | Verdict: PASS**.
> 4. [x] **Triệt tiêu thông báo trùng lặp Human Gate 2**:
>    - `prompts_forge_watcher.py`: Chuyển sang chế độ passive validation (chỉ log và sync trạng thái), vô hiệu hóa việc dispatch Telegram từ watcher.
>    - Duy nhất 1 thông báo Human Gate 2 gửi từ pipeline script theo mẫu tinh gọn 1-chạm chuẩn mực khớp 100% hình ảnh điều hành.
> 5. [x] **Chuẩn hóa Dynamic Director Principle (Loại bỏ mâu thuẫn Adam McKay / David Fincher)**:
>    - `director_planner_b3.py`: Gỡ bỏ sự kết hợp trái ngược Adam McKay / David Fincher khỏi Corporate Noir; Bổ sung phong cách `Sports Documentary Realism (Moneyball Principle)` cho chủ đề thể thao/vận động viên; Khẳng định Astra 6 là Đạo diễn duy nhất.
> 6. [x] **Kiểm thử chất lượng toàn hệ thống & Three-Way Physical Sync (Rule 121, 126, 127)**:
>    - `py_compile`: Toàn bộ 6 file trên VPS đạt exit code `0`.
>    - Pytest: 44/44 unit tests PASS (100%).
>    - CI Neighbor Testing: Block 1.0 PASS; Block 3.0 PASS (Story Gate 12/12, Director Audit 8.44/10).
>    - Master E2E Smoke Gate: 8/8 Gates PASS (in dòng `ALL PIPELINE GATES PASSED`).

---

## 🏛️ VIII. THIẾT LẬP 5 TRỤ CỘT NỘI DUNG SIÊU LỢI NHUẬN & CƠ CHẾ ĐIỀU TRA Ý ĐỒ TÌM KIẾM (2026-09-07 SESSION 9)

> **Căn cứ chỉ đạo chiến lược người dùng ngày 2026-09-07**:
> 1. [x] **Khóa Chặt 5 Trụ Cột Nội Dung Siêu Lợi Nhuận (High-RPM / High-Retention Pillars)**:
>    - Trụ cột 1: **Business Rise & Fall** ($18–$45 CPM) — Corporate Noir (David Fincher / Margin Call).
>    - Trụ cột 2: **Modern History & Systemic Crisis** ($10–$20 CPM) — Historical Realism (Christopher Nolan / Johan Renck).
>    - Trụ cột 3: **True Crime Non-Graphic** ($8–$18 CPM, CTR 8–14%) — Forensic Procedural Noir (David Fincher).
>    - Trụ cột 4: **Psychology & Behavioral Manipulation** ($10–$22 CPM) — Psychological Puzzle Drama (Denis Villeneuve).
>    - Trụ cột 5: **Tech & Geopolitical Systemic Battles** ($25–$50 CPM) — Cyber & Geopolitical Thriller (Sicario / Zero Dark Thirty).
>    - *Code hóa*: Cập nhật `AUTOCOMPLETE_SEEDS` và `AUTOCOMPLETE_SEEDS_BY_MARKET` trong `app/services/trend_gate_ai.py`; Cập nhật `detect_safety_and_theme` trong `app/services/hhtech_reasoner.py`.
> 2. [x] **Hủy Bỏ Phong Cách Thể Thao Không Cần Thiết**:
>    - Đã gỡ bỏ hoàn toàn `Sports Documentary Realism (Moneyball Principle)` khỏi `app/services/director_planner_b3.py` và điều hướng 100% về 5 phong cách tương ứng với 5 trụ cột.
> 3. [x] **Giữ Vững & Code Hóa Rule Loại Bỏ Tin Đồn / Suy Đoán Vô Căn Cứ (Anti-Speculation & Fact-Anchored Gate)**:
>    - Chuẩn hóa điều khoản cưỡng chế trong `assess_keyword_video_viability`: REJECT ngay lập tức các đề tài đời tư, tranh cãi dân sự chưa có phán quyết, hoặc tin đồn chưa có án phạt chính thức (nguyên nhân Astra tự động reject Puka Nacua).
> 4. [x] **Search Intent Forensics (Pháp Y Ý Đồ Tìm Kiếm qua Rising Queries)**:
>    - Bắt buộc nạp cụm từ tìm kiếm bùng nổ (`rising_queries` qua pytrends live) vào `assess_keyword_video_viability` và `reason_topic_niche`.
>    - Khóa quy tắc: `specific_viral_angle` bắt buộc giải mã đúng động cơ bùng nổ thực tế của người xem thay vì tái chế góc nhìn cũ (như trường hợp Elizabeth Holmes bùng nổ vì phim tài liệu mới A24 thay vì vụ án Theranos 2023).
> 5. [x] **Dọn Dẹp Tàn Dư & Sẵn Sàng Kho Số `EN_EP0001`**:
>    - Lưu trữ tập `EN_EP0001_puka_contract_economics` cũ vào `_archive/` trên VPS.
>    - Lưu trữ các trang Notion tương ứng trong VF Trend Brain, Story Library, Director Plan, Prompt Library.
>    - Xác nhận `get_next_episode_id("EN")` quay về chuẩn xác `EN_EP0001`.
> 6. [x] **Master E2E Smoke Test & Three-Way Sync**:
>    - Pytest: 10/10 tests PASS.
>    - E2E Smoketest: 8/8 Gates PASS (`ALL PIPELINE GATES PASSED`).



