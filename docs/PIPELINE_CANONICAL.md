# 🎬 KIẾN TRÚC PIPELINE CHUẨN (CANONICAL PIPELINE 2.0)

> **Mục tiêu**: Định nghĩa chuẩn mực duy nhất (Single Source of Truth) cho luồng sản xuất video AI Vox-Style từ khâu cào đề tài đến xuất bản video hoàn chỉnh.
> **Tuân thủ**: Rule 118 (Zero-Mock), Rule 121 (Forensic Verification), Rule 125 (Single Pipeline Version), Rule 126 (Three-Way Sync), Rule 132 (Decoupled Engine).

---

## 📌 I. SƠ ĐỒ ĐIỀU PHỐI TỔNG THỂ (11 GIAI ĐOẠN)

```
[S1: Ideation] ──► [S2: Research] ──► [S3: Script] ──► [S4: Critic Script]
                                                              │
                                                              ▼
[S7: Image Gen] ◄── [S6: Critic Visual] ◄── [S5: Director Plan]
      │
      ▼
[S8: Video Gen (7 Acc Flow)] ──► [S9: Voice TTS] ──► [S10: Remotion Render] ──► [S11: QC]
```

Mỗi mũi tên `──►` đại diện cho một **Boundary Validation Gate** (`core/gates.py`):
1. Dữ liệu bắt buộc bọc trong `StageArtifact` (Pydantic v2, `extra="forbid"`, `schema_version="1.0.0"`).
2. Stage $N+1$ chỉ nhận dữ liệu thông qua hàm `require_input(StageID, paths)`. CẤM stage tự ý tìm đọc file tùy tiện.
3. Khi hoàn tất, stage gọi `emit_artifact(artifact, paths)` để ghi file atomic (.tmp $\rightarrow$ replace).

---

## 📐 II. BẢNG KHẾ ƯỚC DỮ LIỆU TỪNG GIAI ĐOẠN (STAGE CONTRACTS)

| Giai Đoạn | StageID | Đầu Vào Bắt Buộc | Đầu Ra Chuẩn (Payload) | Chốt Chặn Kiểm Tra (Gate) |
| :--- | :--- | :--- | :--- | :--- |
| **S1: Ideation** | `s01_ideation` | Google Trends RSS Live / Notion Trend DB | `{ topic, raw_term, viability_score, market, angle_brief }` | Score $\ge 8.0$, cấm synthetic/mock |
| **S2: Research** | `s02_research` | S1 Artifact | `{ factsheet, grounding_sources, key_entities, competitor_gaps }` | Có ít nhất 1 nguồn Ground Truth |
| **S3: Script** | `s03_script` | S2 Artifact | `{ beats: [5 Beat Docudrama], scenes: [Scene(scene_id, narration, duration)] }` | Đúng 5 Beat, không mở đầu bằng câu hỏi |
| **S4: Critic Script**| `s04_critic_script` | S3 Artifact | `CouncilDecision { verdict, aggregate_score, verdicts }` | Điểm $\ge 8.5/10.0$ từ Astra 6 + Opus 5.5 |
| **S5: Director Plan**| `s05_director_plan` | S4 Artifact (Approved) | `{ scenes: [Scene(headline, visual_metaphor, color_accent, shots)] }` | Headline 1-4 từ, tactile paper cutout |
| **S6: Critic Visual**| `s06_critic_visual` | S5 Artifact | `CouncilDecision { verdict, aggregate_score }` | Điểm $\ge 8.5/10.0$ về bố cục và màu sắc |
| **S7: Image Gen** | `s07_image_gen` | S6 Artifact (Approved) | `{ images: [seed_image_path] }` lưu tại `composite_seeds/` | Rule 122 Visual Audit (sạch chữ, nét comic) |
| **S8: Video Gen** | `s08_video_gen` | S7 Artifact (Seeds) | `{ clips: [VideoAsset(shot_id, file_path, sha256)] }` | MP4 file size $>100$KB, xoay vòng 7 acc |
| **S9: Voice TTS** | `s09_voice_tts` | S3 Artifact (Narration) | `{ audio_file, subtitles: [KaraokeWord(word, start, end)] }` | Word-level Whisper timestamps |
| **S10: Remotion** | `s10_render` | S8 (Clips) + S9 (Audio) | `final.mp4` trong `10_render/` | ffprobe xác nhận có đủ video + audio stream |
| **S11: QC Final** | `s11_qc` | S10 (final.mp4) | `{ qc_verdict: "PASS", duration_sec, resolution }` | Video đạt chuẩn 1080p/4K không lỗi frame |

