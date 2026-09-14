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

### 3. Khối B2 (Story Engine) ➔ Khối B3 (Director Plan)
* **File lưu trữ**: `/var/vf/episodes/<task_id>/story.txt (Kịch bản 5 Beat) & brain_input.json`
* **Quy chuẩn**: 5 Beat Docudrama (1,800–2,200 từ, ~12–15 phút), Rule 444 Hook (0–60s), Micro-Cliffhangers (90–120s), Story Gate $\ge 8/10$.
* **Data Schema**:
  ```json
  {
    "task_id": "<MARKET>_EP<0000>_<topic_slug>",
    "task_slug": "<lowercase-hyphenated-topic-slug>",
    "language": "<en | vi | ja | ko>",
    "word_count": "<INTEGER: 1800 - 2200>",
    "beats": [
      {"beat": 1, "name": "The Impossible Contradiction", "text": "<BEAT_1_TEXT: Hook 0-60s & An Ong Paradox>"},
      {"beat": 2, "name": "The False Narrative & Red Herring", "text": "<BEAT_2_TEXT: Buildup & Common Misconception>"},
      {"beat": 3, "name": "The Systemic Blindspot & Paper Trail", "text": "<BEAT_3_TEXT: Forensic Investigation & Evidence>"},
      {"beat": 4, "name": "The Real Culprit & Smoking Gun", "text": "<BEAT_4_TEXT: The Climax & Systemic Core Revelation>"},
      {"beat": 5, "name": "The Uncomfortable Modern Mirror", "text": "<BEAT_5_TEXT: Modern Echo & Lingering Lesson>"}
    ]
  }
  ```

---

### 4. Khối B3 (Director Plan) ➔ Khối B3.5 (Prompt Forge)
* **File lưu trữ**: `director_plan.json` ➔ `prompts_forge.json (và prompts.json tương thích ngược)`
* **Quy chuẩn**: Toàn bộ visual prompts viết bằng tiếng Anh, gắn `[STYLE MANDATE]`, `[MARKET & ETHNIC ANCHOR]`, `[MARKET & ENVIRONMENT ANCHOR]`, `[ERA ANCHOR]`, `[STRICT NEGATIVE PROMPT]`.
* **Pacing & Asset Optimization (130-160 Scenes & 15-20 Clustered BGs)**:
  - **Pacing**: Chuẩn hóa nhịp 130–160 scenes động (~4–6s/scene) dàn đều 5 Beats, đẩy nhịp dựng Fincher kịch tính.
  - **Clustered BG Reuse**: B4 sinh tối ưu hóa 15–20 Backgrounds độc bản (`bg_cluster_id`) được tái sử dụng linh hoạt xuyên suốt các scenes trong cùng một bối cảnh, triệt tiêu nguy cơ nghẽn API sinh ảnh hoặc kéo dài render.
  - **6 Cinematic Camera Moves**: `"slow_zoom_in"`, `"slow_zoom_out"`, `"pan_left"`, `"pan_right"`, `"tracking_shot"`, `"dutch_angle_push"`.
  - **4 Forensic Evidentiary Overlays**: `"none"`, `"document_highlight"`, `"timeline_tick"`, `"stat_counter"`, `"redacted_stamp"`.
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
        "camera_movement": "<slow_zoom_in | slow_zoom_out | pan_left | pan_right | tracking_shot | dutch_angle_push>",
        "forensic_overlay": "<none | document_highlight | timeline_tick | stat_counter | redacted_stamp>",
        "setting_description": "<ENVIRONMENT_DESCRIPTION_ENGLISH: Detailed setting and era background>",
        "character_description": "<CHARACTER_DESCRIPTION_ENGLISH: Detailed subject appearance, clothing, mood>",
        "visual_action": "<VISUAL_ACTION_ENGLISH: Subject pose and dynamic interaction>"
      }
    ]
  }
  ```

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
* **Data Schema**:
  ```json
  {
    "audio_path": "audio/narration_master.mp3",
    "bgm_path": "audio/bgm_<mood_slug>.mp3",
    "scenes": [
      {
        "scene_id": "scene_<001>",
        "start_frame": "<INTEGER_START_FRAME>",
        "duration_in_frames": "<INTEGER_DURATION_FRAMES>",
        "bg_image": "images/scene_<001>_bg.png",
        "fg_image": "images/scene_<001>_fg.png",
        "camera_movement": "<slow_zoom_in | slow_zoom_out | pan_left | pan_right | tracking_shot | dutch_angle_push>",
        "forensic_overlay": "<none | document_highlight | timeline_tick | stat_counter | redacted_stamp>",
        "speakerTag": "<DYNAMIC_BEAT_TITLE: e.g. BEAT 1: The Impossible Contradiction>",
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

## 🗂️ II. DANH MỤC MÃ NGUỒN CHUẨN TRÊN VPS (`/root/video_factory`)

| Đường Dẫn Tệp | Vai Trò Kỹ Thuật | Block Phụ Trách |
| :--- | :--- | :--- |
| `app/services/trend_engine_b1.py` | Cào Google Trends RSS live, Wikipedia Anchor | Block 1.0 |
| `app/services/competitor_recon_b15.py` | YouTube Data API, bóc tách comment & Explanatory Vacuum | Block 1.5 |
| `app/services/grounding_layer_b15.py` | Google Search Grounding REST API & Confidence Gate | Block 1.5.5 |
| `tests/test_grounding_layer.py` | Test suite kiểm thử Grounding Verification Gate | Block 1.5.5 Unit Test |
| `app/services/story_engine_b2.py` | Sinh kịch bản 5 Beat Docudrama qua GPT-6-Astra | Block 2.0 |
| `tests/ci_neighbor_tester.py` | Framework ISO Neighbor-Testing `[N-1, N, N+1]` | CI/CD Quality Gate |
| `app/services/prompt_forge.py` | Prompt Forge cho Layer 1 BG & Layer 2 FG (#FF00FF) | Block 3.5 |
| `scripts/gemini_browser_gen.py` | Chrome Automation sinh ảnh Gemini Pro Web | Block 4.0 |
| `app/pipeline/stages/s6_speech.py` | TTS Edge-TTS & Faster-Whisper trích xuất word timestamp | Block 6.0 & 7.0 |
| `app/services/beat_bgm_engine.py` | 5-Beat Docudrama Adaptive BGM & YouTube Audio Library Vault | Block 7.5 (BGM Engine) |
| `tests/test_beat_bgm_engine.py` | Test suite kiểm thử 5-Beat BGM Engine & Crossfading | Block 7.5 Unit Test |
| `app/services/build_remotion_props.py` | Ghép timestamp Whisper vào props Remotion | Block 7.0 |
| `remotion/src/index.tsx` | TwoLayerEpisode 1080p React Remotion Engine | Block 8.0 |
| `app/pipeline/stages/s7_render.py` | Remotion CPU Render & bypass redundant burning | Block 8.0 |
| `app/services/seo_autogen_b10.py` | B10 SEO Packaging & Gate 2 Upload Payload | Block 10.0 |
| `scripts/b11_engine.py` | Analytics 48h Routine Lean Sync & Deep Post-Mortem | Block 11.0 |

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
