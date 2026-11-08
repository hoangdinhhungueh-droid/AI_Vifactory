# 🏛️ CANONICAL VOX DIRECTOR PROMPT (B3 DIRECTOR & STORYBOARD ENGINE)

> **QUY CHUẨN ĐẠO DIỄN NGHỆ THUẬT & PHÂN CẢNH TẬP TRUNG VOX ENGINE V3.**  
> Tích hợp triệt để **Opuscar Core Boxes Architecture** (`lemomo-ai/lemo-opuscar`) và **CL3 Vox Video System** (`config/prompts/cl3_vox_engine/`).  
> Mọi kịch bản phân cảnh S05, storyboard và prompt sinh ảnh/video BẮT BUỘC lấy hệ thống CL3 làm gốc nâng cấp.

---

## 🧭 I. BẢN ĐỒ KIẾN TRÚC KIM CHỈ NAM (CL3 VOX SUITE & OPUSCAR CORE BOXES)

Hệ thống đạo diễn hình ảnh vận hành dựa trên 5 Hộp Cốt Lõi Opuscar và bộ tài liệu gốc tại `config/prompts/cl3_vox_engine/`:

1. **5 Hộp Cốt Lõi Opuscar (Core Boxes)**:
   - `visual-investigation`: Cấu trúc hồ sơ điều tra thực địa, dòng tiền, chứng từ và chuỗi nhân quả logic.
   - `archive-lighttable`: Bàn soi tài liệu ngược sáng lạnh (`#F7F9FB`), hiển thị thớ giấy xuyên thấu, watermark và nét xóa mờ ghost strokes 7% trên bảng trắng.
   - `swiss-motion`: Nghệ thuật tương phản tỷ lệ cực hạn Thụy Sĩ (Swiss extreme scale contrast: số liệu khổng lồ chiếm 30-35% diện tích khung hình đối lập sắc nét với nhãn nguồn IBM Plex Mono trên chip 6x12 siêu nhỏ).
   - `halftone-dossier`: Hồ sơ bán sắc Ben-Day halftone density fields kết hợp con dấu cao su mòn rỗ (pitted rubber stamps) và bóng mực in lệch (+8px misregistration offset pop).
   - `briefing-board`: Bảng tác chiến diorama với cổng kính lúp acrylic méo barrel distortion sắc sai viền, ghim đồng cắm phập và chỉ đỏ liên kết.

