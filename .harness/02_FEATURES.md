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
  4. Chọn ngữ nghĩa trên toàn bộ **35 Paper Props** (`hanko-stamp`, `brass-caliper`, `forensic-loupe`, `courthouse`, `gavel`, `ledger`, `container`, `vault`, `scale`, `contract`, `megaphone`, `briefcase`, `shield` + 22 props gốc) và **5 Biomes** (`heartland`, `pinewood`, `desert`, `snow`, `blossom`), cấm lặp `prop` hoặc cặp `(biome, prop)` hoặc `camera` liền kề (kể cả khi chia shot dài).
  5. Chỉ sử dụng camera động học liên tục phi tuyến (`push`, `orbit`, `crane`, `low` với `easeInOutCubic`/`smooth` trong `motion.js`); làm sạch tiêu đề theo Rule 136 (zero `B1_L01` leak); bắt buộc gắn `note` cards từ số liệu S02 thật (`>= 25%` số shot, tối thiểu `20%` tại gate fail-closed) bằng ngôn ngữ bản địa (`KR`/`EN`/`JA`/`VN`); dùng bảng màu lưu trữ (`#7d342b` thay tím neon); đính kèm **Contact-Frame Timing Sheet (`±2f`)** + `foley_cues` và chạy cổng `audit_papertrails_timeline_antipatterns` fail-closed.

---

### [FT-302] Papertrails Stills Gate & Macro Option-C Parallel VPS Renderer (`--quality vox`)
- **Trạng thái**: `ACTIVE`
- **File Code**: `app/services/papertrails_vps_bridge.py`, `stages/s08_video_gen.py`, `vox/papertrails_engine/scripts/render.mjs`, `vox/papertrails_engine/scripts/render_parallel.mjs`, `vox/papertrails_engine/scripts/lib/renderer.mjs`, `vox/papertrails_engine/engine/src/core/config/render.js`, `vox/papertrails_engine/engine/src/video/motion.js`, `vox/papertrails_engine/engine/src/video/print_textures.js`, `vox/papertrails_engine/engine/src/video/forensic_desk.js`, `vox/papertrails_engine/engine/src/video/props.js`, `vox/papertrails_engine/engine/src/video/index.js`, `vox/papertrails_engine/engine/video.html`
- **Hàm/Service**: `render_papertrails_stills_on_vps`, `render_papertrails_on_vps`, `_run_papertrails_3d_stage`, `createForensicDesk`, `createPrintedPaperMaterial`
- **Input Contract**: `timeline.json` (`1920x1080`, `stageMode: "forensic_desk"`) & `voice_narration.mp3` (EBU R128 normalized)
- **Output Contract**: `stills/*.png` (HG3 Gate) + `master_papertrails.mp4` (`1920x1080`, `vox`, `15->30fps CFR`, `jpeg` pipe, `2 workers`, H.264/AAC)
- **Logic cốt lõi**:
  1. Sân khấu **Vox 3D Forensic Paper Desk** (`forensic_desk.js`) thay thế hoàn toàn địa hình cây cối/sa mạc/người tuyết bằng mặt bàn hồ sơ lưu trữ 5 bề mặt (`#F4F1EA` giấy báo, `#C9BB9C` kraft, sổ kế toán, blueprint, broadsheet), chồng hồ sơ giấy đa lớp, ghim đồng & sợi chỉ đỏ nối bằng chứng (`H4_TETHER`).
  2. `print_textures.js` tạo Dynamic Canvas2D Print Textures in tiêu đề cảnh, nguồn báo và con số kiểm chứng từ `timeline.json` trực tiếp lên mặt 3D của `chart`, `ledger`, `contract`, `hanko-stamp`, `forensic-loupe`, `brass-caliper`, `book` kèm font CJK (`Noto Sans CJK KR`/`JP`).
  3. Camera 3D giữ **Side-Aware Card Framing** (dịch tâm chiếu sang phía đối diện khi có Note Card để không che prop), nâng góc `low`, vá tọa độ cục bộ `brass-caliper`, và giữ nhịp động học `motion.js`.
  4. Chạy `--stills-only` kết xuất ~12 ảnh PNG đại diện (`quality=vox`) để audit thị giác trước khi chạy `render_parallel.mjs --workers 2 --quality vox --render-fps 15 --frame-format jpeg` xuất `30fps CFR` lossless `-c:v copy`.

---

### [FT-303] Voice-First Real ASR, Procedural Foley SFX Mixer & Lossless Master Assembly
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s09_voice_tts.py`, `vox/ffmpeg_utils.py`, `stages/s10_render.py`
- **Hàm/Service**: `_synthesize_edge_tts_stream`, `_resolve_tts_voice`, `normalize_audio_ebur128`, `_measure_words_with_faster_whisper`, `_reconcile_script_casing_onto_whisper`, `build_procedural_foley_inputs_and_filter`, `mix_papertrails_foley_sfx`, `_validate_and_assemble_video`
- **Input Contract**: `S03` narration script, `timeline.json` (`foley_cues`) & `master_papertrails.mp4`
- **Output Contract**: `audio/voice_narration.mp3` + `word_timestamps.json` + `transcript_segments.json`, `10_render/final.mp4` + `chapters.txt`
- **Logic cốt lõi**:
  1. S09 chọn giọng theo đúng `market` (cấm preset EN ghi đè KR/JA/VN), bắt `WordBoundary` thật của Edge-TTS, chuẩn hóa EBU R128 hai bước (`-15.5 LUFS`, `TP <= -2.5 dBTP`), truyền `initial_prompt` vào `faster-whisper` (`small`, `int8`, FFmpeg 16kHz float32 PCM) và đối chiếu many-to-one theo trọng số ký tự với kịch bản S03 đã duyệt để giữ 100% chính tả tên riêng mà không lệch thời gian thực.
  2. S10 giữ nguyên video stream `-c:v copy` từ `master_papertrails.mp4`, tổng hợp Procedural FFmpeg Foley SFX biến thiên theo `seed` đặt đúng `adelay` millisecond theo `foley_cues`, chạy hai bước `loudnorm` (`-15.5 LUFS, -2.5 dBTP`), và đồng bộ `remotion_props.json` & `chapters.txt`.

---

### [FT-205] Ground-Truth Timeline & Forensic QC Gate
- **Trạng thái**: `ACTIVE`
- **File Code**: `stages/s11_qc.py`, `vox/qa/gates.py`
- **Hàm/Service**: `run`, `verify_final_video_gates`
- **Input Contract**: `10_render/final.mp4`, `director_plan.json`, `remotion_props.json`
- **Output Contract**: `s11_qc/artifact.json` (`qc_verdict: "PASS"`)
- **Logic cốt lõi**: Kiểm toán stream H.264/AAC, 0 khung hình đen, không đứng hình > 1.2s (`Rule 140`), âm lượng EBU R128 `[-17.0, -15.0] LUFS` & `<= -2.0 dBTP`, và đối khớp thời lượng giọng đọc.

---

## Legacy Quarantined Engines (`FT-201` / `FT-203` / `FT-204` / `FT-206` / `FT-207`)
- **Trạng thái**: `QUARANTINED_LEGACY`
- **Ghi chú**: Đã bị bỏ qua hoàn toàn trong luồng `prod` (`PAPERTRAILS_VOICE_FIRST_STAGES`). Các hàm helper cũ trong `stages/s05_director_plan.py` và `stages/s10_render.py` chỉ giữ lại cho bộ kiểm thử `e2e_min` / tương thích ngược unit test cho tới khi dọn bỏ hoàn toàn.
