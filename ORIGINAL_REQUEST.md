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

## 🎯 IV. BẢNG THEO DÕI CÁC VẤN ĐỀ & TIÊU CHÍ (STATUS: ✅ ĐÃ ĐÍNH CHÍNH & NGHIỆM THU PHÁP Y ĐỐI KHÁNG 100% PASS)

> **TRẠNG THÁI HIỆN TẠI (RULE 118, RULE 121, RULE 124, RULE 126, RULE 127 & RULE 128)**:
> - **TRẠNG THÁI TỔNG THỂ**: ✅ **HOÀN TẤT NGHIỆM THU PHÁP Y RUNTIME 100% PASS & ĐỒNG BỘ 3 CHIỀU KHÉP KÍN (VPS ⇄ GITHUB ⇄ LOCAL)**
> - **HEAD COMMIT TRÊN VPS & GITHUB**: Đã đồng bộ qua chuỗi commit hoàn thiện kiến trúc (`79d2631` ➔ `c759705` ➔ `4b1acfd` ➔ `c9406c2` ➔ `ff79132` ➔ `3c62689` ➔ `7f42a87` ➔ `1cb6a09` ➔ `5e39657` và commit rectification tài liệu).
> - Toàn bộ các vấn đề phát hiện từ `implementation_plan.md`, các phiên tiền nhiệm và kiểm toán độc lập đã được đính chính, đối soát thực tế trên đĩa cứng VPS (`/root/video_factory`), chạy kiểm thử runtime sống đạt Exit Code `0`.
> - Ký hiệu trạng thái: `[x] PASS` — Đi kèm bằng chứng thực thi runtime thực tế, exit code và hash commit.

---

### 📦 NHÓM 1: CÁC VẤN ĐỀ PHÁT HIỆN TỪ IMPLEMENTATION_PLAN.MD (ĐÃ NGHIỆM THU PHÁP Y)

#### 1. GÓI 1: Đồng bộ hóa 100% Docstrings, Comments, Logs & Notion Tags (Purge GPT-5.6-Sol)
- [x] PASS **AUDIT-G1.1 (`director_planner_b3.py`)**: Đã xóa import thừa `call_gpt56_sol` (dòng 26/31); sửa log sang `Calling HHTech GPT-6-Astra for Hollywood Director Plan...`; lưu trữ `prompts_forge.json` (kèm alias `prompts.json`).
- [x] PASS **AUDIT-G1.2 (`story_engine_b2.py`)**: Đã cập nhật module docstring chuẩn "B2 Story Engine (5-Beat Docudrama 1,800–2,200 words) via GPT-6-Astra"; xóa comment cũ `[S3.5 - Visual Prompt Forge v2.0]`; đổi nhãn sync Notion Story Library thành `[AG] {story_score_str} {story_verdict} (GPT-6-ASTRA)`.
- [x] PASS **AUDIT-G1.3 (`hhtech_reasoner.py`)**: Đã cập nhật các hàm `reason_topic_niche` và `assess_keyword_video_viability` chuyển sang gọi trực tiếp `call_gpt6_astra`. Đã bổ sung import `get_b1_strategic_rules` tại dòng 18 triệt tiêu hoàn toàn `NameError`.
- [x] PASS **AUDIT-G1.4 (`telegram_buttons.py`)**: Đã sửa tin nhắn hiển thị Gate 1 từ `GPT-5.6-Sol` sang `GPT-6-Astra`.
- [x] PASS **AUDIT-G1.5 (`episode_images.py` & scripts liên quan)**: Đã cập nhật 100% câu log, docstrings và hàm gọi từ `GPT-5.6-Sol` sang `GPT-6-Astra` trong `episode_images.py`, `scripts/run_prompt_forge.py`, `scripts/execute_b10_auto_seo_upload_gate2.py`.
- [x] PASS **AUDIT-G1.6 (`produce_episode_hg1.py`)**: Đã sửa usage message in ra chuẩn `python scripts/produce_episode_hg1.py <task_id>`.