2. **Tài liệu quy chuẩn gốc**:
   - **`image_prompts_system.md`**: Hệ thống tạo prompt Text-to-Image (T2I) Paper Diorama 3D, phân tách đa tầng sâu, nhân vật cắt dán halftone đen trắng viền rách với misregistration ink shadow +8px.
   - **`video_prompts_system.md`**: Hệ thống tạo prompt Image-to-Video (I2V) 4 khối bất biến (`[STYLE BLOCK]` -> `SHOT:` -> `AUDIO:` -> `AVOID:`), tích hợp 3 Style Mode (Flat Parallax, Deep Diorama, Locked Stage) và 7 họ động lực học cơ học ($H_1 \to H_7$).
   - **`(Optional) Reference Image Prompt.txt`**: Đặc tả bảng Style Sheet chuẩn (Master Art-Direction Sheet) quy định bảng màu 5 sắc thái (#F4F1EA, #F7F9FB, #C9BB9C, #1A1A1A, #8C8C8C, #D62E1F, #D9A441), type specimen headline caps và component zoo.
   - **`Example Style Reference.png`**: Bản tham chiếu thị giác thực tế được nạp vào mô hình sinh ảnh/video làm style anchor.

---

## ⚡ II. NGUYÊN TẮC BẤT DI BẤT DỊCH TRONG PHÂN CẢNH VÀ ĐỘNG LỰC HỌC S05

1. **Khử tuyệt đối tọa độ Descartes (Rule 140)**: CẤM TUYỆT ĐỐI đưa các chuỗi số học mù quáng dạng `(X: 50%, Y: 30%)` vào prompt I2V. Thay vào đó, định hướng vị trí bằng ngôn ngữ vật lý tự nhiên (`top-down macro perspective`, `sliding into center margin`, `resting above the metric column`).
2. **Khử quái thai từ khóa (Rule 128 & 141)**: CẤM gộp các công cụ không liên quan (như vừa con dấu vừa thước kẹp cùng xuất hiện vô lý). Mỗi phân cảnh chỉ kích hoạt đúng 1 cặp tương tác cơ học chính từ bảng Semantic Archetypes.
3. **Gia tốc bứt tốc snappy cubic-bezier**: Sử dụng đường cong gia tốc `cubic-bezier(.7, 0, .2, 1)` bứt tốc và hồi nảy cơ học (mechanical back-overshoot), ổn định điểm đỗ trong $0.2\text{s} - 0.3\text{s}$.
4. **Cú dập dấu Stamp Slam Opuscar**: Rơi tự do trọng lực trong $0.09\text{s}$ từ tỷ lệ $2.6\times$ xuống $1.0\times$, rung vi chấn dập tắt dần, rung camera 1 frame, chớp trắng $0.5$ flash, và âm thanh mút mực xúc giác (soft ink squelch).
5. **Chuyển động đa tốc độ (Dual-Rate Motion)**: Máy quay di chuyển mượt mà ở 24/30fps, trong khi thớ giấy, bóng đổ bề mặt và nét viền rung nhẹ ở 12fps (on twos).
6. **Công thức kiểm toán thời gian giữ mắt (Readcheck Formula)**:
   $$\text{Hold Time} \ge \max\left(1.8\text{s},\; \frac{\text{chars}}{4.5} + 1.5\text{s},\; \text{VO} + 0.6\text{s}\right)$$
7. **Khoảng lặng tuyệt đối (Two Real Silences)**: Tự động hạ âm lượng BGM (ducking silence) trước cú va chạm dập dấu và thời điểm bóc trần chứng cứ quan trọng.
8. **Một cú máy duy nhất kết thúc bằng `Settle on...`**: Mỗi clip video chỉ có 1 chuyển động máy quay duy nhất và BẮT BUỘC kết thúc bằng chỉ thị điểm đỗ (`Settle on [target] in sharp focus`).
9. **Bảo tồn vùng an toàn phụ đề 20%**: Toàn bộ chủ thể quan trọng và số liệu khổng lồ phải nằm ở 80% phần trên của khung hình. Giữ nguyên 20% đáy màn hình là mặt bàn giấy báo cũ ngả vàng (#F4F1EA) phẳng hoàn toàn trống, tuyệt đối không có chữ hay vật thể để Remotion render phụ đề karaoke 0ms drift không bị va chạm.

---

## 🎨 III. QUY CHUẨN MỸ THUẬT VOX CL3 & HOOK ARCHITECTURE (RULE 128, 131, 140)

1. **Hệ thống thị giác Vox CL3 chuẩn xác (`Example Style Reference.png`)**:
   - Deep 3D paper diorama trên giấy báo cũ ngả vàng lưu trữ (`#F4F1EA`), bìa kraft (`#C9BB9C`), và bàn soi ngược sáng lạnh (`#F7F9FB`).
   - Nhân vật & chủ thể: Cắt dán ảnh halftone đen trắng 60lpi với viền rách trắng thủ công (deckle keylines) và nét bóng mực in lệch (+8px misregistration offset pop).
   - Thành phần xúc giác: Thẻ số liệu khổng lồ (30-35% mass), nhãn nguồn IBM Plex Mono trên chip 6x12, kính lúp acrylic méo barrel distortion sắc sai viền, con dấu cao su mòn rỗ, thước kẹp vernier bằng đồng cổ, sợi chỉ đỏ điều tra kéo căng, mép giấy xé rách tự nhiên.
   - CẤM TUYỆT ĐỐI: Photorealism, bàn khám nghiệm inox (stainless steel forensic tables), găng tay cao su xanh (blue latex gloves), và thẻ tang vật cảnh sát/CSI.
2. **Kiến trúc Hook Beat 1 (Rule 140 / Rule 131)**:
   - Phân rã Beat 1 Hook thành hệ thống 3 đến 4 micro-scenes dứt khoát (3.5s đến 5.0s mỗi scene), tuyệt đối không gộp thành 1 scene nguyên khối.
   - Luân chuyển nhịp nhàng qua 7 họ động lực học cơ học ($H_1 \to H_7$).
3. **Chuẩn hóa Generic cho mọi Episode (Rule 128)**:
   - Áp dụng phổ quát và nhất quán cho mọi thị trường (`EN`, `VN`, `KO`, `JA`) và mọi chủ đề, không hardcode thông tin đặc thù của bất kỳ tập nào.


