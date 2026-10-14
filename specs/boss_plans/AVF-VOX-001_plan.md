  PUSH_IN = "push_in"                  # zoom 1.00→1.20
    PULL_OUT = "pull_out"                # zoom 1.20→1.00
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    KEN_BURNS_TL_BR = "ken_burns_tl_br"  # zoom + chéo
    KEN_BURNS_BR_TL = "ken_burns_br_tl"
    PARALLAX_LEFT = "parallax_left"      # BG chậm, FG nhanh theo depth
    PARALLAX_RIGHT = "parallax_right"
    ROLL_PUSH = "roll_push"              # zoom 1.0→1.15 + roll ±2°

class FGObject(BaseModel):
    id: str
    prompt: str = Field(min_length=10)
    anchor_x: float = Field(ge=0.0, le=1.0)   # tâm theo tỷ lệ khung
    anchor_y: float = Field(ge=0.0, le=1.0)
    scale: float = Field(ge=0.1, le=0.8)      # cạnh FG / chiều cao khung
    depth: float = Field(ge=0.0, le=1.0)      # 0 = sát BG, 1 = sát camera
    enter_at: float = Field(ge=0.0)           # giây, tương đối trong scene

class Scene(BaseModel):
    idx: int
    narration: str = Field(min_length=1)
    bg_prompt: str = Field(min_length=10)     # yêu cầu: không có chủ thể chính
    fg: list[FGObject] = Field(min_length=1, max_length=3)
    camera: CameraMove
    start: float | None = None                # được align.py điền vào
    end: float | None = None

class ScenePlan(BaseModel):
    title: str
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def _camera_variety(self):
        # Không cho 2 scene liền nhau dùng cùng camera move
        for a, b in zip(self.scenes, self.scenes[1:]):
            if a.camera == b.camera:
                raise ValueError(f"scene {a.idx}/{b.idx} trùng camera {a.camera}")
        return self

class Word(BaseModel):
    text: str           # lấy từ script gốc, không lấy từ Whisper
    start: float
    end: float
    scene_idx: int

class WordTimeline(BaseModel):
    words: list[Word]
    audio_duration: float
    match_ratio: float  # tỷ lệ token script khớp được với Whisper