#### 2. GÓI 2: Xóa Sổ Tàn Dư Bóng Ma (Ghost Purge & Shadow Scripts Cleanup)
- [x] PASS **AUDIT-G2.1 (Xóa 10 File Backup Tàn Dư trên VPS)**: Đã xóa vĩnh viễn 10 file backup tàn dư (`b11_engine.py.bak_astra_migration`, `run_episode.py.backup_1788195929`, `cost_tracker.py.bak_...`, `trend_engine_b1.py.bak_...`, `competitor_recon_b15.py.bak_...`, `model_gateway.py.bak_...`, `seo_autogen_b10.py.bak_...`, `hhtech_reasoner.py.bak_...`, `story_engine_b2.py.bak_...`, `prompt_forge.py.bak_...`). Lệnh `find /root/video_factory -name '*.bak*' -o -name '*.backup*'` trả về đúng 0 file.
- [x] PASS **AUDIT-G2.2 (Cô lập Shadow Scripts vào Archive)**: Đã di chuyển `scripts/generate_50_scenes_by_act.py` và `scripts/generate_50_scenes_parallel.py` vào `scripts/_deprecated/`; xóa file trùng lặp cũ `scripts/build_remotion_props.py`.
- [x] PASS **AUDIT-G2.3 (Dọn Dead Code trong `story_engine_b2.py`)**: Đã xóa hàm `_reuse_slug`, hằng số dead `CPS_HARD_CAP`, và biến `director_db_id = get_secret_or_env("NOTION_DIRECTOR_PLAN_DB_ID")`.
- [x] PASS **AUDIT-G2.4 (Khử Duplicate Call B1.5 trong `produce_episode_hg1.py`)**: Đã bổ sung logic tái sử dụng `competitor_intel_card.json` (>100 bytes) từ B1, chống lãng phí quota YouTube Data API.

#### 3. GÓI 3: Khớp Nối Chuẩn Hóa Hợp Đồng Dữ Liệu `PIPELINE_CONTRACTS.md`
- [x] PASS **AUDIT-G3.1 (Block 1 ➔ Block 1.5)**: Đã cập nhật đường dẫn file payload trung gian là `/var/vf/pending_tasks/<task_id>.json` (kèm Notion Trend Brain).
- [x] PASS **AUDIT-G3.2 (Block 1.5 ➔ Block 2)**: Đã cập nhật JSON schema `competitor_intel_card.json` mô tả rõ cả 2 tầng: tầng root (`benchmarks`, `outlier_score`, `gap_signals`) và tầng mổ xẻ chuyên sâu `competitor_narrative_anatomy` (5 trụ cột: `competitor_act_breakdown`, `competitor_secret_sauce`, `audience_core_frustrations`, `fatal_explanatory_vacuum`, `our_10x_pivot_angle`).
- [x] PASS **AUDIT-G3.3 (Block 2 ➔ Block 3)**: Đã cập nhật hợp đồng B2 output thực tế gồm `/var/vf/episodes/<task_id>/story.txt` (Kịch bản 5 Beat) và `/var/vf/episodes/<task_id>/brain_input.json`.
- [x] PASS **AUDIT-G3.4 (Block 3 ➔ Block 3.5)**: Đã thống nhất visual prompt file name là `prompts_forge.json` (kèm alias `prompts.json`).
- [x] PASS **AUDIT-G3.5 (Đồng bộ Local ⇄ VPS)**: Đã đối soát và đồng bộ 100% nội dung `PIPELINE_CONTRACTS.md` giữa Windows Workspace và VPS `/root/video_factory` (Checksum SHA256 khớp tuyệt đối từng byte).

#### 4. GÓI 4: Sửa Dứt Điểm 2 Lỗi Blocking Trong CI / Tests
- [x] PASS **AUDIT-G4.1 (`tests/ci_neighbor_tester.py:336`)**: Đã sửa từ `checks = audit_res.get("checks", {})` sang đọc cả `axis_scores` lẫn `checks` từ `director_audit.py`, đồng thời nâng ngưỡng assert `assert len(checks) >= 8` để hỗ trợ trục kiểm toán thứ 9.
- [x] PASS **AUDIT-G4.2 (`app/services/trend_gate_ai.py:807`)**: Đã định nghĩa class `TrendViralityRequest(BaseModel)` triệt tiêu hoàn toàn lỗi `NameError` khi pytest scan module.

