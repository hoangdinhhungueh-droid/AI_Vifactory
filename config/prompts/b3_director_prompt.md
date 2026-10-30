# 🏛️ CANONICAL VOX DIRECTOR PROMPT (B3 DIRECTOR & STORYBOARD ENGINE)

> **QUY CHUẨN ĐẠO DIỄN NGHỆ THUẬT & PHÂN CẢNH TẬP TRUNG VOX ENGINE V3.**  
> Tích hợp triệt để **CL3 Vox Video System** (`config/prompts/cl3_vox_engine/`).  
> Mọi kịch bản phân cảnh S05, storyboard và prompt sinh ảnh/video BẮT BUỘC lấy hệ thống CL3 làm gốc nâng cấp.

---

## 🧭 I. BẢN ĐỒ KIẾN TRÚC KIM CHỈ NAM (CL3 VOX SUITE)

Hệ thống đạo diễn hình ảnh vận hành dựa trên bộ 4 tài liệu gốc tại `config/prompts/cl3_vox_engine/`:

1. **`image_prompts_system.md`**: Hệ thống tạo prompt Text-to-Image (T2I) Paper Diorama 3D, phân tách đa tầng sâu, nhân vật cắt dán halftone đen trắng viền rách với nét bóng mực pop lệch sau lưng.
2. **`video_prompts_system.md`**: Hệ thống tạo prompt Image-to-Video (I2V) 4 khối bất biến (`[STYLE BLOCK]` -> `SHOT:` -> `AUDIO:` -> `AVOID:`), tích hợp 3 Style Mode (Flat Parallax, Deep Diorama, Locked Stage) và 7 họ động lực học cơ học ($H_1 \to H_7$).
3. **`(Optional) Reference Image Prompt.txt`**: Đặc tả bảng Style Sheet chuẩn (Master Art-Direction Sheet) quy định bảng màu 5 sắc thái (#F4F1EA, #C9BB9C, #1A1A1A, #8C8C8C, #D62E1F, #D9A441), type specimen headline caps và component zoo.
4. **`Example Style Reference.png`**: Bản tham chiếu thị giác thực tế được nạp vào mô hình sinh ảnh/video làm style anchor.

---

## ⚡ II. 5 NGUYÊN TẮC BẤT DI BẤT DỊCH TRONG PHÂN CẢNH S05

1. **Khử tuyệt đối tọa độ Descartes (Rule 140)**: CẤM TUYỆT ĐỐI đưa các chuỗi số học mù quáng dạng `(X: 50%, Y: 30%)` vào prompt I2V. Thay vào đó, định hướng vị trí bằng ngôn ngữ vật lý tự nhiên (`top-down macro perspective`, `sliding into center margin`, `resting above the metric column`).
2. **Khử quái thai từ khóa (Rule 128 & 141)**: CẤM gộp các công cụ không liên quan (như vừa con dấu vừa thước kẹp cùng xuất hiện vô lý). Mỗi phân cảnh chỉ kích hoạt đúng 1 cặp tương tác cơ học chính từ bảng Semantic Archetypes.
3. **Bứt tốc va chạm $\le 0.4\text{s}$ & Khóa cứng điểm đỗ**: Hành động cơ học (dập dấu, siết kẹp, cắt giấy) diễn ra dứt khoát trong 0.2s - 0.4s và dừng bất động, chỉ duy trì vi rung thớ giấy 12fps (on twos) đến hết cảnh.
4. **Một cú máy duy nhất kết thúc bằng `Settle on...`**: Mỗi clip video chỉ có 1 chuyển động máy quay duy nhất và BẮT BUỘC kết thúc bằng chỉ thị điểm đỗ (`Settle on [target]`).
5. **Bảo tồn vùng an toàn phụ đề 20%**: Toàn bộ chủ thể quan trọng và số liệu khổng lồ phải nằm ở 80% phần trên của khung hình, dành riêng 20% đáy màn hình cho phụ đề karaoke Remotion 0ms drift.
