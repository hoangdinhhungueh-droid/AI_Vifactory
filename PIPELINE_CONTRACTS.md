# 📐 Pipeline Interface Contracts & Code Layout (ISO-Grade B1–B11)

> **MỤC ĐÍCH**: Bản đặc tả kỹ thuật sống về Khế ước Dữ liệu (IN/OUT Data Contracts) giữa các block trong Pipeline và Danh mục cấu trúc mã nguồn trên VPS (`/root/video_factory`).
> Mọi thay đổi về Schema dữ liệu bắt buộc phải được kiểm thử qua `tests/ci_neighbor_tester.py` (Rule 447).
>
> 🛡️ **QUY TẮC BẤT BIẾN (RULE 128 - ANTI-SEMANTIC-BIAS)**:
> Toàn bộ Data Schema trong tài liệu này được định dạng theo **Generic Contract Pattern** (Khuôn mẫu Hợp đồng Tổng quát) với Placeholders và Type Annotations. CẤM TUYỆT ĐỐI Agent gán ép hoặc giả định các giá trị mẫu cho một chủ đề cụ thể (như Lehman Brothers, tài chính, chứng khoán...). Mọi Episode mới thuộc bất kỳ đề tài nào (công nghệ, lịch sử, tội phạm, kinh tế, địa chính trị) ở mọi ngôn ngữ (`EN`, `VN`, `JA`, `KO`...) đều áp dụng cấu trúc này với nội dung phát sinh độc lập.

---

## 🔄 I. KHẾ ƯỚC DỮ LIỆU LIÊN KHỐI (INTER-BLOCK DATA CONTRACTS)

### 0. Khế Ước Điều Phối Lịch Tuần (Weekly Staggered Market Production Scheduler — Crash Protection Gate)
* **File lưu trữ & Module**: `app/services/market_scheduler.py` & `scripts/run_trend_pipeline.py`
* **Mục đích**: Triệt tiêu 100% rủi ro nghẽn cổ chai CPU/RAM/API và crash hạ tầng VPS khi Human Gate 1 chuyển sang chế độ Informative Broadcast tự động, bằng cách cố định mỗi ngày chỉ sản xuất duy nhất 1 video cho 1 thị trường.
* **Ma Trận Lịch Tuần (Neo Cứng Múi Giờ Việt Nam UTC+7 / Asia/Ho_Chi_Minh)**:
  | Thứ (VN Time UTC+7) | Python Weekday (`date.weekday()`) | Thị Trường Được Phép Sản Xuất | Nhiệm Vụ Thực Thi |
  | :--- | :---: | :---: | :--- |
  | **Thứ Hai (Monday)** | `0` | **EN** | Pipeline B1 ➔ B1.5 ➔ B2 ➔ B3 ➔ B10 (Kênh English) |
  | **Thứ Ba (Tuesday)** | `1` | **KR** | Pipeline B1 ➔ B1.5 ➔ B2 ➔ B3 ➔ B10 (Kênh Korean) |
  | **Thứ Tư (Wednesday)** | `2` | **JP** | Pipeline B1 ➔ B1.5 ➔ B2 ➔ B3 ➔ B10 (Kênh Japanese) |
  | **Thứ Năm (Thursday)** | `3` | **EN** | Pipeline B1 ➔ B1.5 ➔ B2 ➔ B3 ➔ B10 (Kênh English) |
  | **Thứ Sáu (Friday)** | `4` | **KR** | Pipeline B1 ➔ B1.5 ➔ B2 ➔ B3 ➔ B10 (Kênh Korean) |
  | **Thứ Bảy (Saturday)** | `5` | **JP** | Pipeline B1 ➔ B1.5 ➔ B2 ➔ B3 ➔ B10 (Kênh Japanese) |
  | **Chủ Nhật (Sunday)** | `6` | **NGHỈ** | Dọn rác cache `/tmp`, xóa stale locks, B11 Analytics Dreaming |
* **Quy tắc Bất Biến (Scheduler Invariants)**:
  1. **Strict Calendar Isolation**: Nếu một ngày gặp sự cố (API lỗi, không cào được đề tài), ngày hôm sau vẫn chạy đúng thị trường của ngày đó, không dồn ứ làm trễ lịch kênh khác. Cho phép chạy bù thủ công qua cờ CLI `--market <MKT>`.
  2. **Boundary Precision**: Crontab chạy `0 23 * * *` (23:00 UTC) tự động quy đổi thành 06:00 AM VN của ngày tiếp theo. Cấm dùng UTC naive datetime.