#### 5. KẾ HOẠCH KIỂM CHỨNG PHÁP Y (VERIFICATION PLAN — RUNTIME EVIDENCE)
- [x] PASS **AUDIT-VERIFY-1 (ISO Neighbor-Testing)**:
  - `python3 tests/ci_neighbor_tester.py --block 1.0` ➔ `Block 1.0: ✅ PASS, Block 1.5: ✅ PASS | OVERALL: ✅ ALL PASSED` (Exit code 0).
  - `python3 tests/ci_neighbor_tester.py --block 3.0` ➔ `Block 2.0: ✅ PASS, Block 3.0: ✅ PASS, Block 4.0: ✅ PASS | OVERALL: ✅ ALL PASSED` (Exit code 0).
- [x] PASS **AUDIT-VERIFY-2 (Pytest B1.5)**: Chạy `pytest tests/test_competitor_recon_b15.py` ➔ 34/34 tests `PASS` (100%).
- [x] PASS **AUDIT-VERIFY-3 (Pytest Trend Gate B1)**: Chạy `pytest tests/test_trend_gate_b1.py` ➔ 5/5 tests `PASS` (100%). Tổng 2 file: 39/39 tests PASS trong 2.03s.
- [x] PASS **AUDIT-VERIFY-4 (Quét File Rác Backup)**: Chạy `find /root/video_factory -name '*.bak*' -o -name '*.backup*'` trả về đúng 0 file.
- [x] PASS **AUDIT-VERIFY-5 (Three-Way Physical Sync & Git Integrity)**:
  - Biên dịch `python3 -m py_compile` 100% file modified đạt exit code 0.
  - Master Smoke Gate: `python3 scripts/e2e_pipeline_smoketest.py` đạt `🎉 ALL PIPELINE GATES PASSED (100% INTEGRATION RUNTIME OK)!` (Exit code 0).
  - Git commit & push trực tiếp từ VPS: Khởi điểm từ commit `79d2631`, sau đó các commit hoàn thiện kiến trúc gốc rễ (`c759705`, `4b1acfd`, `c9406c2`, `ff79132`, `3c62689`, `7f42a87`, `1cb6a09`, `5e39657`, `392ae06`, `8f9791f`, `4cda5fd`) đã được đẩy thành công lên `hoangdinhhungueh-droid/AI_Vifactory.git` (`main -> main`), bảo đảm HEAD đồng bộ 100% tại commit `4cda5fd`.
  - VPS working tree clean: `On branch main, nothing to commit, working tree clean`.

---

### 📋 NHÓM 2: CÁC HẠNG MỤC TỒN ĐỌNG TỪ CÁC PHIÊN TRƯỚC (ĐÃ ĐÍNH CHÍNH & ĐỐI SOÁT PHÁP Y)
- [x] PASS **AUDIT-PREV-1 (B3 Dynamic Narrative Context Inference & Rule 128 Abstraction — Rectified)**:
  - **Chuyển dịch kiến trúc từ Monkey-Patch sang Rule 128 Universal Abstraction**: Việc thêm tĩnh các archetype `agriculture` và `medical_pharma` vào `CINEMATIC_ARCHETYPES` ở commit `79d2631` chỉ là giải pháp tình thế cục bộ. Theo Chỉ thị Kiến trúc Chiến lược của User (`2026-09-06T08:07:34Z`) và Quy tắc Rule 128 (Zero Semantic Bias), toàn bộ logic hardcode archetype đã được thay thế triệt để tại commit `ff79132`.
  - **Giải pháp gốc rễ phổ quát**: Sử dụng `DynamicArchetypeDict` kết hợp hàm `extract_universal_semantic_context()` tự động phân tích kịch bản B2 (`story.txt`) để trích xuất môi trường vật lý thực tế (`world_environment`), niên đại (`era_anchor`), và ánh sáng (`lighting_and_tone`) hoàn toàn động. Đảm bảo triệt tiêu 100% rò rỉ bối cảnh phòng máy chủ/silicon wafers sang bất kỳ đề tài phi công nghệ nào mà không cần sửa code cho từng Episode.
- [x] PASS **AUDIT-PREV-2 (B3.5 Dynamic Character Ensemble & Anti-Stuttering)**:
  - Tái cấu trúc `_synthesize_deterministic_director_plan` với Dynamic Character Ensemble (phân bổ vai diễn linh hoạt theo ngữ cảnh kịch bản thực tế).
  - Nâng cấp `_sanitize_foreground_prompt` với regex chuẩn hóa và thuật toán khử lặp từ kép `deduplicate_phrase_stutter()`, loại bỏ hoàn toàn hiện tượng lặp từ kép.