---

## 🗂️ III. CƠ QUAN ĐƯỜNG DẪN DUY NHẤT (`core/paths.py`)

Toàn bộ artifact được gom về một thư mục thống nhất:
```
runs/<run_id>/ (hoặc episodes/<episode_id>/)
  ├── run_manifest.json          # Trạng thái State Machine & Resume
  ├── pipeline.log               # Log tập trung
  ├── composite_seeds/           # Ảnh seed chuẩn bị cho I2V
  │     ├── composite_scene_01.png
  │     └── ...
  ├── video_clips/               # Video MP4 thô từ Google Flow
  │     ├── clip_scene_01.mp4
  │     └── ...
  ├── audio/                     # Audio voiceover và Whisper subtitles
  │     ├── voice_narration.mp3
  │     └── word_timestamps.json
  ├── 10_render/                 # Thành phẩm Remotion Master Video
  │     └── final.mp4
  └── <stage_name>/              # JSON khế ước từng stage
        └── artifact.json
```

---

## 🚀 IV. VẬN HÀNH CHUẨN 1 LỆNH (ONE-COMMAND RUNBOOK)

Cổng điều phối duy nhất của toàn bộ hệ thống là module `orchestrator.run_pipeline`. Tuyệt đối không gọi các shadow script cũ.

### 1. Sản Xuất Tập Mới (Production Full Run)
Chạy toàn bộ 11 stages với profile chuẩn (7-account Google Flow, Remotion 1080p, đầy đủ 5 Beat Docudrama):
```bash
python -m orchestrator.run_pipeline --profile prod
```

### 2. Kiểm Thử Nhanh / Khí Tài Tối Thiểu (Low-Quota E2E Run)
Chạy kiểm thử khép vòng tối thiểu (1 scene, 1 shot 5s, 1 account) để nghiệm thu hệ thống mà không hao tốn tài nguyên:
```bash
python -m orchestrator.run_pipeline --profile e2e_min
```

### 3. Phục Hồi & Chạy Tiếp Sau Sự Cố (Chaos / Crash Resumption)
Nếu pipeline gặp sự cố mạng hoặc dừng ở giữa (ví dụ tại `s08_video_gen`):
- Hệ thống tự động lưu `run_manifest.json` và checkpoint SHA256 cho các stages trước.
- Khôi phục và chạy tiếp từ stage gặp lỗi mà không cần chạy lại từ đầu:
```bash
python -m orchestrator.run_pipeline --run-id RUN_YYYYMMDD_HHMMSS --from s08_video_gen
```

### 4. Chạy Riêng Lẻ / Debug Một Stage (Single-Stage Execution)
Khi cần tinh chỉnh hoặc kiểm thử riêng biệt một stage duy nhất (ví dụ tái sinh kịch bản với Prompt mới):
```bash
python -m orchestrator.run_pipeline --run-id RUN_YYYYMMDD_HHMMSS --only s03_script --force
```

### 5. Kiểm Toán An Toàn Mã Nguồn & Chống Ghost Code (Anti-Ghost Gate)
Trước khi commit hoặc deploy, bắt buộc chạy scanner để chứng minh zero ghost remnants:
```bash
python tools/ghost_scan.py
```

### 6. Bộ Kiểm Thử Hợp Đồng & Luồng Chuẩn (Canonical Unit Tests)
```bash
pytest tests/test_paths.py tests/test_contracts.py tests/test_gates_manifest.py tests/test_config.py tests/test_legacy_isolation.py
```