### 1. Khối B1 (Trend Discovery) ➔ Khối B1.5 (Competitor Recon)
* **File lưu trữ**: `/var/vf/pending_tasks/<task_id>.json (kèm đồng bộ Notion Trend Brain DB)`
* **Data Schema (Generic Specification)**:
  ```json
  {
    "task_id": "<MARKET>_EP<0000>_<topic_slug>",
    "market": "<MARKET_CODE: EN | VN | JA | KO | ...>",
    "raw_term": "<PRIMARY_SEARCH_TOPIC_OR_ENTITY_NAME>",
    "viability_score": "<FLOAT: 0.0 - 100.0>",
    "factsheet": {
      "verified_date": "<YYYY-MM-DD | Historical Era Anchor>",
      "key_entities": ["<Entity_1>", "<Entity_2>", "<Entity_3>"],
      "core_mechanism": "<Core conflict, technical mechanism, or systemic event>",
      "wikipedia_ground_truth_url": "https://<lang>.wikipedia.org/wiki/<Verified_Article_Slug>"
    },
    "niche_angle_brief": "<Specific unexplored narrative angle with zero competitor coverage>",
    "story_direction_5_arcs": [
      "<Arc 1: Hook/Contradiction>",
      "<Arc 2: Buildup/False Narrative>",
      "<Arc 3: Paper Trail/Investigation>",
      "<Arc 4: Climax/Smoking Gun>",
      "<Arc 5: Resolution/Modern Reflection>"
    ]
  }
  ```
* **Quy chuẩn Field Ràng buộc**:
  - `task_id`: Bắt buộc tuân thủ regex `^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$`. Cấp phát tự động tịnh tiến theo kho số thực tế trên VPS, cấm fallback cứng.
  - `viability_score`: Tính toán từ dữ liệu Google Trends RSS live & Wikipedia Anchor, cấm hardcode giả định.
  - `content_theme`: Gán nhãn 1 trong 11 Content Pillars chính thống, bao gồm Pillar 11 (Everyday Consumer Injustice & Institutional Traps: `consumer_injustice_institutional_trap`).
  - `editorial_archetype`: Hỗ trợ `social_reality_docudrama` cho các đề tài bẫy tiêu dùng đời thường, tuân thủ nghiêm ngặt Anti-Tutorial SEO Packaging Mandate (Rule 130: cấm mọi tiền tố 'How to / Cách / Mẹo / 5 bước / 환불하는법'; bắt buộc áp dụng công thức va chạm điện ảnh).

---

### 2. Khối B1.5 (Competitor Recon) ➔ Khối B2 (Story Engine)
* **File lưu trữ**: `/var/vf/episodes/<task_id>/competitor_intel_card.json`
* **Data Schema (Cấu trúc 2 tầng chuẩn: Root Benchmarks & Deep Narrative Anatomy)**:
  ```json
  {
    "task_id": "<MARKET>_EP<0000>_<topic_slug>",
    "analyzed_videos_count": "<INTEGER: Number of competitor videos analyzed, e.g. 5-15>",
    "competitor_benchmarks": [
      {
        "channel": "<COMPETITOR_CHANNEL_NAME>",
        "channel_id": "<YOUTUBE_CHANNEL_ID>",
        "subscriber_count": "<INTEGER: e.g. 2500>",
        "views": "<INTEGER_VIEWS>",
        "vph": "<FLOAT: views per hour, e.g. 450.25>",
        "v_s_ratio": "<FLOAT: views / subscribers, e.g. 42.5>",
        "outlier_score": "<FLOAT: virality outlier score>",
        "selection_group": "<small_channel_outlier_surge | all_time_top_velocity | recent_90_365_days>",
        "duration": "<INTEGER_SECONDS>",
        "hook_pacing": "<fast | moderate | slow>"
      }
    ],
    "gap_signals": {
      "avg_views": "<INTEGER_AVG_VIEWS>",
      "top_opportunity": "<Core underserved topic or content gap identified>"
    },
    "competitor_narrative_anatomy": {
      "competitor_act_breakdown": [
        {
          "competitor": "<NAME>",
          "structure": "<Chronological | Problem-Solution | Investigative>",
          "weakness": "<Specific analytical flaw or surface-level coverage>"
        }
      ],
      "competitor_secret_sauce": "<High-retention technique used by rivals>",
      "audience_core_frustrations": [
        "<Audience pain point 1 extracted from top comments>",
        "<Audience pain point 2 extracted from top comments>"
      ],
      "fatal_explanatory_vacuum": "<Critical knowledge gap completely missed or glossed over by existing videos>",
      "our_10x_pivot_angle": "<Our distinctive narrative breakthrough angle that definitively solves the vacuum>",
      "transposition_opportunities": {
        "proven_structural_vehicle": "<Underlying psychological format/hook structure, e.g. Unit Economics of Operating an Elite Facility>",
        "recommended_target_niches": ["<Cross-niche opportunity 1>", "<Cross-niche opportunity 2>"]
      },
      "ai_slop_redlines": [
        "<Specific generic phrases or bot cliches flagged by audience in this niche>"
      ],
      "audience_wishlist_topics": [
        "<Specific future video topic or investigation explicitly requested by viewers>"
      ]
    },
    "transposition_opportunities": {
      "proven_structural_vehicle": "<Underlying psychological format/hook structure>",
      "recommended_target_niches": ["<Cross-niche opportunity 1>", "<Cross-niche opportunity 2>"]
    },
    "ai_slop_redlines": ["<Audience-mined banned cliches>"],
    "audience_wishlist_topics": ["<Viewer-requested upcoming topics>"]
  }
  ```

---

