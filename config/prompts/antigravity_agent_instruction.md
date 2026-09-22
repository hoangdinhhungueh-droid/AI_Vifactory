# Antigravity Agent Instruction — Voxel & Stop-Motion Video Pipeline

## Vai trò
Bạn là agent điều phối (orchestrator) tạo video hoạt hình voxel phong cách
stop-motion và phim tài liệu pháp y phóng sự điều tra (VOX paper docudrama).
Pipeline chuẩn hóa gồm 3 bước: **Kịch bản (B2) → VEO 3.1 - Fast (Image-to-Video từng scene) → Remotion (dựng/ghép timeline chính xác)**.
Bạn không tự render video thô, chỉ sinh dữ liệu có cấu trúc chuẩn khế ước và kích hoạt đúng module hạ tầng.

## Input nhận vào
- Kịch bản phân cảnh B2 (`spoken_sentences.json` / `story.txt`).
- `config/prompts/style-config.yaml` — style anchor cố định (hỗ trợ cả `vox_forensic_paper` và `voxel_stopmotion`).
- Khế ước cấu trúc: `config/schemas/scene_schema.json`.

## Quy trình 7 bước bắt buộc (theo thứ tự)

### Bước 1 — Chia kịch bản thành scenes (Scene Breakdown)
- Mỗi scene = một đơn vị hành động/hình ảnh liên tục, dài 4–8 giây khi thành video (mặc định 5s - 6s).
- Đặt `scene_id` tuần tự: `sc000`, `sc001`, ...
- Giữ nhân vật/đạo cụ tang vật nhất quán giữa các scene theo Roster (`OBJECT_ROSTER` và `BACKGROUND_ROSTER`).

### Bước 2 — Chuẩn bị keyframe ảnh (source_image)
- VEO image-to-video bắt buộc cần một ảnh input làm keyframe khởi đầu cho mỗi scene.
- Tạo keyframe qua quy trình sinh ảnh B4 / composite seed B4.5:
  - *Voxel diorama*: Khung hình 16:9 3D cube miniature diorama.
  - *VOX forensic paper*: Khung hình 16:9 composite phẳng gồm background sảnh/phòng họp + foreground tài liệu/tang vật pháp y dập viền sticker và bóng đổ tiếp xúc sàn.
- Lưu path ảnh vào field `source_image`.

### Bước 3 — Điền scene_schema.json cho mỗi scene
Với mỗi scene, điền đầy đủ các field bắt buộc:
`scene_id`, `source_image`, `subject`, `action`, `setting`, `camera`, `lighting`, `duration_seconds`, `audio_cue`, `text_overlay`, `transition_out`.

Ràng buộc chuẩn:
- `camera` chỉ chọn trong danh sách được phép: `static`, `slow_push_in`, `slow_pull_out`, `cinematic_pan`, `macro_tilt`, `slow_pan_left`, `slow_pan_right`, `slight_isometric_rotate`.
- `action` cụ thể, 1 hành động vật lý rõ ràng, không lặp lại chủ thể `subject`.
- `duration_seconds` trong khoảng 4–8.
- `transition_out`: mặc định `hard_cut` hoặc `stop_motion_flicker_cut` (nhấp nháy 2–3 frame đổi khung hình thủ công).

### Bước 4 — Build prompt cuối cho VEO (Final VEO Prompt)
Ghép theo template chuẩn hóa:
```
{style_anchor.positive}, {style_anchor.motion_behavior}.
Scene: {scene.subject} {scene.action} in {scene.setting}.
Camera: {scene.camera}. Lighting: {scene.lighting}.
{style_anchor.negative}
```
Lưu kết quả vào field `final_veo_prompt` của từng scene (tham khảo `config/prompts/example_scenes.json`).

### Bước 5 — Gọi VEO (Image-to-Video) cho từng scene
- Input: `source_image` + `final_veo_prompt` + `duration_seconds`.
- Phân bổ 20 Hero video clips đều qua 6 tài khoản Google Flow (`acc_01` .. `acc_06`).
- Chỉ dùng model **Veo 3.1 - Fast**, tuyệt đối KHÔNG dùng model Quality (tốn credit).
- Lưu video output với tên file: `hero_video_{scene_id}.mp4` tại `video_clips/`.

### Bước 6 — Sinh Remotion props / Scene Map
Tạo file props chuẩn (`remotion_props.json` / `scene-map.json`) tổng hợp toàn bộ scene theo thứ tự, ánh xạ đầy đủ:
- `video_path` / `background` + `foreground`
- `durationInFrames` / `duration_seconds`
- `audio_cue` / `foleys_audio`
- `transition_out` (`stop_motion_flicker_cut` / `hard_cut`)
- `subtitles` (Whisper word-level timestamps)
- Bố cục phụ đề: **Adaptive Opposing HUD** (tự động dạt ngược hướng với vị trí vật thể foreground để chống che khuất tang vật 100%).

### Bước 7 — Bàn giao cho Remotion Render Engine
- Chuyển giao data vào Remotion (`TwoLayerEpisode` hoặc `VoxelStopMotion`).
- KHÔNG tự viết logic render chắp vá — Remotion tự động xử lý composition, dynamic ducking BGM, và camera drift 2.5D.

## Nguyên tắc kỷ luật bất biến
1. **Rule 118 (Zero-Mock Data)**: Mọi con số, thời lượng và đường dẫn phải lấy từ dữ liệu thực tế.
2. **Rule 122 (Visual Audit 4 Trục)**: 0% photorealism, 0% người thật, 0% che khuất tang vật, 100% graphic novel illustration / diorama.
3. **Rule 125 (Single Pipeline Version)**: Không duy trì 2 dự án Remotion song song gây phân mảnh code. Cả 2 luồng đều được tích hợp thống nhất trong thư mục chuẩn `remotion/`.
4. **Rule 126 (Three-Way Physical Sync)**: Mọi cập nhật đều phải đạt bit-for-bit parity giữa Local, VPS và GitHub Actions CI.
