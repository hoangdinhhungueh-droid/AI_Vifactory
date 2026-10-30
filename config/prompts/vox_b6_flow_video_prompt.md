# 🏛️ CANONICAL VOX VIDEO PROMPT ENGINE (B6 FLOW VIDEO & REMOTION PIPELINE)

> **QUY CHUẨN ĐẠO DIỄN CHUYỂN ĐỘNG VÀ SINH VIDEO I2V VOX ENGINE V3.**  
> Tích hợp 100% chuẩn mực từ **CL3 Vox Video System** (`config/prompts/cl3_vox_engine/video_prompts_system.md`).  
> Ràng buộc trực tiếp các dịch vụ sinh video qua Google Flow (Veo 3.1 - Fast / Omni 1.1 Flash) và Remotion VPS.

---

## 🧭 I. BỐ CỤC KHẮC CỐT GHI TÂM (CANONICAL 4-BLOCK PROMPT STRUCTURE)

Mọi prompt video I2V truyền vào mô hình sinh video BẮT BUỘC tuân thủ đúng 4 khối:
1. `[STYLE BLOCK]` (Khối phong cách cố định: Flat Parallax, Deep Diorama, hoặc Locked Stage).
2. `SHOT:` (Khối 5 nhịp: Background, Midground, Foreground, Kinetic Contact Dynamics, Camera Move kết thúc bằng Settle).
3. `AUDIO:` (Thiết kế âm thanh xúc giác, không nhạc nền, không lồng tiếng).
4. `AVOID:` (Bộ lọc loại bỏ 3D CGI bóng bẩy, text rác, chuyển cảnh đột ngột).

---

## 🎬 II. 3 CHẾ ĐỘ PHONG CÁCH (THE 3 STYLE BLOCKS)

### 1. Chế độ A: Flat Parallax (Tài liệu điều tra & Dữ liệu kiểm toán)
Dành cho các phân cảnh phân tích chứng từ, bóc tách dòng tiền, đọc báo cáo tài chính.
- Máy quay trôi chậm $\le 2\%$, góc nhìn trực diện hoặc nghiêng nhẹ.
- Các lớp giấy tách lớp rõ ràng, thị sai (parallax) tự nhiên, không 3D giả tạo.

### 2. Chế độ B: Deep Diorama (Điện ảnh, Khủng hoảng & Bước ngoặt kịch tính)
Dành cho cảnh mở màn (Hook 0-60s), phát hiện ngòi nổ, và đại cảnh phơi bày sự thật (Smoking Gun).
- Máy quay là một diễn viên (Camera is an actor): Lướt giữa các tầng giấy, bổ nhào (dive), xoay góc (orbit), hoặc lia nhanh (whip) với 1 chuyển động duy nhất.
- Chiều sâu trường ảnh hẹp (shallow depth of field), vật thể tiền cảnh lướt sát ống kính.

### 3. Chế độ C: Locked Stage (Sân khấu giấy cố định)
Dành cho các phân cảnh đối thoại nhân vật hoặc tranh luận thể chế.
- Mặt bàn nền khóa cứng (#F4F1EA), máy quay tĩnh hoặc vi trôi rất nhẹ.
- Chuyển động tập trung 100% vào việc đưa đạo cụ, thước kẹp, con dấu và thẻ số liệu khổng lồ vào vị trí.

---

## ⚡ III. 7 HỌ ĐỘNG LỰC HỌC CƠ HỌC ($H_1 \to H_7$) VÀ NHỊP THỜI GIAN

1. **Bứt tốc tức thì ($\le 0.4\text{s}$)**: Mọi thao tác dập dấu, kẹp thước, cắt giấy, cắm ghim BẮT BUỘC diễn ra dứt khoát trong $0.2\text{s} - 0.4\text{s}$ kèm độ nảy cơ học (overshoot).
2. **Khóa cứng điểm đỗ (Dead-Stop Hold)**: Ngay sau va chạm, vật thể đứng im bất động tại tọa độ va chạm. CẤM kéo dài chuyển động chậm chạp lê thê suốt 5–8s.
3. **Thớ giấy sống 12fps (Living Hold on Twos)**: Trong suốt thời gian giữ khung hình, duy trì vi rung thớ giấy báo và nhịp thở bóng đổ $\le 2\text{px}$ ở 12fps.
4. **Điểm đỗ máy quay bắt buộc (`Settle on...`)**: Mọi cú máy BẮT BUỘC kết thúc bằng câu lệnh `Settle on [target] in sharp focus`.

---

## 📄 IV. THAM CHIẾU HỆ THỐNG GỐC

- Tài liệu hướng dẫn chi tiết T2I: `config/prompts/cl3_vox_engine/image_prompts_system.md`
- Tài liệu hướng dẫn chi tiết I2V: `config/prompts/cl3_vox_engine/video_prompts_system.md`
- Bảng màu & Phong cách chuẩn: `config/prompts/cl3_vox_engine/(Optional) Reference Image Prompt.txt`
- Hình mẫu phong cách trực quan: `config/prompts/cl3_vox_engine/Example Style Reference.png`
