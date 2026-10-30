# 🏛️ MASTER REFORM PLAN 2.0: SYSTEMIC DYNAMIC ARCHITECTURE, LEAN NOTION SOT, HIGH-FIDELITY I2V ENGINE & END-TO-END CODEMAP (VOX V3)

> **Mã văn bản**: `PLAN-VOX-V3-REFORM-20261030`  
> **Trạng thái**: Đã phê duyệt (Approved by User) — Mở rộng Codemap Chuyên sâu  
> **Phạm vi tác động**: Toàn bộ hệ thống AI Video Factory (Pipeline Stages S01–S11, Vox Engine v3, Notion SoT, Remotion Renderer, B11 Dreaming Loop)

---

## 📑 MỤC 1: BÁO CÁO PHÁP Y THỰC CHỨNG & NGUYÊN NHÂN GỐC RỄ (ROOT-CAUSE AUDIT)

### 1. Phẫu thuật Tử huyệt `clip_scene_06` (Vì sao Slideshow & Lệch chi tiết?)
Qua kiểm tra pháp y file `prompts_forge.json` và `flow_video_manifest.json` của Scene 06 tập `KR_EP0003`, phát hiện 4 lỗi kỹ thuật nghiêm trọng:
1. **Lỗi Quái thai từ khóa (Chimeric Keyword Mashup)**: Prompt vừa gọi con dấu đỏ (`crimson forensic seal stamp`), vừa mô tả *"kẹp chặt hàm"* (`locks jaws shut`), vừa xuất hiện *"vạch chia thước kẹp vernier"* (`vernier scale aligns`). Việc ghép nối mù quáng từ khóa của Thước kẹp ($H_2$) vào Con dấu ($H_1$) khiến AI Veo bị loạn thị giác và sinh hình dị dạng.
2. **Lỗi Tọa độ mù (Cartesian Coordinate Blindness)**: Prompt nhồi tọa độ toán học `(X:50%, Y:36%)` và mốc thời gian vi mô `0.600s - 1.000s`. Các mô hình video diffusion (Veo/Omni) không hiểu tọa độ Descartes, coi đây là nhiễu và bỏ qua chuyển động.
3. **Lỗi Đóng băng chết chóc (Dead-Stop Freeze 7.7s)**: Video dài 10.03s nhưng prompt chỉ định hành động từ 0s–2.3s, sau đó lệnh *"All objects permanently locked in spatial anchor for remaining 3.740s"*. Kết quả: gần 8 giây cuối khung hình bị đơ cứng 100%, gây cảm giác slideshow PowerPoint.
4. **Lỗi Xung đột Âm bản / Dương bản**: Chủ thể là văn bản tin tức (`국제뉴스는 마감임박`) nhưng Negative Prompt lại cấm mọi chữ và số (`no writing or readable digits`), khiến AI sinh ra mẩu giấy xám mờ không nội dung.

### 2. Hiện Trạng Nạp Tri Thức (Notion vs. Local Parity & Token Bloat)
1. **Kho Prompt Bị Phình To**: 14 files cấu hình trong `config/prompts/` chiếm tới **106,401 ký tự (~26,600 tokens)**.
2. **Xung Đột Phong Cách Cũ - Mới**: File Notion `b3_director_prompt.md` là Hollywood 3D (Fincher style, 3D rooms), file `b35_visual_rules.md` là phông tím Magenta `#FF00FF`. Trong khi Vox Engine v3 chuẩn là Bàn giấy báo `#f4ece1`, cutout nền trắng `#FFFFFF` và cấm tuyệt đối 3D rooms.
3. **5 File Mồ Côi Ngoài Notion**: `vox_b3_director_image_prompt.md`, `vox_b6_flow_video_prompt.md`, `vox_docudrama_engine.md`, `vox_multi_motion_engine.md`, `style-config.yaml` chưa được quản lý trên Notion SoT.
4. **Hardcode Triệu Chứng Cục Bộ**: `kinetic_sub_director.py` chứa từ điển hardcode tiếng Hàn `KOREAN_ACT_I_SCENE_PROFILES` cho riêng `KR_EP0003`, vi phạm Rule 128 và Rule 139.

---

## 🏛️ MỤC 2: QUY HOẠCH LẠI KHO TRI THỨC TRÊN NOTION SOT (NOTION HUB RESTRUCTURING)

Tái cấu trúc toàn bộ kho tri thức trên Notion SoT thành **4 Hub tường minh**, đồng thời di dời các file legacy vào kho lưu trữ:

- **Hub 1: Content Engine Hub**: Quản lý `b1_strategy` (ngưỡng điểm 8.0, 7 Pillars) và `b2_editorial` (kịch bản 5 Beat Docudrama).
- **Hub 2: Media Production Hub**: Quản lý `b3_vox_director` (chuẩn màu `#F4F1EA`, `#FFFFFF` alpha, 5 Archetypes) và `b6_flow_motion` (Stop-motion $H_1 \to H_7$).
- **Hub 3: Distribution Hub**: Quản lý `b10_seo` (Metadata, Thumbnail text $\ge 40\%$, Chapters).
- **Hub 4: Active Instinct Memory Vault**: Quản lý trang `active_instincts` với tối đa 5 slots bài học.
- **Archive / Legacy Vault**: Di chuyển toàn bộ các file Hollywood 3D và phông tím Magenta vào đây để vô hiệu hóa hoàn toàn.

---

## ⚙️ MỤC 3: CỔNG NẠP TRI THỨC THỐNG NHẤT (`core/skill_gateway.py`) & GIT-SOT PARITY

1. **Nguyên lý Prompts-as-Code (Git-SoT)**:
   - Pipeline khi render video **CHỈ ĐỌC TRỰC TIẾP TỪ THƯ MỤC GIT NỘI BỘ (`config/prompts/`)**.
   - Tuyệt đối không gọi API ra ngoài (Notion/Google) trong lúc đang render để triệt tiêu 100% rủi ro mạng, rate limit và độ trễ.
   - Notion chỉ là **Giao diện soạn thảo của Con người (Human Staging)**, được đồng bộ bất đồng bộ về Git qua `scripts/ag_notion_bridge.py`.
2. **Cơ chế JIT Micro-Engine Injection ($\le 2,000\text{ tokens/call}$)**:
   - Mỗi Stage chỉ nạp đúng 1 Micro-Engine tương ứng (Stage 1 nạp B1; Stage 3 nạp B2; Stage 5 nạp B3 Vox; Stage 9 nạp B6 Flow).
   - Cắt giảm $> 88\%$ tải lượng token rác, triệt tiêu hiện tượng "Lost-in-the-Middle".
3. **In-Memory Lookup Table**:
   - Chuyển `cinematic_tokens_dictionary.json` (16.7KB) thành module Python tra cứu in-memory; cấm nhồi JSON thô vào prompt.

---

## ⏱️ MỤC 4: BỘ PHÂN BỔ THỜI LƯỢNG & DÀN Ý FRAME TTS (`core/pacing_budgeter.py`)

1. **Tốc Độ Nói Tự Nhiên Theo Thị Trường**:
   $$\text{KR: } 5.8 - 6.2\text{ syl/s} \quad | \quad \text{JP: } 6.5 - 7.0\text{ morae/s} \quad | \quad \text{EN: } 3.0 - 3.4\text{ từ/s} \quad | \quad \text{VN: } 3.4 - 3.8\text{ từ/s}$$
2. **Dàn Ý Frame Dự Kiến (Projected Frame Outline)**:
   - Sinh trước mốc `exact_duration_sec` và `target_frames_30fps` cho từng scene trước khi gọi bất kỳ prompt thị giác nào.
   - Đảm bảo Act I của `KR_EP0003` chuẩn dài **~29.5s – 30.5s** (thay vì 38.0s), loại bỏ hoàn toàn 1.5s đơ cứng cuối cảnh.

---

## 🔍 MỤC 5: BỘ TRÍCH XUẤT BẰNG CHỨNG THỰC CHỨNG (CLAIM-TO-EVIDENCE BINDING - RULE 141)

1. **Thanh Lọc Hardcode**: Xóa sạch từ điển `KOREAN_ACT_I_SCENE_PROFILES` trong `kinetic_sub_director.py`.
2. **5 Archetypes Bằng Chứng Thực Tế Động**:
   - `LegalSanctionArchetype`: Quyết định xử phạt, mộc đỏ cơ quan quản lý, trát tòa.
   - `CorporateEntityArchetype`: Giấy phép kinh doanh, hợp đồng thuê nhà, sơ đồ sở hữu.
   - `ParadoxClaimArchetype`: Tờ rơi quảng cáo bóng bẩy bị dập mộc đỏ "HỦY BỎ / GIAN DỐI", lật mở hợp đồng con ẩn giấu.
   - `QuantitativeMetricArchetype`: Biểu đồ cột sụp giảm, thước kẹp vernier siết con số tài chính.
   - `InvestigativeMediaArchetype`: Tiêu đề phóng sự điều tra, kính lúp soi thấu điều khoản vi mô.
