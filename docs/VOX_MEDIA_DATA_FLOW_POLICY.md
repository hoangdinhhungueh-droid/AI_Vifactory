# 📜 VOX MEDIA PIPELINE: CHÍNH SÁCH QUẢN TRỊ THƯ MỤC & LUỒNG DỮ LIỆU ĐỊNH DANH
## (VOX MEDIA DIRECTORY TOPOLOGY & DATA FLOW POLICY SPECIFICATION)

> **Mã tài liệu**: `VF-POL-VOX-001`  
> **Phiên bản**: `1.0.0 (Production Standard)`  
> **Áp dụng**: Toàn bộ quy trình sản xuất Video dạng Vox Continuous Object-Assembly (B3 -> B4 -> Human Gate -> B5 -> B6 -> Remotion).  
> **Ràng buộc**: Tuân thủ triệt để Rule 118 (Zero-Mock), Rule 121 (Forensic Verification), Rule 122 (Visual Audit 4 Trục), Rule 126 (Three-Way Physical Sync), Rule 136 (Zero-Asset-Leak & Pure Post Typography).

---

## 🗺️ I. TỔNG QUAN KIẾN TRÚC THƯ MỤC CẤP TẬP PHIM (`episodes/<EP_ID>/`)

Mỗi tập phim (Episode) là một không gian sản xuất khép kín. Toàn bộ tài nguyên hình ảnh, video clip, metadata và biên bản kiểm toán được lưu trữ theo cấu trúc thư mục phân cụm (Clustered Block Workspace) kết hợp bản sao phẳng (Flat Remotion Mirror):

```
episodes/<EP_ID>/
├── director_plan.json                     # [SOT-01] Khế ước đạo diễn: 140 phân cảnh, ray chuyển động, prompt sạch 100%
├── block_manifest.json                    # [SOT-02] Phân rã 28 Cụm phân đoạn (Sequence Blocks), 5-6 scenes/cụm
├── flow_video_manifest.json               # [SOT-03] Bản đồ phân bổ 140 clips xoay vòng 7 tài khoản Google Flow
├── b5_visual_audit_summary.json           # [AUDIT] Kết quả kiểm toán thị giác B5 (độ phân giải, viền alpha, điểm số)
├── review_gallery.html                    # [GATE-UI] Dashboard duyệt ảnh trực quan 1-click cho User
├── human_gate_checkpoint.json             # [GATE-STATE] Trạng thái dừng kiểm duyệt người dùng (PENDING / APPROVED)
│
├── blocks/                                # 📦 VÙNG DỮ LIỆU PHÂN CỤM (Clustered Block Workspace)
│   ├── BLOCK_1_<BLOCK_SLUG>/
│   │   ├── images/                        # Thư mục gốc chứa ảnh seed do Gemini Pro Web sinh ra
│   │   │   ├── composite_SCENE_01.png     # Ảnh 2560x1440 sạch chữ (chỉ gồm canvas + cutouts + textures)
│   │   │   ├── composite_SCENE_02.png
│   │   │   └── ... (SCENE_01 -> SCENE_06)
│   │   └── videos/                        # Thư mục gốc chứa video clip Veo 3.1 do Google Flow sinh ra
│   │       ├── clip_scene_01.mp4          # Clip 1080p 24fps render theo camera ray chuyển động
│   │       ├── clip_scene_02.mp4
│   │       └── ... (scene_01 -> scene_06)
│   ├── BLOCK_2_<BLOCK_SLUG>/
│   │   ├── images/
│   │   └── videos/
│   └── ... (BLOCK_01 -> BLOCK_28)
│
├── composite_seeds/                       # 🪞 BẢN SAO PHẲNG HÌNH ẢNH (Flat Image Mirror)
│   ├── composite_SCENE_01.png             # Tự động đồng bộ 1:1 từ blocks/*/images/ phục vụ Remotion
│   ├── composite_SCENE_02.png
│   └── ... (SCENE_01 -> SCENE_140)
│
└── video_clips/                           # 🪞 BẢN SAO PHẲNG VIDEO (Flat Video Mirror)
    ├── clip_scene_01.mp4                  # Tự động đồng bộ 1:1 từ blocks/*/videos/ phục vụ Remotion ghép nối
    ├── clip_scene_02.mp4
    └── ... (clip_scene_01 -> clip_scene_140)
```

---

## 🔄 II. MA TRẬN LUỒNG DỮ LIỆU ĐỊNH DANH GIỮA CÁC BƯỚC (STAGE HANDOFF CONTRACTS)

Mọi công cụ và script trong pipeline bắt buộc đọc và ghi dữ liệu tại các vị trí chính xác tuyệt đối sau:

| Giai Đoạn (Stage) | Script Điều Phối | Thư Mục / File ĐẦU VÀO (Input) | Thư Mục / File ĐẦU RA (Output) | Cơ Chế Xác Thực & Chặn Lỗi |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1 & 2: Recon & Script** | B1, B1.5, B2 | Trend RSS, YouTube Intel | `story.txt`, `grounding_intel.json` | Khắc sâu 7 Golden Pillars, 5 Act Docudrama, Rule 130/131. |
| **🛑 HUMAN GATE 1 (HG1)** | Telegram Notifier | B1-B2 Outputs | User duyệt kịch bản & đề tài | Bắn Telegram noti: `/vox:b3 --episode <EP_ID>` |
| **Stage 3: Director Plan & Prompts** | `scripts/reforge_b3_director.py` | `story.txt`, `vox_b3_director_image_prompt.md` | - `director_plan.json`<br>- `prompts.json` | Quy chuẩn Rule 140: 6.0-8.0s/Beat (~70-75 Beats), 4 thì $S_1..S_4$, vật thể xúc giác, negative prompt cấm chữ. |
| **🛑 HUMAN GATE 2 (HG2)** | Telegram Notifier | `director_plan.json`, `prompts.json` | User duyệt Director Plan & Prompts trước khi tạo ảnh | Bắn Telegram noti: `/vox:image --episode <EP_ID>` |
| **Stage 4: Seed Image Generation** | Gemini Pro Web (Playwright) | `director_plan.json` (trường `image_prompt`) | - `blocks/<BLOCK_NAME>/images/composite_SCENE_XX.png`<br>- Tự động sao chép sang `composite_seeds/` | Ảnh phải đạt chuẩn 2560x1440 hoặc 1920x1080 PNG; không dính watermark; không rò rỉ typography/phụ đề. |
| **Stage 4.5: Visual Audit & Gallery** | Visual Critic Council | `blocks/<BLOCK_NAME>/images/*.png` | - `b5_visual_audit_summary.json`<br>- `review_gallery.html` | Đạt chuẩn 10/10 độ phân giải, kiểm toán viền cutout; xuất file HTML để người dùng mở xem ngay lập tức. |
| **🛑 HUMAN GATE 3 (HG3 - MỚI)** | Telegram Notifier | `review_gallery.html`, ảnh seed | User duyệt Gallery ảnh seed sạch chữ. Nếu OK $\rightarrow$ tạo DEMO video clip Act I | Bắn Telegram noti: `/vox:video --episode <EP_ID> --mode demo` |
| **Stage 5A: Demo Video Gen (Act I)** | `flow_video_dispatcher.py` | 8-10 ảnh seed Act I | `video_clips/clip_scene_01..10.mp4` | Chạy 8-10 clips Act I qua 7 tài khoản Google Flow để User kiểm tra chuyển động. |
| **Stage 5B: Full Video Gen (7 Acc)** | `flow_video_dispatcher.py` | Toàn bộ 70-75 ảnh seed | Toàn bộ `video_clips/*.mp4` | Luân phiên 7 profile Chrome độc lập (`acc_01` -> `acc_07`); kiểm tra dung lượng MP4 > 100KB; verify exit code 0. |
| **🛑 HUMAN GATE 4 (HG4 - MỚI)** | Telegram Notifier | Toàn bộ video clips raw | User duyệt Full raw video clips. Nếu OK $\rightarrow$ tự động đi full luồng còn lại | Bắn Telegram noti: `/vox:render --episode <EP_ID>` |
| **Stage 6: Remotion Video Assembly** | Remotion Engine (VPS CPU) | `video_clips/*.mp4`, Whisper timestamps, BGM | `renders/<EP_ID>_master.mp4` | Chèn chữ phụ đề và motion graphics động trong Remotion (Hậu kỳ); video clips nền hoàn toàn sạch nhiễu. |
| **Stage 7: Forensic QC & Upload** | B8 QC & B10 Upload | Master MP4, SEO Payload | YouTube Unlisted Video (Unpublic) | Rule 135 Chapters chính xác, `status.containsSyntheticMedia: true`. |
| **🛑 HUMAN GATE 5 (HG5)** | Telegram Notifier | YouTube Unlisted Link, Chapters | User duyệt bản Unlisted cuối cùng trước khi chuyển Public | Bắn Telegram noti kèm link YouTube Unlisted |

---

## 🛡️ III. QUY TẮC BẤT KHẢ XÂM PHẠM VỀ HÌNH ẢNH & CHỮ (ZERO-TEXT MANDATE)