### 2.1. Khối B1.5.5 (Search Grounding & Fact Verification Gate) ➔ Khối B2 (Story Engine)
* **File lưu trữ**: `/var/vf/episodes/<task_id>/grounding_intel.json`
* **Mục đích**: Chặn đứng 100% rủi ro hallucination về số liệu tài chính, ngày tháng, thương vong hoặc sự kiện chính trị nhạy cảm trước khi viết kịch bản. Sử dụng Google Search Grounding (REST API `tools: [{"googleSearch": {}}]`) trích xuất sự kiện thực tế có nguồn dẫn chứng minh bạch.
* **Data Schema (Generic Specification)**:
  ```json
  {
    "topic": "<PRIMARY_SEARCH_TOPIC_OR_ENTITY_NAME>",
    "rejected": "<BOOLEAN: false if credible, true if pure rumor/satire/unsubstantiated>",
    "reject_reason": "<STRING: Explanation if rejected, empty string if passed>",
    "claims": [
      {
        "claim": "<Concise, specific factual claim with concrete metric/action>",
        "source": "<Name of reporting outlet or agency, e.g. Reuters, Bloomberg, SEC filings, Nikkei, official ministry>",
        "source_url": "<Optional URL or domain if available>",
        "date": "<YYYY-MM-DD>",
        "confidence": "<verified | reported | speculative>",
        "mechanism": "<legal | military | commercial | financial | technical | regulatory>"
      }
    ],
    "grounding_chunks": [
      {
        "title": "<Source page title>",
        "uri": "<Source web URL>"
      }
    ],
    "search_queries": [
      "<Web search query executed by Grounding model>"
    ],
    "has_live_search": "<BOOLEAN: true if live web search succeeded, false if degraded fallback>"
  }
  ```
* **Quy chuẩn Verification Gate (Rule 121 & Rule 127)**:
  1. `rejected == false`: Chủ đề không bị mô hình đánh cờ là tin đồn hoặc phỏng đoán vô căn cứ.
  2. `claims`: Tối thiểu 1 factual claim đạt cấp độ `confidence: "verified"` (được xác thực bởi cơ quan chuyên môn/hồ sơ pháp lý hoặc nhiều hãng tin uy tín).
  3. `Fast-Fail Rotation`: Nếu không thỏa mãn Gate, pipeline B1.5.5 lập tức loại bỏ chủ đề, xoay vòng sang ứng viên tiếp theo trong danh sách cào trend.
  4. `Prompt Anchoring`: Khi đạt Gate, các claims được chuyển hóa thành bảng sự thật (`REAL-WORLD GROUNDED FACTS TABLE`) nhúng thẳng vào prompt B2 với quy tắc ràng buộc ngôn ngữ 3 cấp:
     - `VERIFIED`: Được phép khẳng định trực diện như sự thật khách quan.
     - `REPORTED`: Bắt buộc dẫn nguồn phân bổ ("Theo báo cáo từ...", "Ghi nhận của...").
     - `SPECULATIVE`: Bắt buộc đóng khung giả định ("Trong kịch bản dự phóng...", "Nếu các ước tính tiếp tục...").

---

### 3. Khối B2 (Story Engine) ➔ Khối B2.5 (Spoken VO) ➔ Khối B2.6 (Audio Spine) ➔ Khối B3 (Director Plan)
* **Quy chuẩn Hollywood Movie Standard**:
  1. **B2.5 Spoken VO Adaptation**: Chuyển thể 5-Beat Story thành các câu thoại ngắt hơi nhịp thở (`spoken_script.txt` & `spoken_sentences.json`). Mỗi câu tối đa ~15 từ (~3-5s), trần thời lượng tổng $\le 15$ phút, qua kiểm toán phản biện `adversarial_audit_spoken_script` đạt điểm $\ge 7.5/10$.
  2. **B2.6 Master Audio Spine (Edge-TTS)**: Sinh file âm thanh `tts_out.mp3` và bóc tách timecode mili-giây chính xác (`start_ms`, `end_ms`, `duration_frames` tại 30fps) cho từng câu thoại trong `spoken_sentences.json`, xuất phụ đề `subtitles.srt`.
  3. **B3.0 Hollywood Visual Director Plan**: Đạo diễn hình ảnh nhận danh sách câu thoại đã có timecode thật. Toàn bộ các cảnh hình ảnh được khóa 1:1 theo câu thoại (`narration == sent["text"]`, `duration_frames == sent["duration_frames"]`). Tuyệt đối 0% bịa thoại hay phân cảnh text mù.
* **File lưu trữ**:
  - `/var/vf/episodes/<task_id>/story.txt` (Kịch bản 5 Beat)
  - `/var/vf/episodes/<task_id>/spoken_script.txt` (Kịch bản đọc thoại)
  - `/var/vf/episodes/<task_id>/spoken_sentences.json` (Danh sách câu thoại kèm timecode ms và frames)
  - `/var/vf/episodes/<task_id>/tts_out.mp3` (Audio spine chuẩn)
  - `/var/vf/episodes/<task_id>/subtitles.srt` (Phụ đề đồng bộ mili-giây)
  - `/var/vf/episodes/<task_id>/director_plan.json` (Phân cảnh hình ảnh khóa audio)
