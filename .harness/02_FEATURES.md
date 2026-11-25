# 🧩 02_FEATURES.md - DANH MỤC TÍNH NĂNG PIPELINE (IN-PLACE LIVING STATE)

> **CẤM GHI NHẬT KÝ SONG SONG (ZERO APPEND-ONLY LOGS).**
> File này luôn phản ánh chính xác trạng thái sống hiện tại của các module đang chạy trong `orchestrator/run_pipeline.py`.

---

### [FT-301] Voice-First Papertrails LLM Semantic 3D Director
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/papertrails_director.py`, `stages/s05_director_plan.py`, `config/prompts/papertrails_director.md`
- **Hàm/Service**: `direct_papertrails_timeline_with_llm`, `_run_papertrails_voice_first_director`
- **Input Contract**: `S09` audio + measured `faster-whisper`/`WordBoundary` word timestamps, `S02` Grounding claims, `S03` 5-Beat script
- **Output Contract**: `PapertrailsTimelineSpec` (`timeline.json`), `DIRECTION.md`, `director_plan.json`
- **Logic cốt lõi**:
  1. Đọc chuỗi từ vựng gắn timestamp thật từ S09 (`timing_source` tuyệt đối không giả lập ở chế độ `prod`).
  2. Gọi `ModelGateway.call_llm` với system spec tách rời tại `config/prompts/papertrails_director.md` (Rule 132/128).
  3. Cắt shot nhịp `2.0s–5.0s` trên đúng ranh giới chỉ mục từ (`word_start_idx..word_end_idx`), phủ 100% không hở khoảng thời gian.
  4. Chọn ngữ nghĩa trên toàn bộ **32 Paper Props** (`courthouse`, `gavel`, `ledger`, `container`, `vault`, `scale`, `contract`, `megaphone`, `briefcase`, `shield` + 22 props gốc) và **5 Biomes** (`heartland`, `pinewood`, `desert`, `snow`, `blossom`), cấm lặp cặp `(biome, prop)` hoặc `camera` liền kề.
  5. Chỉ sử dụng camera động học liên tục (`push`, `orbit`, `crane`, `low`); làm sạch tiêu đề theo Rule 136 (zero `B1_L01` leak); gắn `note` cards từ số liệu S02 thật.

---

### [FT-302] Papertrails Stills Gate & Parallel 3-Worker VPS Renderer
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/papertrails_vps_bridge.py`, `stages/s08_video_gen.py`, `vox/papertrails_engine/scripts/render.mjs`, `vox/papertrails_engine/scripts/render_parallel.mjs`, `vox/papertrails_engine/engine/src/video/props.js`, `vox/papertrails_engine/engine/src/video/index.js`
- **Hàm/Service**: `render_papertrails_stills_on_vps`, `render_papertrails_on_vps`, `_run_papertrails_3d_stage`
- **Input Contract**: `timeline.json` (`1920x1080`) & `voice_narration.mp3` (EBU R128 normalized)
- **Output Contract**: `stills/*.png` (HG3 Gate) + `master_papertrails.mp4` (`1920x1080`, `med`, `30fps`, H.264/AAC, `--sfx`)
- **Logic cốt lõi**:
  1. Bổ sung 10 3D folded-paper props điều tra/tài chính vào `props.js` và bổ sung chuyển động nhẹ liên tục vào `wide`/`close`/`top` trong `index.js` để triệt tiêu mọi khung hình đóng băng.
  2. Chạy `--stills-only` kết xuất nhanh ~12 ảnh đại diện qua scene-seeking (`allowSeek`), tải qua `download_vps_asset.py` để kiểm tra thị giác trước khi render full.
  3. Chạy `render_parallel.mjs --workers 3 --quality med --sfx` chia theo ranh giới scene trên 6 vCPU VPS (unset PM2 env vars tránh SIGABRT exit 134), ghép lossless `-c:v copy` và kiểm chứng 3 cửa sổ chuyển động (`t=start/mid/end`).

---

### [FT-303] Voice-First Real ASR & Lossless Master Assembly
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s09_voice_tts.py`, `vox/ffmpeg_utils.py`, `stages/s10_render.py`
- **Hàm/Service**: `_synthesize_edge_tts_stream`, `normalize_audio_ebur128`, `_measure_words_with_faster_whisper`, `_validate_and_assemble_video`
- **Input Contract**: `S03` narration script & `master_papertrails.mp4`
- **Output Contract**: `audio/voice_narration.mp3` + `word_timestamps.json` + `transcript_segments.json`, `10_render/final.mp4` + `chapters.txt`
- **Logic cốt lõi**:
  1. S09 bắt sự kiện `WordBoundary` thật của Edge-TTS, chuẩn hóa EBU R128 hai bước (`-16.0 LUFS`, `TP <= -2.5 dBTP`), đo và đối soát mốc từ qua `faster-whisper` (`small`, `int8`).
  2. S10 giữ nguyên video stream `-c:v copy` từ `master_papertrails.mp4` và chạy hai bước `loudnorm` trên kênh audio sau trộn `--sfx`, đồng bộ `remotion_props.json` & `chapters.txt` từ `timeline.json`.

---

### [FT-205] Ground-Truth Timeline & Forensic QC Gate
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s11_qc.py`, `vox/qa/gates.py`
- **Hàm/Service**: `run`, `verify_final_video_gates`
- **Input Contract**: `10_render/final.mp4`, `director_plan.json`, `remotion_props.json`
- **Output Contract**: `s11_qc/artifact.json` (`qc_verdict: "PASS"`)
- **Logic cốt lõi**: Kiểm toán stream H.264/AAC, 0 khung hình đen, không đứng hình > 1.2s (`Rule 140`), âm lượng EBU R128 `[-17.0, -15.0] LUFS` & `<= -2.0 dBTP`, và đối khớp thời lượng giọng đọc.

---

### [FT-201] / [FT-203] / [FT-204] / [FT-206] / [FT-207] Legacy 2D Sheet, Omni, Veo & Remotion Engines
- **Trạng thái**: `QUARANTINED_LEGACY`
- **Ghi chú**: Đã bị bỏ qua hoàn toàn trong luồng `prod` (`PAPERTRAILS_VOICE_FIRST_STAGES`). Các hàm helper cũ trong `stages/s05_director_plan.py` và `stages/s10_render.py` chỉ giữ lại cho bộ kiểm thử `e2e_min` / tương thích ngược unit test cho tới khi dọn bỏ hoàn toàn.