3. **Quy Tắc Khóa Ngữ Nghĩa**: Hero Object bắt buộc phải là bằng chứng vật lý của câu nói. Chấm dứt vĩnh viễn việc vẽ kéo tỉa lông mày, thước cuộn, con lăn, vết đế giày ngẫu nhiên.

---

## 🎬 MỤC 6: TÁI CẤU TRÚC PROMPT IMAGE-TO-VIDEO (I2V) — NÂNG CẤP ĐỘNG LỰC HỌC VOX

1. **Chuyển Từ Tọa Độ Descartes Sang Động Lực Học Tự Nhiên**:
   - Cấm: `(X:50%, Y:36%)`, `[X:36%-64%, Y:46%-74%]`, `0.600s - 1.000s`.
   - Chuẩn hóa:
     ```text
     [CAMERA & ENVIRONMENT]: Top-down macro flat-lay perspective on aged archival newsprint (#F4F1EA).
     [ACTION PHASE (0.2s - 0.4s)]: A heavy red wooden seal stamp drops briskly from the top frame, striking down with a firm mechanical thud onto the unpermitted rental contract.
     [PHYSICAL REACTION & RESIDUE]: Paper fibers visibly indent under the impact; crimson ink splatters subtly and registers an indelible red official sanction seal on the document.
     [HOLD & LIVING TEXTURE]: The stamp lifts away cleanly, revealing the crisp crimson mark. The document holds firmly in place with subtle living paper grain flutter and micro shadow breathing at 12fps (on twos). Zero 3D camera drift, zero static freeze.
     ```
2. **Nguyên Tắc Đơn Nhất Tương Tác**: Mỗi scene chỉ áp dụng duy nhất 1 cơ chế va chạm ($H_1$ Dập dấu, hoặc $H_2$ Thước kẹp, hoặc $H_3$ Kéo cắt). Không bao giờ trộn thước kẹp với con dấu.
3. **Nhịp Thở Thớ Giấy 12fps (Living Hold)**: Duy trì vi rung thớ giấy $\le 2\text{px}$ và bóng đổ tự nhiên ở 12fps cho đến hết thời lượng của frame. Chấm dứt đóng băng khung hình (freeze frame).

---

## 🧠 MỤC 7: QUY HOẠCH VỊ TRÍ TƯỜNG MINH & CODEMAP ĐẤU NỐI CƠ CHẾ HỌC TOÀN TRÌNH (END-TO-END CODEMAP & DREAMING PIPELINE)

> Đây là kiến trúc xương sống đảm bảo tri thức và bài học từ kết quả thực chiến (YouTube Analytics, Retention, Drop-offs, QA Audits) được đấu nối khép kín và tự động nâng cấp ngược vào từng Stage của Pipeline mà **không gây phình context hay xung đột luật**.

### 1. Bảng Quy Hoạch Vị Trí Vật Lý & Logic Tường Minh (Explicit Physical Layout)