* **Data Schema (`spoken_sentences.json`)**:
  ```json
  [
    {
      "sentence_id": "sent_<001>",
      "beat_index": "<INTEGER: 1-5>",
      "text": "<SPOKEN_VERBATIM_TEXT>",
      "start_ms": "<INTEGER: Millisecond start time>",
      "end_ms": "<INTEGER: Millisecond end time>",
      "duration_sec": "<FLOAT: Duration in seconds>",
      "duration_frames": "<INTEGER: Duration in frames at 30fps>"
    }
  ]
  ```

---

### 4. Khối B3 (Director Plan) ➔ Khối B3.5 (Prompt Forge)
* **File lưu trữ**: `director_plan.json` ➔ `prompts_forge.json (và prompts.json tương thích ngược)`
* **Quy chuẩn**: Toàn bộ visual prompts viết bằng tiếng Anh, gắn `[STYLE MANDATE]`, `[MARKET & ETHNIC ANCHOR]`, `[MARKET & ENVIRONMENT ANCHOR]`, `[ERA ANCHOR]`, `[STRICT NEGATIVE PROMPT]`.
* **Pacing & Asset Optimization (130-160 Scenes & 15-20 Clustered BGs)**:
  - **Pacing**: Chuẩn hóa nhịp 130–160 scenes động (~4–6s/scene) dàn đều 5 Beats, đẩy nhịp dựng Fincher kịch tính.
  - **Clustered BG Reuse**: B4 sinh tối ưu hóa 15–20 Backgrounds độc bản (`bg_cluster_id`) được tái sử dụng linh hoạt xuyên suốt các scenes trong cùng một bối cảnh, triệt tiêu nguy cơ nghẽn API sinh ảnh hoặc kéo dài render.
  - **6 Canonical Camera Moves (Rule 128)**: `"slow_push_in"`, `"snap_zoom"`, `"cinematic_pan"`, `"macro_tilt"`, `"slow_pull_out"`, `"handheld_shake"`.
  - **Forensic Evidentiary Overlays (VOX Overhaul)**: `"evidence_3d_prop"` (Three.js procedural 3D hanko/dossier/ledger 12fps stop-motion), `"document_highlight"`, `"tactical_map"`, `"kinetic_counter"`, `"evidence_board"`, `"causal_flowchart"`, hoặc `null`.
  - **20 Google Flow Cinematic Tokens**: 
    + Camera Axis: `/straightdown`, `/groundlevel`, `/birdseye`, `/firstperson`, `/secondview`.
    + Framing/Scale: `/closecrop`, `/tightframe`, `/extremeclose`, `/thirdgrid`, `/innerframe`.
    + Lighting: `/darkmood`, `/edgelight`, `/spotbeam`, `/lightrays`, `/sunsetglow`, `/duskhour`.
    + Optical FX: `/filmlook`, `/highcontrast`, `/edgefade`, `/digitalglitch`.
* **Khế ước Bản Sắc Thị Trường (Rule 122 & 128 Generic Pattern)**:
  - Thị trường mục tiêu `<MARKET>` (`JP`, `KR`, `VN`, `EN`...) quyết định bắt buộc đặc điểm nhân chủng học của nhân vật FG (khuôn mặt, mắt, tóc, trang phục) và kiến trúc của BG (phòng họp, cao ốc, đường phố địa phương).
  - FG: CẤM TUYỆT ĐỐI thiên kiến da trắng/Âu Mỹ (Caucasian/Western bias) khi tạo nhân vật Á Châu.
  - BG: CẤM TUYỆT ĐỐI kiến trúc đô thị phương Tây khi bối cảnh diễn ra tại thị trường Á Đông.
