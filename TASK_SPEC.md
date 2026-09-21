# 📐 [TASK_SPEC] VOX_OBJECT_DRIVEN_DOCUDRAMA_OVERHAUL

## 📌 1. Bối Cảnh & Ranh Giới (Context & Boundaries)
- **Feature Title**: Radical VOX / Netflix Investigative Docudrama Overhaul — 100% Tangible Evidence Objects & Continuous Kinetic Montage.
- **Target Episode ID**: `EN_EP0004_amazon_ad_lawsuit`
- **Primary Blocks Impacted**:
  - `B3.0` (`app/services/director_planner_b3.py` & `scripts/rebuild_en0004_director_plan.py`): Triệt tiêu 100% nhân vật hoạt hình toàn thân đứng trước máy quay; chuyển đổi toàn diện sang cốt truyện dẫn dắt bằng tang vật điều tra (Forensic Evidence Exhibits).
  - `B3.5` (`app/services/prompt_forge.py`): Nhận diện tự động các từ khóa tang vật (`doc`, `evidence`, `object`, `prop`, `item`, `meter`, `invoice`, `check`, `paper`, `artifact`, `ledger`, `gauge`, `statute`, `envelope`, `stamp`), tạo prompt 1:1 sticker cutout trên phông nền #FF00FF magenta phẳng.
  - `B4/B5` (`vf-image-gen` & HSV Chroma Keying): Sinh 22 asset 2K DCI chuẩn (14 FG Evidence Objects + 8 BG Environments), tách nền HSV sạch 100% viền, 0% magenta bleed, 0% UI artifacts.
  - `B6.0` (`scripts/orchestrator/adversarial_director_gate.py`): Hiệu chuẩn chốt kiểm toán tỷ trọng FG — phân định nhân vật người (trần 20% / 12 scenes) và tang vật điều tra (cho phép 50-55% / ~60 scenes), auto-repair phân bổ đều 5 Beat.
  - `B6.5` (`scripts/update_and_build_props.py` & `app/services/build_remotion_props.py`): Tái lập `remotion_props.json` chuẩn 131 scenes, 60 scenes có tang vật FG, karaoke đồng bộ từng từ.
  - `B7.0 / B8.0` (`scripts/render_twolayer_chunks.py` & Remotion TwoLayerEpisode): Render 5 chunk Beat-based, ghép nối lossless stream-copy (`-c copy`), tự động dọn dẹp chunk trung gian giải phóng ổ cứng VPS, tự động kích hoạt B9/B10/Gate 3.

---

## 🎯 2. Yêu Cầu Kỹ Thuật (Requirements R1 - R6)
- **R1 (Zero Generic Cartoon Humans)**: Loại bỏ triệt để các hình vẽ hoạt hình nhân vật đứng tạo dáng đơ. 100% nhân vật lịch sử/thực tế chỉ xuất hiện dưới dạng ảnh hồ sơ điều tra (dossier photo) kẹp ghim trong tệp tài liệu vụ án.
- **R2 (Tangible Forensic Evidence Objects)**: 14 tang vật pháp y sắc nét (Hồ sơ khởi kiện FTC, Hộp tìm kiếm tài trợ Amazon, Đồng hồ đo Soft Reserve 30%->80%, Hóa đơn thiệt hại 20 tỷ USD, Nhật ký đấu thầu mili-giây, Phong bì niêm phong mật, Sổ cái ngân hàng tiểu thương Ohio, Bộ luật chống độc quyền, Ổ cứng máy chủ, Bản hợp đồng bôi đen, Tập hồ sơ bồi thường, Con dấu hồ sơ Lina Khan & Andy Jassy, Búa công lý & cán cân đồng).
- **R3 (Cinematic Contrast & VOX Sticker Cutout)**: Bối cảnh Layer 1 mờ tối (`brightness(0.78) saturate(0.68) blur(1.2px)`) + Viền sticker trắng dập nổi (`drop-shadow(0 0 2px white)` + đổ bóng 3D sâu) trên Layer 2 giúp tang vật nổi bật tuyệt đối, không tiếp màu vào nền.
- **R4 (Continuous Kinetic Montage & Calibrated Gate)**: Nâng trần cho phép tang vật pháp y trong `adversarial_director_gate.py` lên 55% (~60 scenes / 131 scenes) để duy trì nhịp dựng tài liệu điều tra dồn dập, tránh khoảng trống hình ảnh 16 phút.
- **R5 (VPS Disk Pressure Relief)**: `render_twolayer_chunks.py` tự động xóa các file chunk MP4 trung gian ngay sau khi ghép nối thành công vào `twolayer_silent.mp4`, giải phóng 400-500MB ổ cứng VPS.
- **R6 (Three-Way Physical Parity & CI Verification)**: Đồng bộ vật lý 100% bit-for-bit giữa VPS (`/root/video_factory`), GitHub repository (`origin/main`), và Local Windows workspace; GitHub Actions CI đạt `conclusion: success` (exit code 0).

---

## 🔒 3. Khế Ước Giao Diện (Interface Contracts)
- **Asset Manifest Contract (`manifest.json`)**:
  - 14 Foreground Evidence Objects (`layer_type: "Foreground"`, Status: `Approved`, RGBA PNG 2048x2048)
  - 8 Background Environments (`layer_type: "Background"`, Status: `Approved`, RGB PNG 2560x1440)
- **Director Gate Verdict Contract (`director_gate_report.json`)**:
  - `verdict: "PASS"`
  - `defects_found_initial: 0`
  - `overlay_density_pct <= 35.0%`
  - `foreground_evidence_count: 60` (45.8% density)