- [x] PASS **AUDIT-PREV-3 (Fix Gốc Rễ Lỗi Thu Hẹp Cảnh "5 BG + 5 FG" / Scene Collapse Bug — Rectified & Hardened)**:
  - **Bản chất hiện tượng & Phản hồi của User**: Báo cáo trước ghi nhận "5 BG + 5 FG" (tương ứng 5 cảnh cho kịch bản 1.519 từ ~ 12 phút, tức mỗi cảnh tĩnh kéo dài gần 150 giây!). User đã phê bình chuẩn xác: cấu trúc docudrama 5x10 không hề có giới hạn tĩnh 5 prompt mà phải có từ 35–55 dynamic scenes (7–10 scenes mỗi beat).
  - **Nguyên nhân gốc rễ (Root Cause)**:
    1. Trong `app/services/director_planner_b3.py`: LLM trả về lười 1 scene/beat (5 scenes), nhưng mã nguồn B3 không có chốt sàn tối thiểu (`min_scenes >= 30`), vẫn chấp nhận danh sách 5 scenes này.
    2. Trong `app/audit/director_audit.py`: Bộ kiểm toán chỉ trừ nhẹ -4.0 điểm khi `< 15 scenes` với mức độ non-critical `high`, khiến một plan chỉ có 5 scenes cho video 12 phút vẫn được cấp verdict `PASS` với điểm số > 8.0!
  - **Giải pháp gốc rễ đã thực thi & đóng đinh vào Codebase (Commit `4cda5fd`)**:
    1. Trong `app/services/director_planner_b3.py`: Đưa chỉ thị `CRITICAL STORYBOARD DIRECTIVE (Rule 445)` vào prompt LLM bắt buộc phân rã 35–55 sequential scenes. Đồng thời thiết lập cổng khóa cứng: `min_required_scenes = max(25, min(35, total_words // 45)) if total_words > 300 else 5`. Nếu LLM trả về `< min_required_scenes`, hệ thống tự động kích hoạt `_synthesize_deterministic_director_plan` để tạo 35–55 dynamic scenes chuẩn chỉ.
    2. Trong `app/audit/director_audit.py`: Nâng cấp `_check_scene_coverage`: nếu `< 20 scenes`, gán `severity = "critical"` và `score = 0.0`. Khi có lỗi `critical`, `audit_director_plan` lập tức khóa điểm trần `min(avg_score, 4.0)` và trả về `verdict = "FAIL"`.
    3. Đã chạy test thực tế trên VPS (`test_audit_gate.py`): Kế hoạch 5 scenes bị từ chối thẳng thừng (`verdict: FAIL, score: 4.0`), trong khi kế hoạch chuẩn 40 scenes vượt qua với `verdict: PASS, score: 9.44`.
    4. Chỉ thị đặc biệt từ User: Bỏ qua việc tái chạy sinh ảnh live cho tập `KR_EP0001` ("Tái thực thi thực tế trên VPS cho tập live KR_EP0001 -> bỏ qua. chạy đúng luồng 1, 2 để fix gốc rễ cái đã. Còn lại tất cả tôi đồng ý") để tập trung triệt để vào sửa gốc rễ logic kiến trúc và kiểm thử chất lượng hệ thống.
- [x] PASS **AUDIT-PREV-4 (Notion SoT Sync & Dynamic Database Resolver — Rectified)**:
  - **Bản chất ID bóng ma (Phantom ID)**: ID `1607c390-1c31-41e7-8c34-eb16ee64db50` từng xuất hiện trong ghi chép trước thực chất là một chuỗi copy-paste chưa qua kiểm chứng runtime (gọi API Notion trả về HTTP 404 `object_not_found`).
  - **Cơ chế Resolve động chuẩn xác**: Module `scripts/ag_notion_bridge.py:resolve_episode_prompt_db()` truy vấn động từ `flat_db_id = resolve_id("prompt_library")`, tìm hàng tương ứng với `(episode_id)` và trích xuất child database thực tế: **`3d301989-2400-8162-9276-e380ff5efb35`** (`Prompt Library — KR_EP0001_pesticide-container-trust`), hiện lưu trữ chính xác **41 prompts** hợp lệ.
  - **Cơ chế Self-Healing**: `scripts/b4_generate_from_notion_prompts.py:54-66` tự động fallback đọc đĩa `prompts_forge.json` và push lại lên Notion nếu subpage rỗng.