1. **Tuyệt Đối Không Vẽ Chữ Lên Ảnh Bitmap Seed (Rule 136 Extension)**:
   - Ảnh do AI sinh ra (Gemini Pro Web) **CHỈ ĐƯỢC CHỨA**:
     + *Layer 1 (Canvas)*: Nền giấy báo cũ cổ điển (#F4F1EA), bảng ghim điều tra hoặc bàn làm việc phẳng.
     + *Layer 2 (Geometry)*: Mảng màu đồ họa hình học phẳng (Terracotta, Vox Yellow, Navy).
     + *Layer 3 (Negative Space)*: Khoảng không gian trống sạch sẽ 100% để dành chỗ cho Remotion chèn chữ động ở hậu kỳ.
     + *Layer 4 (Tactile Cutouts)*: Vật thể giấy cắt dán vật lý nổi bật viền trắng 2-4px deckle edge và đổ bóng nhẹ (con thuyền, tờ trát thuế, hòn đảo, con dấu sáp).
     + *Layer 5 (Vintage Texture)*: Hạt giấy, vân in ấn misregistration cổ điển.
   - **CẤM TUYỆT ĐỐI**: Không nhồi tiêu đề, không chèn ngày tháng trôi nổi, không vẽ chữ phụ đề, không đóng dấu `"BEAT 1"`, `"BEAT 2"` lên ảnh bitmap.

2. **Chữ Đồ Họa Và Phụ Đề Thuộc Về Hậu Kỳ Remotion (Pure Remotion Typography)**:
   - Toàn bộ typography (tiêu đề phân cảnh, số liệu, dòng trích dẫn, phụ đề karaoke) được render động dạng SVG/Vector trong Remotion, đồng bộ chính xác từng mili-giây theo Whisper timestamps.
   - Nhãn nội bộ như `"BEAT 1"`, `"BEAT 2"` bị loại bỏ vĩnh viễn khỏi mọi giao diện người xem; thay thế bằng nhãn chủ đề biên tập sạch (`TAX INVOICE`, `COURT RULING`, `REVENUE SCALE`).

---

## 🌐 IV. PHÂN ĐỊNH KHÔNG GIAN THỰC THI: LOCAL (WINDOWS) VS VPS (LINUX)

| Tài Nguyên / Tác Vụ | Môi Trường Local Windows | Môi Trường Hetzner VPS | Cơ Chế Đồng Bộ Hóa |
| :--- | :--- | :--- | :--- |
| **Tự động hóa trình duyệt (Browser Automation)** | **CHÍNH (Primary)**: Chạy Gemini Pro Web (profile Google Pro cá nhân) và Google Flow 7 tài khoản (`acc_01` -> `acc_07`) với GUI native mượt mà. | Không khuyến nghị chạy browser automation GUI vì CAPTCHA/Cloudflare và tài nguyên RAM headless. | N/A |
| **Lưu trữ Cụm Thư mục Blocks & Flat Mirrors** | **CHÍNH (Primary)**: Lưu tại `episodes/<EP_ID>/` để phục vụ xem trực quan bằng `view_file` và `review_gallery.html`. | **ĐỒNG BỘ (Synced)**: Lưu tại `/var/vf/episodes/<EP_ID>/` hoặc `/root/video_factory/episodes/<EP_ID>/`. | Tự động đóng gói `.tar.gz` và upload qua SSH/SCP khi hoàn thành stage. |
| **Kiểm Toán Thị Giác B5 & Human Gate** | **CHÍNH (Primary)**: User duyệt trực tiếp trên Windows qua trình duyệt click mở ảnh 2K. | Lưu bản sao json audit để CI/CD đối soát tính toàn vẹn. | Git commit hoặc SSH sync. |
| **Remotion Video Rendering (B6, B7)** | Có thể test preview cục bộ nếu cần. | **CHÍNH (Primary)**: Server Hetzner 16-Core chuyên dụng thực thi render Remotion CPU không nghẽn máy người dùng. | Local upload asset hoàn chỉnh lên VPS $\rightarrow$ VPS render master MP4. |

---

## 🎯 V. HƯỚNG DẪN THAO TÁC 1-LỆNH CHO USER

- **Để sinh toàn bộ ảnh hoặc 1 cụm Block và tự động audit**:
  ```bash
  python scripts/run_vox_media_pipeline.py --episode KR_EP0001_google_kr_tax_loss --limit-blocks 1
  ```
- **Khi pipeline dừng tại Human Audit Gate**:
  - Mở file `episodes/KR_EP0001_google_kr_tax_loss/review_gallery.html` trong trình duyệt.
  - Kiểm tra 6 ảnh: Đảm bảo nền giấy cắt dán sắc nét, **100% không dính chữ phụ đề hay BEAT thừa**.
- **Khi đồng ý cho phép tạo video Veo 3.1**:
  - Chạy lệnh kích hoạt:
  ```bash
  python scripts/trigger_video_generation.py --episode KR_EP0001_google_kr_tax_loss --limit-blocks 1
  ```
  *(hoặc click đúp file `trigger_video.bat` trên Windows)*.