* **Data Schema (`director_plan.json`)**:
  ```json
  {
    "director_profile": "<DIRECTOR_ARCHETYPE_NAME>",
    "target_scene_count": "<INTEGER: 130-160>",
    "bg_clusters_count": "<INTEGER: 15-20>",
    "scenes": [
      {
        "scene_id": "scene_<001>",
        "act_number": "<INTEGER: 1-5>",
        "beat_number": "<INTEGER: 1-5>",
        "beat_name": "<BEAT_NAME>",
        "bg_cluster_id": "bg_cluster_<01-20>",
        "background_reuse_key": "bg_<location_slug>",
        "foreground_reuse_key": "fg_<character_or_subject_slug>_<action_slug>",
        "camera_movement": "<slow_push_in | snap_zoom | cinematic_pan | macro_tilt | slow_pull_out | handheld_shake>",
        "cinematic_tokens": ["<TOKEN_1>", "<TOKEN_2>", "<TOKEN_3>"],
        "forensic_overlay": "<evidence_3d_prop | document_highlight | tactical_map | kinetic_counter | evidence_board | causal_flowchart | null>",
        "setting_description": "<ENVIRONMENT_DESCRIPTION_ENGLISH: Detailed setting and era background>",
        "character_description": "<CHARACTER_DESCRIPTION_ENGLISH: Detailed subject appearance, clothing, mood>",
        "visual_action": "<VISUAL_ACTION_ENGLISH: Subject pose and dynamic interaction>",
        "scene_sub_director_plan": {
          "schema_version": "scene_sub_director_plan.v3",
          "calculated_beat_count": "<INTEGER: 4-7>",
          "dominant_kinetic_families": ["<H1_IMPACT | H2_CONSTRAINT | H3_SEVER | H4_TETHER | H5_OPTICAL | H6_MARK | H7_DISPLACE>"],
          "object_roster": [
            { "id": "<STRING>", "label": "<STRING>", "material": "<STRING>", "mass_class": "<STRING>", "z_index": "<INTEGER: 1-5>", "role": "<STRING>" }
          ],
          "kinetic_couplings": [
            { "id": "<STRING>", "family": "<STRING>", "source_obj_id": "<STRING>", "target_obj_id": "<STRING>", "action_verb": "<STRING>", "contact_point": "<STRING>", "physical_reaction": "<STRING>", "residue": "<STRING>" }
          ],
          "dynamic_micro_beats": [
            { "beat_id": "<STRING>", "phase": "<STRING>", "time_window": "<STRING>", "coupling_id": "<STRING|null>", "action_description": "<STRING>", "handoff_to": "<STRING|null>" }
          ]
        }
      }
    ]
  }
  ```

---

### 4.5. Khế Ước Foley SFX & Tactile Audio Spine (Rule 120, Rule 128, Rule 134 & CANONICAL_SFX_REGISTRY)
* **Module Single Source of Truth (SoT)**: `app/services/sfx_registry.py`
* **Mục đích**: Triệt tiêu hoàn toàn cơ chế tạo asset âm thanh ad-hoc và xóa bỏ 100% các logic fallback mù quáng (`marker_stroke.mp3` / `paper_rustle.mp3`) gây biến dạng sound design và che giấu lỗi hệ thống.
* **Danh mục Đóng Kín 13 Cues Chuẩn Hóa (`CANONICAL_SFX_REGISTRY`)**:
  | Canonical Slug | File Vật Lý (`remotion/public/sfx/`) | Nhóm Âm Thanh | Ngữ Cảnh Kịch Bản Chuẩn |
  | :--- | :--- | :--- | :--- |
  | `counter_tick` | `counter_tick.mp3` | `INSTRUMENT_METER` | Đồng hồ đếm ngược, rollup số liệu forensic |
  | `document_table_thud` | `document_table_thud.mp3` | `PERCUSSION_IMPACT` | Đập tập tài liệu/hồ sơ dày xuống bàn gỗ |
  | `gauge_needle_hiss` | `gauge_needle_hiss.mp3` | `INSTRUMENT_METER` | Kim đồng hồ đo áp lực nhảy, thử nghiệm hóa chất/quang phổ |
  | `gavel_thud` | `gavel_thud.mp3` | `PERCUSSION_IMPACT` | Búa quan tòa giáng xuống bàn tuyên án |
  | `marker_stroke` | `marker_stroke.mp3` | `MARKER_GRAPHIC` | Bút dạ quang gạch dòng chữ chứng cứ |
  | `node_pop` | `node_pop.mp3` | `DIGITAL_NETWORK` | Mắt xích mạng lưới quan hệ/đồ thị xuất hiện |
  | `paper_crease_snap` | `paper_crease_snap.mp3` | `PAPER_TACTILE` | Mở gập bìa hồ sơ mật bifold dossier |
  | `paper_page_turn` | `paper_page_turn.mp3` | `PAPER_TACTILE` | Lật góc trang giấy tài liệu dog-ear peel |
  | `paper_rustle` | `paper_rustle.mp3` | `PAPER_TACTILE` | Sột soạt giấy tờ tài liệu điều tra chung |
  | `paper_slide` | `paper_slide.mp3` | `PAPER_TACTILE` | Trượt tài liệu nhanh trên mặt bàn gỗ phẳng |
  | `sonar_ping` | `sonar_ping.mp3` | `INSTRUMENT_METER` | Quét sóng âm rada/vệ tinh trinh sát |
  | `stamp_impact` | `stamp_impact.mp3` | `PERCUSSION_IMPACT` | Đóng mộc kiểm định (tiếng cộp vừa) |
  | `stamp_slam` | `stamp_slam.mp3` | `PERCUSSION_IMPACT` | Dập dấu triện đỏ/hanko/sawonjeung chính thức (tiếng nện mạnh) |
* **Kỷ Luật Thép Bất Biến (SFX Invariants)**:
  1. **Zero-Hallucination Gate (B3 Fail-Fast)**: Hàm `determine_spatial_physics()` và `build_unified_director_plan()` BẮT BUỘC chỉ được phát ra 13 slugs trên thông qua `resolve_semantic_foley()`. Mọi cue lạ sẽ kích hoạt `validate_director_sfx_compliance()` dừng pipeline ngay tại B3.
  2. **Zero-Silent-Fallback Mandate**: `build_remotion_props.py` và `remotion/src/index.tsx` CẤM TUYỆT ĐỐI tự ý gán fallback ngầm về `marker_stroke` hay `paper_rustle`. Thiếu file hoặc sai key phải kích hoạt lỗi pháp y hoặc bỏ qua âm thanh kèm cảnh báo console, không được phát sai âm thanh.
  3. **1:1 Physical Parity Gate**: 100% file mp3 phải tồn tại trên đĩa cứng vật lý (cả VPS, Local, Repo GitHub) với dung lượng > 1000 bytes, được kiểm chứng liên tục trong `tests/ci_neighbor_tester.py`.