```

### Ràng buộc toán học cho camera (`camera.py`)

Ký hiệu: s là zoom (s ≥ 1.0), (dx, dy) là offset tâm viewport theo tỷ lệ kích thước canvas. Điều kiện để viewport không lọt ra ngoài canvas:

|dx| ≤ (s − 1) / (2s) và |dy| ≤ (s − 1) / (2s)

Mọi move dùng easing `ease_in_out_cubic`. FG có hệ số parallax là `1 + depth × k`, với k = 0.6. Hàm chính:

`move_transform(move, t_norm, canvas_wh, out_wh) -> np.ndarray (2×3)`

Hàm này phải là hàm thuần và deterministic.

## 4. Task Decomposition for Worker

Mỗi task có input, output và lệnh "done when" riêng. Làm tuần tự trên branch `refactor/vox-single-pipeline`.

**T0. Inventory legacy (chỉ đọc, chưa xóa)**
- Input: repo hiện tại.
- Việc cần làm: chạy `git ls-files`. Viết `scripts/legacy_inventory.py` dùng AST để dựng import graph bắt đầu từ các entrypoint hiện có. Tìm mọi pipeline đang tồn tại: các hàm `main`, CLI, workflow.
- Output: `legacy_inventory.json` gồm `{keep: [...], remove: [...], reuse_candidates: [...]}`. Danh sách `reuse_candidates` là các đoạn code TTS, image gen hoặc ffmpeg có thể port sang `vox/`.
- Điểm dừng: trình danh sách `remove` cho user duyệt trước khi sang T10.

**T1. `schemas.py`** theo đúng contract ở mục 3.
- Done when: `pytest tests/vox/test_schemas.py` pass. Test phải bao gồm trường hợp camera trùng liền kề bị reject, và FG > 3 bị reject.

**T2. `camera.py`** gồm 12 move và hàm `move_transform`.
- Done when, với mỗi move, sample 60 giá trị t:
  - Bốn góc viewport map ngược về luôn nằm trong canvas (0 vi phạm).
  - Frame t=0 và t=1 khác nhau, trừ `static_breath`: yêu cầu chênh lệch zoom ≥ 0.02.
  - Không có bước nhảy: chênh lệch giữa hai frame liền kề ≤ 1.5% chiều rộng khung.

**T3. `tts.py`**: port từ `reuse_candidates`.
- Output: `narration.wav`, mono, 48 kHz.
- Gate: duration > 0, peak ≤ −1 dBFS, không có khoảng lặng > 1.5 s ở giữa bài.

**T4. `align.py`**: faster-whisper (`large-v3` hoặc `medium`) với `word_timestamps=True`, sau đó align với token script bằng `difflib.SequenceMatcher` / Needleman-Wunsch.
- Gate:
  - `match_ratio ≥ 0.95`.
  - Timestamps đơn điệu, mỗi từ có `end > start`.
  - Từ cuối có `end ≤ audio_duration + 0.05`.
  - Mỗi scene có `start`/`end` lấy từ từ đầu và từ cuối của scene đó, không có gap giữa các scene.

**T5. `assets_bg.py`**
- Output: `bg_{idx}.png`, tỷ lệ 16:9, upscale lên 2400×1350.
- Gate:
  - Đúng kích thước.
  - Ảnh không phẳng: độ lệch chuẩn luminance > 12.
  - Có seed và prompt hash ghi trong manifest.

**T6. `assets_fg.py` và `cutout.py`**
- Output: `fg_{idx}_{id}.png`, RGBA 1024×1024.
- Gate cho mỗi FG:
  - Diện tích alpha > 0.5 nằm trong khoảng [5%, 85%].
  - Có ≥ 0.5% pixel alpha mềm (giá trị 1–254), chứng minh viền không bị răng cưa.
  - Viền ngoài 8 px có alpha trung bình < 0.05, nghĩa là chủ thể không bị cắt mép.
  - Bbox của alpha không chạm cạnh ảnh.

**T7. `karaoke.py`**: tạo file ASS 1920×1080.
- Format: tối đa 2 dòng, mỗi dòng ≤ 42 ký tự, mỗi event ứng với một cụm từ, dùng tag `\kf` theo từng từ.
- Done when: parse ngược file ASS và tính lại timing từng từ, sai lệch so với WordTimeline ≤ 10 ms (giới hạn của đơn vị centisecond trong ASS).

**T8. `compositor.py`**: render từng scene, gồm BG warp theo camera, các FG overlay theo depth và parallax, FG fade-in 8 frame tại `enter_at`. Pipe rgb24 vào ffmpeg.
- Done when, với mỗi clip:
  - Đúng 1920×1080, 30 fps.
  - Số frame bằng `round((end − start) × 30)`, sai lệch ±1.
  - `blackdetect` trả về 0 đoạn.

**T9. `assemble.py` và `pipeline.py`**: concat các clip, mux audio, burn ASS, loudnorm.
- CLI duy nhất: `python -m vox.pipeline run --script X --out Y`.
- Ghi `manifest.json` gồm mọi asset, hash và kết quả từng gate.
- Pipeline fail ngay khi bất kỳ gate nào fail. Không cho phép tiếp tục chạy khi đã fail.

**T10. Gỡ legacy** (chỉ làm sau khi user duyệt danh sách T0)
- Dùng `git rm` cho các file trong `remove`. Gỡ các dependency không còn dùng khỏi `requirements` / `pyproject`. Cập nhật README cho entrypoint mới.
- Done when:
  - `grep` không còn tham chiếu nào tới module đã xóa.
  - Toàn bộ test suite pass.
  - Chạy lại `legacy_inventory.py` cho kết quả `remove` rỗng.
- Commit bằng `git add` theo từng đường dẫn cụ thể. Không dùng `git add .`.

**T11. Golden e2e**: chạy pipeline trên `golden_script.txt`, sinh thật, không mock. Lưu `manifest.json` làm baseline để so sánh về sau.

## 5. Verification Protocol & Acceptance Criteria

**Lệnh bắt buộc, tất cả phải trả về exit code 0:**

```bash
python -m py_compile $(git ls-files 'vox/*.py' 'tests/vox/*.py')
pytest tests/vox -q
python -m vox.pipeline run --script tests/vox/fixtures/golden_script.txt --out out/golden
python -m vox.qa.gates verify out/golden/manifest.json
```

**Acceptance cho video cuối** (do `vox/qa/gates.py` kiểm, dùng ffprobe/ffmpeg trên file thật):

| Tiêu chí | Ngưỡng |
|---|---|
| Video stream | h264, yuv420p, 1920×1080, 30 fps CFR |
| Audio stream | AAC, 48 kHz |
| Duration | Bằng duration của audio, sai lệch ±0.1 s |
| Loudness | `ebur128`: −14 LUFS ±1, true peak ≤ −1 dBTP |
| Black frames | `blackdetect=d=0.1`: 0 đoạn |
| Frozen frames | `freezedetect=n=0.001:d=2`: 0 đoạn |
| Karaoke | Sai lệch timing từng từ trong ASS so với WordTimeline ≤ 10 ms; mọi từ của script đều xuất hiện |
| Camera | Mỗi scene đúng move trong plan, không có 2 move liền kề trùng nhau, tổng số move khác nhau ≥ min(12, số scene) |
| Assets | Mọi BG và FG pass gate T5/T6, có ghi trong manifest |

**Quy tắc zero-mock:**
- Không dùng `unittest.mock`, `MagicMock` hay monkeypatch cho model, API hoặc ffmpeg. CI kiểm bằng lệnh `grep -rE "mock|MagicMock|monkeypatch" tests/vox` phải trả về rỗng.
- Test camera và schema chạy trên phép tính thật. Test align, cutout và e2e chạy trên golden fixture được sinh thật.

**Điều kiện hoàn tất:**
- Toàn bộ lệnh trên pass.
- `legacy_inventory.py` báo 0 file chết.
- Tồn tại đúng một entrypoint sinh video trong repo.

Một điểm cần bạn chốt trước T10: chỉ `git rm` rồi commit thường (mặc định của plan), hay rewrite cả history? Rewrite history cần force push và sẽ làm hỏng clone của mọi người đang dùng repo.