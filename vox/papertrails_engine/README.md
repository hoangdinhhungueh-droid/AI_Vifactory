# Papertrails Video — đưa voice vào, nhận MP4

Skill dùng qua **Claude Code, Cursor Agent, Codex hoặc Hermes** có quyền chạy lệnh và đọc/ghi file trên máy. Đây không phải plugin thiết kế website, không phải app upload MP3, cũng không phải model AI sinh video.

Luồng dùng: **một voice → nhận dạng lời nói và thời gian → agent tự hiểu nội dung, dàn cảnh → hoạt hình thế giới giấy → MP4 giữ nguyên voice + phụ đề**. Không bắt bro viết thêm kịch bản hoặc storyboard.

Engine nền lấy từ Papertrails của Shikhar (xikhar), giữ nguyên mã gốc/asset và MIT notice. Lớp video bổ sung timeline, đạo cụ minh họa, camera và xuất video; game gốc vẫn có entry riêng.

## Gói có gì

- `SKILL.md`: chỉ dẫn làm trọn quy trình, không dừng ở việc lập kế hoạch.
- `scripts/pipeline.py`: đo voice, ASR local CPU, tạo transcript/caption/timeline, kiểm MP4.
- `scripts/render.mjs`: frame renderer Three.js → FFmpeg → MP4.
- `engine/`: mã/asset gốc và entry dựng video, không cần lấy lại ảnh từ mạng.
- `scripts/setup.py`: cài runtime tại chỗ, không sửa cấu hình agent toàn cục.
- `scripts/install.py`: chép skill vào Claude/Cursor/Codex/Hermes, mặc định chỉ xem trước đường dẫn.
- `references/`: setup, schema timeline và luật dàn cảnh.
- `rights/`: nguồn và giấy phép.
- `tests/`: regression tests. Independent engineering QA artifacts remain in the working source folder and are excluded from portable installs.

## 1. Cài vào agent muốn dùng

Mở terminal ở thư mục chứa file README này. `--project` là dự án nơi bro sẽ gọi agent, **khác** thư mục gói skill.

```text
python scripts/install.py --agent claude --project "<duong-dan-du-an>"
python scripts/install.py --agent claude --project "<duong-dan-du-an>" --apply
```

Thay `claude` bằng `cursor` hoặc `codex`. Đích tương ứng:

| Agent | Nơi cài trong dự án |
|---|---|
| Claude Code | `.claude/skills/papertrails-video/` |
| Cursor | `.cursor/skills/papertrails-video/` |
| Codex | `.agents/skills/papertrails-video/` |
| Hermes | `$HERMES_HOME/skills/papertrails-video/` của profile đang chạy |

Hermes:

```text
python scripts/install.py --agent hermes
python scripts/install.py --agent hermes --apply
```

Nếu không có `HERMES_HOME`, truyền `--skills-dir "<skills-folder-cua-profile-dang-dung>"`. Không đoán profile khác. Installer không ghi đè bản cũ, không chép `node_modules`, model ASR, voice kiểm thử hoặc video đầu ra. Có thể chỉ giữ gói ở đây và yêu cầu agent đọc `SKILL.md`; không bắt buộc cài toàn cục.

**Chưa có xác minh UI trên cả bốn ứng dụng.** Cấu trúc và đường dẫn bám theo tài liệu chính thức, lệnh cài được kiểm tại thư mục sandbox; không tự tuyên bố đã cài vào tài khoản/app của bro.

## 2. Cài runtime một lần

Trong **bản skill sẽ dùng**, chạy hoặc để agent chạy:

```text
python scripts/setup.py --with-asr
```

Cần Node.js 22.12+, Python 3.12, FFmpeg/ffprobe và uv. Chi tiết/cách không dùng uv: `references/setup.md`.

- ASR chạy CPU tại máy, mặc định Whisper `small`, nhận tiếng Việt.
- Lần đầu cần mạng để lấy npm, Chromium và model; voice không gửi lên API ASR trả phí.
- Đây không phải cam kết hoàn toàn không tốn phí: tài khoản/model của Claude/Cursor/Codex/Hermes vẫn theo gói bro đang dùng. Skill không tự gọi dịch vụ tạo ảnh/video trả phí.

## 3. Dùng: chỉ đưa voice và nói yêu cầu

Ví dụ gửi agent kèm file MP3:

> Dùng papertrails-video, lấy voice này làm video thế giới giấy. Tự chia cảnh minh họa đúng lời, phụ đề tiếng Việt, khung dọc 9:16, giữ nguyên voice, xuất MP4. Không cần hỏi duyệt từng bước.

Nếu không chỉ định, mặc định khung ngang 1920×1080, 30 fps, thời lượng theo voice. Shorts/Reels/TikTok dùng khung dọc 1080×1920.

Agent tự chạy các lệnh này, đọc transcript rồi **tự đạo diễn lại từng cảnh**, không bắt bro chạy:

```text
<ASR_PYTHON> scripts/pipeline.py prepare --audio "voice.mp3" --project "<new-project>" --language vi --format portrait
node scripts/render.mjs "<new-project>/timeline.json" "<new-project>/final.mp4" --quality med
python scripts/pipeline.py verify --video "<new-project>/final.mp4" --timeline "<new-project>/timeline.json"
```

`<ASR_PYTHON>` = `.venv-asr/Scripts/python.exe` trên Windows; `.venv-asr/bin/python` trên macOS/Linux.

Đầu ra: `final.mp4`, `captions.srt`, `transcript.json`, `transcript.txt`, `timeline.json`, `DIRECTION.md`, bản sao voice gốc.

## Giới hạn nói rõ

- **Phần code tự động mới tạo bản nháp bằng từ khóa.** Agent dùng skill phải đọc toàn bộ lời và dựng lại ý nghĩa cảnh. Không có lời hứa một lệnh Python là hiểu mọi câu chuyện.
- Bộ đạo cụ có giới hạn; với chủ đề mới agent phải bổ sung code cảnh. Nhân vật/game nền không tự diễn mọi hành động như model video.
- ASR có thể sai tên riêng hoặc mốc từ. Transcript có sẵn là tùy chọn hỗ trợ, không phải đầu vào bắt buộc thứ hai.
- CPU/WebGL software có thể render chậm. Bản `low` là kiểm kỹ thuật, không đại diện chất lượng xuất cuối.
- Không thay voice bằng giọng AI; không tự tải nhạc/ảnh của người khác.
- Báo cáo chạy thực tế nằm ở `VERIFICATION.md` khi hoàn thành gói. Phân biệt rõ voice kiểm thử tổng hợp với voice thật của người dùng.

## Nguồn

Xem `rights/SOURCES.md`: commit Papertrails được ghim, MIT notice và tài liệu chính thức cho bốn agent. Gói không do Anthropic, Cursor, OpenAI, Nous Research hoặc tác giả Papertrails chứng thực.