---

### 5. Khối B6 (Speech & Whisper) ➔ Khối B8 (Remotion Props)
* **File lưu trữ**: `remotion_props.json`
* **Quy chuẩn Rule 120**: `durationInFrames` khớp chính xác timestamp câu thoại trong Whisper, cấm chia đều toán học.
* **Dynamic Beat Title & Sidechain Ducking**:
  - `speakerTag`: Hiển thị `BEAT <N>: <EPISODE_SPECIFIC_BEAT_TITLE>` tùy biến theo từng tập và từng beat (không dùng tiêu đề mặc định cố định).
  - Sidechain Ducking: FFmpeg `-20dB` tự động hạ BGM khi có giọng đọc thoại và phục hồi sau 300ms.
* **Lộ Trình Chuẩn Hóa Timeframe Whisper Đồng Nhất Toàn Luồng (Architectural Roadmap Note)**:
  > [!NOTE]
  > Quy hoạch tương lai sẽ tích hợp cơ chế đồng nhất Timeframe khép kín giữa Đạo diễn nghệ thuật (B3 Director Plan) ➔ Visual Assets (B4/B5) ➔ Phân cảnh & Karaoke Subtitles (B7/B8) ➔ Speech TTS Audio (B6) dựa trên Whisper Word Timestamps thực tế, loại bỏ hoàn toàn độ trễ lệch pha giữa nhịp thoại và nhịp cảnh.
* **Data Schema (Remotion Multi-Layer Motion Graphics Contract - Vox Benchmark Parity cXQuNBZA0FA)**:
  ```json
  {
    "audio_path": "audio/narration_master.mp3",
    "bgm_path": "audio/bgm_<mood_slug>.mp3",
    "scenes": [
      {
        "scene_id": "scene_<001>",
        "start_frame": "<INTEGER_START_FRAME>",
        "duration_in_frames": "<INTEGER_DURATION_FRAMES: Max 300 @ 30fps>",
        "canvas_texture": "paper_kraft_300gsm",
        "background": "images/scene_<001>_bg.png",
        "foreground": "images/scene_<001>_fg.png",
        "geometric_stage": {
          "shape": "<bracket_dossier | split_screen_diagonal | tactical_grid_matrix>",
          "color_accent": "<HEX_COLOR: e.g. #f2a63b>",
          "enter_frame": "<INTEGER: 15-30>"
        },
        "subject_layer": {
          "image_src": "images/scene_<001>_fg.png",
          "position": "<left | right | center>",
          "drop_physics": {
            "enter_frame": "<INTEGER: 45-60>",
            "drop_distance_px": 35,
            "damping": 12,
            "mass": 0.4
          }
        },
        "evidence_documents": [
          {
            "doc_id": "doc_<01>",
            "image_src": "images/scene_<001>_evidence.png",
            "enter_frame": "<INTEGER: 90-120>",
            "tilt_deg": "<FLOAT: -3.0 to +3.0>",
            "stamp_badge": "<CONFIDENTIAL | CRITICAL | LEAKED | EXCEEDED | null>",
            "stamp_slam_frame": "<INTEGER: 180>"
          }
        ],
        "data_visualization": {
          "type": "<rising_bar | line_draw | kinetic_counter | causal_flow | null>",
          "enter_frame": "<INTEGER: 100-150>",
          "payload": {
            "start_value": 0,
            "target_value": "<FLOAT_OR_INT>",
            "prefix": "<e.g. $ | null>",
            "suffix": "<e.g. B | % | null>",
            "chart_points": [
              {"label": "<LABEL_1>", "value": "<FLOAT>"},
              {"label": "<LABEL_2>", "value": "<FLOAT>"}
            ]
          }
        },
        "highlight_marker": {
          "start_word_index": "<INTEGER>",
          "end_word_index": "<INTEGER>",
          "color": "#facc15",
          "start_frame": "<INTEGER>",
          "duration_frames": "<INTEGER>"
        },
        "camera_movement": "<slow_push_in | snap_zoom | cinematic_pan | macro_tilt | slow_pull_out | handheld_shake>",
        "cinematic_tokens": ["<TOKEN_1>", "<TOKEN_2>"],
        "optical_fx": ["<vignette | film_grain | chromatic_aberration | glitch>"],
        "speakerTag": "<DYNAMIC_BEAT_TITLE: e.g. BEAT 1: The Impossible Contradiction>",
        "transition_out": "<vox_push_zoom | vox_paper_wipe | tactical_snap_cut>",
        "subtitles": [
          {"word": "<WORD_1>", "start_ms": "<INT_MS>", "end_ms": "<INT_MS>"},
          {"word": "<WORD_2>", "start_ms": "<INT_MS>", "end_ms": "<INT_MS>"}
        ]
      }
    ]
  }
  ```