| Thành phần | Vị trí đĩa cứng / URL | Trách nhiệm kiến trúc | Cơ chế đồng bộ |
| :--- | :--- | :--- | :--- |
| **Notion SoT Root** | `https://notion.so/Skill-AI-ac901989...` | Giao diện quản trị tri thức của Con người | Web / Mobile UI |
| **Notion Hub 1: Content** | Sub-page `b1_strategy`, `b2_editorial` | Quy chuẩn Kịch bản & Chiến lược đề tài | Pull/Push qua bridge |
| **Notion Hub 2: Media** | Sub-page `b3_vox_director`, `b6_flow_motion` | Quy chuẩn Thị giác Vox v3 & Động lực học | Pull/Push qua bridge |
| **Notion Hub 3: Growth** | Sub-page `b10_seo` | Quy chuẩn Thumbnail CTR & YouTube Chapters | Pull/Push qua bridge |
| **Notion Hub 4: Instincts**| Sub-page `active_instincts` | Lưu trữ tối đa 5 slots bài học đã qua kiểm duyệt | Cập nhật tự động sau duyệt |
| **Git Prompts Source** | [`config/prompts/*.md`](file:///C:/Users/hunghd2/Documents/antigravity/AI%20Video%20Factory/config/prompts/) | File Markdown nội bộ trong Git repo (Git-SoT) | Commit Git SHA |
| **Local Snapshot Cache** | [`data/notion_audit/skills_snapshot.json`](file:///C:/Users/hunghd2/Documents/antigravity/AI%20Video%20Factory/data/notion_audit/skills_snapshot.json) | Bộ nhớ đệm JSON 100% bit-for-bit parity | Cache offline |
| **Runtime Gateway** | [`core/skill_gateway.py`](file:///C:/Users/hunghd2/Documents/antigravity/AI%20Video%20Factory/core/skill_gateway.py) | Cổng JIT nạp micro-engine cho từng stage | In-memory Python |
| **Audit DB** | `data/audit.db` (SQLite) | Lưu vết audit, metric vi phạm, tần suất lỗi | SQLite transaction |
| **B11 Telemetry State** | `data/b11_state.json` | Lưu trữ chỉ số 4-Tab YouTube Studio sau 48h | JSON atomic write |
| **Active Instincts File**| [`config/active_instincts.json`](file:///C:/Users/hunghd2/Documents/antigravity/AI%20Video%20Factory/config/active_instincts.json) | 5 slots bản năng thực chiến nạp trực tiếp vào prompt | Schema-validated JSON |

---

### 2. Ma Trận Điều Hướng Bài Học Từng Stage (Signal-to-Stage Routing Matrix)

Mọi chỉ số telemetry thực chiến thu hoạch từ YouTube Studio và các bài kiểm toán được định tuyến chính xác đến file code chịu trách nhiệm:

| Chỉ số / Vấn đề thực chiến | Ngưỡng kích hoạt | Module thụ hưởng trực tiếp | File mã nguồn xử lý | Hành vi tự điều chỉnh (Parameter Adaptation) |
| :--- | :--- | :--- | :--- | :--- |
| **Drop-off 0–15s** (Tụt người xem mở đầu) | Tỷ lệ giữ chân $< 65\%$ tại giây 15 | **Stage 3 (Story B2)** | `app/services/story_engine_b2.py` | Giảm thời lượng Cold Strike xuống $\le 15s$, đưa con số Grounding lên ngay câu thứ nhất. |
| **Click-Through Rate (CTR)** | CTR 28h đầu $< 5.5\%$ | **Stage 11 (SEO B10) & S10 Thumbnail** | `app/services/seo_package_forge.py` | Ép tỷ lệ diện tích Typography trên thumbnail $\ge 45\%$, đổi cấu trúc tiêu đề sang thể đối kháng. |
| **Mid-Video Slump** (Tụt dốc giữa video) | Drop-off $> 10\%$ trong Beat 3 | **Stage 5 (Director B3)** | `stages/s05_director_plan.py` | Chèn một nhịp ngắt thị giác (Pattern Interrupt): Kéo cắt giấy ($H_3$) hoặc Kính lúp soi cận cảnh ($H_5$) ở giây thứ 50%. |
| **Karaoke Timing Drift** (Lệch phụ đề) | Độ trôi lệch $> 100\text{ms}$ | **Stage 4 (Pacing)** | `core/pacing_budgeter.py` | Tự động hiệu chỉnh tham số `speech_rate_target` (ví dụ từ 5.8 syl/s lên 6.0 syl/s cho phát thanh viên đọc nhanh). |
| **Visual Inconsistency** (Lệch chi tiết) | Điểm Visual Critic $< 8.5$ | **Stage 5 & 9 (I2V Motion)** | `app/services/semantic_evidence_extractor.py` | Ép buộc áp dụng 1 trong 5 Archetypes, xóa bỏ mọi đạo cụ không có căn cứ pháp lý trong kịch bản. |

---

### 3. Khế Ước Dữ Liệu `active_instincts.json` (Slot-Based Schema)

File [`config/active_instincts.json`](file:///C:/Users/hunghd2/Documents/antigravity/AI%20Video%20Factory/config/active_instincts.json) lưu trữ đúng 5 slots bản năng:

```json
{
  "version": "2.0.0",
  "max_slots": 5,
  "updated_at": "2026-10-30T11:40:00Z",
  "slots": [
    {
      "slot_id": 1,
      "target_stage": "s03_script",
      "rule_code": "INSTINCT_COLD_STRIKE_METRIC_FIRST",
      "parameter_patch": {"first_metric_max_word_offset": 8},
      "rationale": "YouTube retention 0-15s drops when metric appears after word 15",
      "applied_count": 12,
      "last_triggered": "2026-10-29T18:00:00Z"
    },
    {
      "slot_id": 2,
      "target_stage": "s04_pacing",
      "rule_code": "INSTINCT_KR_NEWS_TEMPO_CALIBRATION",
      "parameter_patch": {"ko_speech_rate": 5.85},
      "rationale": "InJoonNeural voiceover requires 5.85 syl/s to prevent dead silence",
      "applied_count": 8,
      "last_triggered": "2026-10-30T09:00:00Z"
    },
    {
      "slot_id": 3,
      "target_stage": "s05_director",
      "rule_code": "INSTINCT_ARCHETYPE_SANCTION_STAMP_HOLD",
      "parameter_patch": {"living_texture_fps": 12, "max_dead_freeze_sec": 0.4},
      "rationale": "Causal handoff H1 must maintain living paper grain flutter at 12fps",
      "applied_count": 15,
      "last_triggered": "2026-10-30T10:30:00Z"
    },
    {
      "slot_id": 4,
      "target_stage": "s11_seo",
      "rule_code": "INSTINCT_THUMBNAIL_TEXT_AREA_RATIO",
      "parameter_patch": {"min_text_area_pct": 42},
      "rationale": "Mobile view CTR increases by 18% when title text occupies >= 42%",
      "applied_count": 6,
      "last_triggered": "2026-10-28T12:00:00Z"
    },
    {
      "slot_id": 5,
      "target_stage": "s05_director",
      "rule_code": "INSTINCT_ANTI_CARTESIAN_COORDINATE_IN_I2V",
      "parameter_patch": {"ban_cartesian_regex": true, "enforce_kinetic_verbs": true},
      "rationale": "Video diffusion models hallucinate on (X,Y) coordinates; require natural verbs",
      "applied_count": 22,
      "last_triggered": "2026-10-30T11:00:00Z"
    }
  ]
}
```

---

## 🎨 MỤC 8: QUY TRÌNH HẬU KỲ REMOTION (LÀM SAU KHI XONG VIDEO)

1. **Khớp Nối Video Clips**: Remotion nhận các clips đã render đúng theo Frame Outline của Mục 4.
2. **Lồng Voiceover & Whisper Alignment**: Trích xuất timestamp chính xác từng từ của file âm thanh TTS (`ko-KR-InJoonNeural`).
3. **Phủ Phụ Đề Karaoke Vox**: Phụ đề chữ trắng viền đen tại vùng an toàn 20% đáy màn hình, highlight vàng neon theo đúng từng từ (độ trôi lệch $0\text{ms}$ drift).
4. **Chèn SFX Foley Cơ Học Tương Ứng**: Đồng bộ tiếng dập mộc (*thud*), tiếng kéo rách giấy (*rip*), tiếng thước kẹp (*click*) khớp với va chạm thị giác của video.

---

## 🗺️ LỘ TRÌNH THỰC THI NGUYÊN TỬ (ATOMIC 5-PHASE EXECUTION ROADMAP)

| Giai đoạn | Hạng mục thực hiện chính | File can thiệp | Tiêu chí nghiệm thu (Gate) |
| :---: | :--- | :--- | :--- |
| **P1** | **Skill Gateway & Notion Archiving** | `core/skill_gateway.py`, `skills_snapshot.json`, `config/prompts/` | 100% test import PASS, cách ly file legacy, token budget $\le 2,000$ |
| **P2** | **TTS Pacing & Frame Budgeter** | `core/pacing_budgeter.py`, `stages/s04_storyboard.py` | Sinh Dàn ý Frame chuẩn cho KR (5.8 syl/s), EP0003 Act I = ~30s |
| **P3** | **Semantic Evidence Extractor** | `app/services/semantic_evidence_extractor.py`, `kinetic_sub_director.py` | Xóa sạch hardcode tiếng Hàn, 5 Archetypes sinh đúng 100% |
| **P4** | **Natural Kinetic I2V Prompt Engine** | `stages/s05_director_plan.py`, `app/services/prompt_forge.py` | Loại bỏ 100% tọa độ Descartes, tái tạo Scene 1–8 đạt chuẩn stop-motion |
| **P5** | **Remotion Karaoke Sync & Codemap Dreaming** | `build_remotion_props.py`, `config/active_instincts.json`, tests | 31/31 unit tests PASS, Alibaba OCR PASS (0 Critical), 0ms drift Karaoke |