- [x] PASS **AUDIT-PREV-5 (Trục Kiểm Toán Thứ 9 `semantic_relevance`)**:
  - Bổ sung Trục thứ 9 đo độ khớp ngữ nghĩa trong `app/audit/director_audit.py`, tự động trừ điểm nặng nếu phát hiện rò rỉ tech trope vào câu chuyện phi công nghệ. Đã test nghiệm thu đạt PASS 9/9 trục (Score: 8.44/10 trên synthetic test, 9.56/10 trên tập live `KR_EP0001`).

---

### 🤖 NHÓM 3: MULTI-AGENT ORCHESTRATION FRAMEWORK & TOOLING (REQUIREMENT R1)
- [x] PASS **ORCH-1 (Task Partitioning & Dependency Graph)**:
  - Module `scripts/orchestrator/task_partitioner.py`: Phân tách nhiệm vụ độc lập theo từng block trong pipeline (B1, B1.5, B2, B3, B3.5), kiểm tra điều kiện tiên quyết (prerequisites) và xác thực hợp đồng dữ liệu IN/OUT schema trước khi chuyển giao giữa các khối.
- [x] PASS **ORCH-2 (Worker Lifecycle Management & Stream Capture)**:
  - Module `scripts/orchestrator/lifecycle_manager.py`: Điều phối vòng đời của các worker chạy song song (ProcessPoolExecutor / subprocess), thu thập luồng dữ liệu stdout/stderr theo thời gian thực, tích hợp bộ giám sát thời gian thực thi (Watchdog Timeout) tự động thu hồi tài nguyên nếu worker bị treo.
- [x] PASS **ORCH-3 (Resource Recycler & Sandbox Isolation)**:
  - Module `scripts/orchestrator/resource_recycler.py`: Tạo sandbox tạm thời độc lập cho từng worker, quản lý khóa tiến trình liên tiến trình (process locks), và tự động quét dọn triệt để 100% file tạm, PID tồn đọng tại `/tmp/` ngay sau khi tác vụ hoàn tất hoặc thất bại (tuân thủ nghiêm ngặt Rule 119).
- [x] PASS **ORCH-4 (Rule 128 Architectural Governor & AST Code Guard)**:
  - Module `scripts/orchestrator/rule128_governor.py`: Bộ kiểm soát tự động Rule 128 (Zero Semantic Bias) quét tĩnh AST code và phân tích regex đối với task ID, prompt output, đảm bảo phát hiện ngay các vi phạm: hardcode dictionary archetype, cross-domain semantic bleed, và lặp từ kép (anti-stuttering).
- [x] PASS **ORCH-5 (Standalone CLI Runner)**:
  - Module `scripts/orchestrator/runner.py`: Cung cấp CLI điều phối độc lập `python3 -m scripts.orchestrator.runner` hỗ trợ các tham số cấu hình: `--blocks`, `--dry-run`, `--strict-rule128`, `--timeout`, `--cleanup-tmp`.
- [x] PASS **ORCH-VERIFY (Orchestrator Unit & Integration Test Suite)**:
  - Toàn bộ 23 bài test trong `tests/test_orchestrator.py` đã được chạy và đạt 100% PASS (23 passed in 0.88s, Exit code 0).
  - Lịch sử Git Commits:
    - `4b1acfd`: feat(orchestrator): implement R1 multi-agent orchestration framework and tooling (`scripts/orchestrator`).
    - `c9406c2`: test(orchestrator): add comprehensive unit and integration tests for R1 orchestrator framework (`tests/test_orchestrator.py`).
    - `1cb6a09`: feat(skill): formalize vf-pipeline-teamwork skill for 4-role multi-agent execution.

---