---

### 6. Khối B10 (SEO Packaging) ➔ YouTube Upload Payload
* **File lưu trữ**: `youtube_upload_payload.json`
* **Data Schema**:
  ```json
  {
    "snippet": {
      "title": "<TITLE: High-CTR Curiosity Gap Title Without Clickbait Deception>",
      "description": "<DESCRIPTION: 5-Beat chapter markers, forensic sources, disclaimer>",
      "tags": ["<PRIMARY_KEYWORD>", "<NICHE_ENTITY>", "<ERA_OR_TOPIC_THEME>"]
    },
    "status": {
      "privacyStatus": "unlisted",
      "selfDeclaredMadeForKids": false,
      "containsSyntheticMedia": true
    },
    "thumbnail_path": "thumbnails/thumbnail_a.png"
  }
  ```

---

### 7. Khối B11 (Analytics Dreaming) ➔ Khối B1.0/B1.5 (V7 Autonomous Closed-Loop Feedback Engine)
* **File lưu trữ**: `data/v7_winning_pool.json`
* **Mục đích**: Vòng lặp phản hồi thuật toán tự học (học từ "Công thức V7" của An Ong). B11 tự động trích xuất các video đối thủ đang đề xuất (`RELATED_VIDEO`) sang video thắng của kênh, lọc sạch qua 3 lớp (Khử nhiễu Views >= 10, Bộ lọc kép CTR/AVD > Average dòng Tổng, Lọc ngách ngữ nghĩa khớp Canonical Pillars), sau đó nạp vào vòng đấu thầu Điểm Khả Thi (Competitive Scoring) tại B1.0 và làm Anchor Video cho B1.5.
* **Data Schema (Generic Specification)**:
  ```json
  {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "V7WinningTopicPool",
    "type": "object",
    "properties": {
      "market": "<MARKET_CODE: EN | JP | KR | VN | ALL>",
      "last_harvest_at": "<ISO_8601_TIMESTAMP>",
      "candidates": [
        {
          "candidate_id": "V7_<MARKET>_<REFERRING_VIDEO_ID>",
          "source_winning_video_id": "<SOURCE_WINNING_VIDEO_ID>",
          "referring_video_id": "<REFERRING_VIDEO_ID>",
          "referring_title": "<REFERRING_VIDEO_TITLE>",
          "referring_channel_title": "<REFERRING_CHANNEL_TITLE>",
          "ctr_percent": "<FLOAT: Calculated or proxy CTR %>",
          "benchmark_avg_ctr": "<FLOAT: Total row benchmark CTR %>",
          "avd_seconds": "<FLOAT: Average view duration in seconds>",
          "benchmark_avg_avd": "<FLOAT: Total row benchmark AVD in seconds>",
          "views_from_source": "<INTEGER_VIEWS>",
          "canonical_pillar": "<CANONICAL_PILLAR_NAME>",
          "viability_score": "<FLOAT: 0.0 - 10.0 | null>",
          "status": "<PENDING | CONSUMED | EXPIRED | REJECTED>",
          "consumed_by_episode": "<MARKET>_EP<0000>_<topic_slug> | null",
          "discovered_at": "<ISO_8601_TIMESTAMP>"
        }
      ]
    }
  }
  ```
* **Quy chuẩn Field Ràng buộc**:
  - `candidate_id`: Bắt buộc tuân thủ regex `^V7_[A-Z]{2}_[a-zA-Z0-9_-]+$`.
  - `status`: Chuyển từ `PENDING` sang `CONSUMED` ngay khi đề tài được cam kết sản xuất tại B1.0 (`commit_trend_task`).
  - `canonical_pillar`: Bắt buộc thuộc danh sách 10 Canonical Pillars chính thống, cấm rò rỉ video rác giải trí/nhạc/game.

---

## 🗂️ II. DANH MỤC MÃ NGUỒN CHUẨN TRÊN VPS (`/root/video_factory`)

