# 📐 Pipeline Interface Contracts & Code Layout (ISO-Grade B1–B11)

> **MỤC ĐÍCH**: Bản đặc tả kỹ thuật sống về Khế ước Dữ liệu (IN/OUT Data Contracts) giữa các block trong Pipeline và Danh mục cấu trúc mã nguồn trên VPS (`/root/video_factory`).
> Mọi thay đổi về Schema dữ liệu bắt buộc phải được kiểm thử qua `tests/ci_neighbor_tester.py` (Rule 447).

---

## 🔄 I. KHẾ ƯỚC DỮ LIỆU LIÊN KHỐI (INTER-BLOCK DATA CONTRACTS)

### 1. Khối B1 (Trend Discovery) ➔ Khối B1.5 (Competitor Recon)
* **File lưu trữ**: `/var/vf/episodes/<task_id>/trend_intel.json`
* **Data Schema**:
  ```json
  {
    "task_id": "EN_EP0102_lehman_collapse",
    "market": "EN",
    "raw_term": "Lehman Brothers Bankruptcy",
    "viability_score": 88.5,
    "factsheet": {
      "verified_date": "2008-09-15",
      "key_entities": ["Richard Fuld", "Federal Reserve", "Treasury"],
      "core_mechanism": "Subprime mortgage CDO collateral collapse",
      "wikipedia_ground_truth_url": "https://en.wikipedia.org/wiki/Bankruptcy_of_Lehman_Brothers"
    },
    "niche_angle_brief": "The hidden repo 105 loophole that masked insolvency",
    "story_direction_5_arcs": ["The Facade", "The Secret Ledger", "The Fed Standoff", "The 72-Hour Panic", "The Living Echo"]
  }
  ```

---

### 2. Khối B1.5 (Competitor Recon) ➔ Khối B2 (Story Engine)
* **File lưu trữ**: `/var/vf/episodes/<task_id>/competitor_intel_card.json`
* **Data Schema**:
  ```json
  {
    "task_id": "EN_EP0102_lehman_collapse",
    "analyzed_videos_count": 8,
    "competitor_act_breakdown": [
      {"competitor": "Channel A", "structure": "Chronological history of 150 years", "weakness": "Surface-level, lacks drama"}
    ],
    "competitor_secret_sauce": "Fast paced B-roll montage with heavy cinematic bass drops",
    "audience_core_frustrations": [
      "No one explains what Repo 105 actually was in plain English",
      "Rivals never showed who actually profited from the bailout"
    ],
    "fatal_explanatory_vacuum": "Complete silence on the accounting accounting gimmick Repo 105 and Fed internal division",
    "our_10x_pivot_angle": "Forensic crime scene investigation: How accounting fraud was disguised as liquidity"
  }
  ```

---

### 3. Khối B2 (Story Engine) ➔ Khối B3 (Director Plan)
* **File lưu trữ**: `/var/vf/episodes/<task_id>/story_5_acts.json`
* **Quy chuẩn**: 5 Beat Docudrama (1,800–2,200 từ, ~12–15 phút), Rule 444 Hook (0–60s), Micro-Cliffhangers (90–120s), Story Gate $\ge 8/10$.
* **Data Schema**:
  ```json
  {
    "task_id": "EN_EP0102_lehman_collapse",
    "task_slug": "lehman-repo105-collapse",
    "language": "en",
    "word_count": 2045,
    "beats": [
      {"beat": 1, "name": "The Impossible Contradiction", "text": "..."},
      {"beat": 2, "name": "The False Narrative & Red Herring", "text": "..."},
      {"beat": 3, "name": "The Systemic Blindspot & Paper Trail", "text": "..."},
      {"beat": 4, "name": "The Real Culprit & Smoking Gun", "text": "..."},
      {"beat": 5, "name": "The Uncomfortable Modern Mirror", "text": "..."}
    ]
  }
  ```

---

### 4. Khối B3 (Director Plan) ➔ Khối B3.5 (Prompt Forge)
* **File lưu trữ**: `director_plan.json` ➔ `prompts_forge.json`
* **Quy chuẩn**: Toàn bộ visual prompts viết bằng tiếng Anh, gắn `[STYLE MANDATE]`, `[ERA ANCHOR]`, `[STRICT NEGATIVE PROMPT]`.
* **Data Schema (`director_plan.json`)**:
  ```json
  {
    "scenes": [
      {
        "scene_id": "scene_001",
        "act_number": 1,
        "background_reuse_key": "bg_wall_street_trading_floor",
        "foreground_reuse_key": "fg_fuld_frantic_phone",
        "setting_description": "Manhattan investment bank trading desk at midnight",
        "character_description": "CEO Richard Fuld, mid-60s, sharp pin-striped suit, exhausted",
        "visual_action": "Slamming landline telephone onto desk covered in red spreadsheets"
      }
    ]
  }
  ```

---

### 5. Khối B6 (Speech & Whisper) ➔ Khối B8 (Remotion Props)
* **File lưu trữ**: `remotion_props.json`
* **Quy chuẩn Rule 120**: `durationInFrames` khớp chính xác timestamp câu thoại trong Whisper, cấm chia đều toán học.
* **Data Schema**:
  ```json
  {
    "audio_path": "audio/narration_master.mp3",
    "bgm_path": "audio/bgm_cinematic_tension.mp3",
    "scenes": [
      {
        "scene_id": "scene_001",
        "start_frame": 0,
        "duration_in_frames": 180,
        "bg_image": "images/scene_001_bg.png",
        "fg_image": "images/scene_001_fg.png",
        "subtitles": [
          {"word": "On", "start_ms": 120, "end_ms": 280},
          {"word": "September", "start_ms": 290, "end_ms": 750},
          {"word": "15th,", "start_ms": 760, "end_ms": 1150}
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
      "title": "The $600 Billion Lie That Broke Wall Street",
      "description": "...",
      "tags": ["wall street", "2008 financial crisis", "lehman brothers"]
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
| `app/services/story_engine_b2.py` | Sinh kịch bản 5 Beat Docudrama qua GPT-6-Astra | Block 2.0 |
| `tests/ci_neighbor_tester.py` | Framework ISO Neighbor-Testing `[N-1, N, N+1]` | CI/CD Quality Gate |
| `app/services/prompt_forge.py` | Prompt Forge cho Layer 1 BG & Layer 2 FG (#FF00FF) | Block 3.5 |
| `scripts/gemini_browser_gen.py` | Chrome Automation sinh ảnh Gemini Pro Web | Block 4.0 |
| `app/pipeline/stages/s6_speech.py` | TTS Edge-TTS & Faster-Whisper trích xuất word timestamp | Block 6.0 & 7.0 |
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