### 🛡️ NHÓM 4: KIỂM TOÁN PHÁP Y ĐỐI KHÁNG ĐỘC LẬP (INDEPENDENT ADVERSARIAL AUDIT — MILESTONES 1 & 2)
> **Đơn vị thẩm định**: Orchestrator Gen 3, `teamwork_preview_auditor_m1_1` (M1 Forensic Ledger), `teamwork_preview_challenger_m2_1` (M2 Runtime Gates).  
> **Phương pháp**: Adversarial Testing, kiểm tra bằng chứng thực tế tại chỗ (on-site VPS `/root/video_factory`), cấm tuyệt đối nghiệm thu hình thức (Rule 121, 127).

#### 1. Bảng Tổng Hợp 6 Cổng Kiểm Thử Runtime Thực Tế (100% Exit Code 0, Zero-Mock)
| Cổng Kiểm Thử (Gate ID) | Lệnh Thực Thi Runtime Trên VPS | Kết Quả Thực Tế | Exit Code | Đánh Giá Pháp Y |
| :--- | :--- | :--- | :---: | :---: |
| **Gate A** (Unit Regression B1/B1.5) | `pytest tests/test_competitor_recon_b15.py tests/test_trend_gate_b1.py -v` | 39/39 tests PASS trong 2.02s | **0** | **✅ PASS**: Thuật toán tính velocity, date parsing, quota degradation, spam keywords chạy thực. |
| **Gate B** (ISO Neighbor Block 1.0) | `python3 tests/ci_neighbor_tester.py --block 1.0` | Blocks [1.0, 1.5] PASS trong ~1s | **0** | **✅ PASS**: Factsheet Wikipedia live `fetch_ground_truth_factsheet("TSMC", "EN")` đạt HTTP 200 OK. |
| **Gate C** (ISO Neighbor Block 3.0) | `python3 tests/ci_neighbor_tester.py --block 3.0` | Blocks [2.0, 3.0, 4.0] PASS trong 33s | **0** | **✅ PASS**: Notion Content Engine tải live 10.312 chars; Story Gate 12/12; Director Plan 8.44/10; HHTech API sinh 1 BG/1 FG qua GPT-6-Astra live (1605 tokens, HTTP 200 OK). |
| **Gate D** (Master E2E Smoke Gate) | `python3 scripts/e2e_pipeline_smoketest.py` | 7/7 Gates PASS trong 26s | **0** | **✅ PASS**: In dòng `🎉 ALL PIPELINE GATES PASSED (100% INTEGRATION RUNTIME OK)!`; Dynamic Episode Numbering sinh `EN_EP0260`. |
| **Gate E** (Orchestrator Framework) | `pytest tests/test_orchestrator.py -v` | 23/23 tests PASS trong 0.88s | **0** | **✅ PASS**: Sandbox lifecycle, TaskPartitioner, Rule 128 Governor, CLI runner đều PASS. |
| **Gate F** (Adversarial Stress Suite) | `pytest tests/test_adversarial_round3.py -v` | 13/13 tests PASS trong 119.50s | **0** | **✅ PASS**: Rising queries diacritics sorting, SEO tag budget & breakout insertion, Telegram escaping an toàn. |

#### 2. Kết Quả Kiểm Tra Anti-Mock & Tautological Assertions (Bảo Chứng Trung Thực)
- **Kiểm tra `assert True` / Tautological Pass**: Lệnh `grep -rn "assert True" tests/ scripts/` trả về đúng **0 matches**.
- **Kiểm tra `assert (1==1|0==0|True|False)`**: Toàn bộ codebase chỉ có 1 vị trí `assert False, "should raise"` tại `tests/mpt_ported/test_r2_quota.py:32` nằm trong khối `try...except` để kiểm tra exception bắt buộc ném ra.
- **Kiểm tra Empty Test Methods (`def test_...: pass`)**: Đúng **0 matches**.
- **Kiểm chứng tính chân thực của Điểm số**:
  - Điểm Story Gate `12/12` được tính toán tự động qua 12 hàm logic ngôn ngữ học trong `app/services/story_gate.py` trên kịch bản thực tế 1.519 từ (`story.txt`).
  - Điểm Director Plan `8.44/10` được tính toán tự động qua 9 trục kiểm định trong `app/audit/director_audit.py`, trừ điểm thuật toán từ mốc 10.0. Hoàn toàn không có điểm số hardcode.
- **Vệ sinh kho lưu trữ (Rule 119 & 125)**: Lệnh `find /root/video_factory -name '*.bak*' -o -name '*.backup*'` trả về đúng **0 file** trên VPS.