| Đường Dẫn Tệp | Vai Trò Kỹ Thuật | Block Phụ Trách |
| :--- | :--- | :--- |
| `app/services/trend_engine_b1.py` | Cào Google Trends RSS live, Wikipedia Anchor | Block 1.0 |
| `app/services/competitor_recon_b15.py` | YouTube Data API, bóc tách comment & Explanatory Vacuum | Block 1.5 |
| `app/services/grounding_layer_b15.py` | Google Search Grounding REST API & Confidence Gate | Block 1.5.5 |
| `tests/test_grounding_layer.py` | Test suite kiểm thử Grounding Verification Gate | Block 1.5.5 Unit Test |
| `app/services/story_engine_b2.py` | Sinh kịch bản 5 Beat Docudrama qua GPT-6-Astra | Block 2.0 |
| `app/services/beat_tts_engine.py` | Hollywood Audio Spine, Beat-Level Edge-TTS, Word Karaoke & Subtitles SRT | Block 2.6 (Audio Spine) |
| `app/services/director_planner_b3.py` | Dynamic Director Plan, Universal Scene Breakdown & Hard Gate | Block 3.0 |
| `app/services/prompt_forge.py` | Prompt Forge cho Layer 1 BG & Layer 2 FG (#FF00FF) | Block 3.5 |
| `scripts/gemini_browser_gen.py` | Chrome Automation sinh ảnh Gemini Pro Web | Block 4.0 |
| `app/services/beat_bgm_engine.py` | 5-Beat Docudrama Adaptive BGM & YouTube Audio Library Vault | Block 7.5 (BGM Engine) |
| `tests/test_beat_bgm_engine.py` | Test suite kiểm thử 5-Beat BGM Engine & Crossfading | Block 7.5 Unit Test |
| `app/services/build_remotion_props.py` | Ghép timestamp Whisper vào props Remotion | Block 7.0 |
| `remotion/src/index.tsx` | TwoLayerEpisode 1080p React Remotion Engine | Block 8.0 |
| `app/pipeline/stages/s7_render.py` | Remotion CPU Render & bypass redundant burning | Block 8.0 |
| `app/services/seo_package_forge.py` | B10 SEO Packaging & Gate 2 Upload Payload | Block 10.0 |
| `scripts/b11_engine.py` | Analytics 48h Routine Lean Sync & Deep Post-Mortem | Block 11.0 |
| `scripts/orchestrator/ghost_code_detector.py` | 4-Layer Automated Ghost Code Hunter Engine (VETO Authority) | Core Orchestrator Gate |

---

## 🌐 III. KHẾ ƯỚC HẠ TẦNG ĐỒNG BỘ TAM GIÁC (THREE-WAY SYNC INFRASTRUCTURE)

> **MỤC ĐÍCH**: Ngăn chặn triệt để tình trạng "Antigravity báo xong nhưng VPS chưa nhận", đảm bảo mọi thay đổi code giữa máy Local (Antigravity IDE), VPS Hetzner (`/root/video_factory`), GitHub Remote và Notion SoT luôn ở trạng thái đồng bộ vật lý 100%.

### 1. Ma Trận Tọa Độ Hạ Tầng (Infrastructure Coordinates)
| Thực Thể | Đường Dẫn / Tọa Độ | Vai Trò | Cơ Chế Kết Nối / Đồng Bộ |
| :--- | :--- | :--- | :--- |
| **Local Workspace** | `c:\Users\hunghd2\Documents\antigravity\AI Video Factory` | IDE Interface & Prompt Engineering | Trực tiếp trong Antigravity IDE |
| **VPS Hetzner** | `/root/video_factory` | Production Core & Pipeline Execution | MCP Tool `vf-factory` / Runner `scripts/vps_runner.py` |
| **GitHub Remote** | `https://github.com/hoangdinhhungueh-droid/AI_Vifactory.git` | Version Control Single Truth (`main`) | `git push origin main` từ VPS |
| **Notion SoT** | Notion DBs & Second Brain Hubs | Single Source of Truth & Analytics Lab | Notion REST API v2022-06-28 |

### 2. Quy Chuẩn Vận Hành 4 Khóa Nghiệm Thu Vật Lý (Physical Verification 4-Step Gate)
Mọi tác vụ can thiệp code trong pipeline BẮT BUỘC tuân thủ thứ tự 4 bước pháp y:
1. **Khóa 1 (Physical Write Verification)**:
   - Ghi trực tiếp xuống đĩa cứng VPS (`/root/video_factory`). CẤM TUYỆT ĐỐI chỉ sửa file tại local Windows rồi báo hoàn thành.
   - Nếu MCP transport gặp lỗi (`Internal Server Error` / `Unauthorized`), BẮT BUỘC fallback sang `scripts/vps_runner.py` để thực thi trực tiếp qua Fresh Session.
2. **Khóa 2 (Syntax & ISO Neighbor Testing)**:
   - Kiểm tra biên dịch AST `python3 -m py_compile <file_path>` đạt exit code `0`.
   - Chạy test kiểm thử liên khối neighbor-testing đạt PASS.
3. **Khóa 3 (Git Atomic Commit & Push từ VPS lên GitHub)**:
   - Thực thi ngay trên VPS:
     ```bash
     git -C /root/video_factory add <modified_files>
     git -C /root/video_factory commit -m "<type>(<scope>): <explicit message>"
     git -C /root/video_factory push origin main
     ```
   - Xác nhận `git -C /root/video_factory status` trả về: `On branch main, your branch is up to date with 'origin/main', nothing to commit, working tree clean`.
4. **Khóa 4 (Local Workspace & Notion SoT Alignment)**:
   - Đồng bộ tệp tài liệu/khế ước tương ứng vào thư mục cục bộ của Antigravity (`c:\Users\hunghd2\Documents\antigravity\AI Video Factory`).
   - Cập nhật trang Notion SoT tương ứng, đảm bảo mọi tài liệu nội hàm khớp 100% với code thực tế trên VPS (Zero-Ambiguity Mandate).
