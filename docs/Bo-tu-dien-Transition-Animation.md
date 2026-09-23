# Bộ từ điển Transition & Animation cho Motion Graphic / Vox-style / Stop Motion

> **Single Source of Truth (SoT) - Thư viện chuẩn hóa thuật ngữ chuyển cảnh & chuyển động nội cảnh cho AI Video Factory.**
> Áp dụng trực tiếp cho:
> - **Giám đốc hình ảnh / Đạo diễn phân cảnh (B3 Director Plan)**
> - **Người quay phim / Tạo hình mỹ thuật (B3.5 Lead Cinematographer & Prompt Forge)**
> - **Dựng hậu kỳ & Kỹ xảo chuyển động (B6 Remotion Motion Graphics Engine)**

---

## I. TRANSITION — Chuyển cảnh

### 1. Nhóm Mask / Wipe (dùng shape che phủ)
- **Wipe transition** (`/wipe_transition`) — quét theo hướng (trái/phải/trên/dưới)
- **Iris wipe / Circle wipe** (`/circle_wipe`) — mở/đóng theo vòng tròn từ tâm
- **Radial wipe** (`/radial_wipe`) — quét theo hình quạt (kiểu kim đồng hồ)
- **Blind wipe** (`/blind_wipe`) — kiểu rèm cửa, các dải song song
- **Checkerboard wipe** (`/checkerboard_wipe`) — dạng ô bàn cờ hiện dần
- **Shape mask reveal** (`/shape_mask_reveal`) — dùng logo/icon làm mask lộ cảnh sau

### 2. Nhóm Zoom / Scale
- **Zoom blur transition** (`/zoom_blur`) — zoom nhanh kèm motion blur
- **Zoom through transition** (`/zoom_through`) — zoom xuyên vào 1 điểm/lỗ khóa rồi cảnh mới bừng hiện
- **Whip zoom** (`/whip_zoom`) — zoom siêu nhanh tạo cảm giác giật và áp lực tâm lý
- **Peephole transition** (`/peephole_transition`) — zoom through qua 1 vòng tròn nhỏ (như nhìn qua lỗ khóa / ống kính gián điệp)

### 3. Nhóm Motion Blur / Speed
- **Whip pan (Swish pan)** (`/whip_pan`) — máy quay "quẹt" ngang cực nhanh nối liền hai không gian hoặc tài liệu
- **Speed ramp transition** (`/speed_ramp`) — tăng tốc độ đột ngột giữa 2 cảnh rồi chậm dần khóa nét
- **Smash cut** (`/smash_cut`) — cắt đột ngột, tương phản cực mạnh (hình ảnh đanh thép, ngắt âm thanh bất ngờ)

### 4. Nhóm Morph / Transform
- **Shape morph transition** (`/shape_morph`) — 1 hình khối/icon biến đổi hình dạng sang hình khối khác
- **Match cut / Match action transition** (`/match_cut`) — 2 cảnh có hình dạng, vị trí hoặc hành động tương đồng nối tiếp nhau
- **Liquid morph / Metaball transition** (`/liquid_morph`) — các khối chất lỏng hòa tan và kết tụ thành cảnh mới
- **Object transform transition** (`/object_transform`) — vật thể chứng cứ A biến hình dần thành vật thể kết luận B

### 5. Nhóm Glitch / Digital
- **Glitch transition** (`/digital_glitch`) — nhiễu số, gián đoạn tín hiệu camera điều tra
- **RGB split (Chromatic aberration) transition** (`/rgb_split`) — tách quang sai 3 kênh màu đỏ/xanh lá/xanh dương
- **Datamosh transition** (`/datamosh_cut`) — hiệu ứng nén vỡ điểm ảnh pixel, kéo lê mảng màu
- **VHS / scanline transition** (`/vhs_scanline`) — nhiễu từ tính băng analog, đường quét sọc ngang CRT

### 6. Nhóm Light / Texture
- **Light leak transition** (`/light_leak`) — ánh sáng quang học tràn viền qua khung hình
- **Lens flare transition** (`/lens_flare`) — vệt sáng lóe quét qua thấu kính anamorphic
- **Film burn transition** (`/film_burn`) — hiệu ứng cháy phim nhựa cổ điển
- **Bokeh transition** (`/bokeh_blur`) — các đốm sáng mờ nhòe quang học che phủ chuyển cảnh
- **Smoke / fog transition** (`/smoke_dissolve`) — khói hoặc sương mù dày đặc lan tỏa che giấu vết cắt
- **Ink bleed transition** (`/ink_bleed`) — vệt mực loang hữu cơ chuyển từ bản đồ tổng quan sang chi tiết hồ sơ
- **Particle burst / dissolve transition** (`/particle_burst`) — bụi giấy/hạt phân rã nổ tung hoặc tụ hội

### 7. Nhóm Stop Motion / Physical (Đặc trưng VOX & Xúc giác)
- **Paper crumple / tear / fold / unfold transition** (`/paper_tear`) — giấy bị xé rách, vò nát hoặc mở nếp gấp lộ chứng cứ
- **Unboxing transition** (`/unboxing_reveal`) — mở nắp hộp niêm phong vật chứng lộ tài liệu bên trong
- **Stop-motion object move transition** (`/stopmotion_move`) — vật thể "tự" trượt giật cục rời khỏi khung hình theo từng nấc
- **Flipbook transition** (`/flipbook_cut`) — lật nhanh như tập ảnh tài liệu lưu trữ

### 8. Nhóm Split / Grid
- **Split screen transition** (`/split_screen`) — chia đôi khung hình so sánh 2 dữ liệu rồi trượt
- **Grid reveal transition** (`/grid_reveal`) — chia lưới ma trận rồi từng ô lộ diện tuần tự
- **Page / panel slide** (`/panel_slide`) — kiểu khung truyện tranh graphic novel, các ô trượt ăn khớp vào nhau

---

## II. ANIMATION — Chuyển động nội cảnh

### 1. Kinetic Typography (chữ động) — đặc trưng Vox-style
- **Text pop-up / bounce** (`/text_bounce`) — chữ nảy lên với gia tốc đàn hồi
- **Typewriter effect** (`/typewriter_text`) — chữ gõ từng ký tự theo nhịp máy chữ cơ học
- **Word-by-word reveal** (`/word_karaoke`) — hiện từng từ chính xác theo nhịp micro-second giọng đọc Whisper
- **Text mask reveal** (`/text_mask_reveal`) — dòng chữ nhô lên từ phía sau vạch kẻ hoặc đường biên
- **3D text rotation** (`/text_3d_rotate`) — khối chữ xoay lập thể theo phối cảnh 3 chiều
- **Elastic / spring text** (`/elastic_spring_text`) — chữ co giãn kiểu lò xo nén bung

### 2. Character / Object Animation
- **Squash & stretch** (`/squash_stretch`) — ép bẹp khi va chạm và dãn dài khi bay, tạo độ sống động
- **Rubber hose animation** (`/rubber_hose`) — tay chân uốn dẻo kiểu hoạt hình cổ điển
- **Walk cycle** (`/walk_cycle`) — chu kỳ bước đi của nhân vật 2D
- **Idle animation** (`/idle_breathe`) — nhịp thở và nhấp nhô nhẹ khi nhân vật đứng yên quan sát
- **Puppet rig animation** (`/puppet_rig`) — khớp chuyển động của nhân vật giấy cắt lớp

### 3. Camera Movement (Giả lập trong không gian 2.5D & 3D)
- **Parallax scrolling** (`/parallax_depth`) — các lớp giấy, bản đồ và nhân vật trôi lệch tốc độ tạo chiều sâu thị sai
- **Pan / Tilt** (`/cinematic_pan`, `/macro_tilt`) — máy quay lia ngang điều tra hoặc ngửa/cúi quét hợp đồng
- **Dolly zoom (Vertigo effect)** (`/dolly_zoom`) — máy tiến tới trong khi góc nhìn mở rộng, tạo ảo giác choáng váng
- **Orbit / 3D camera rotation** (`/macro_orbit`, `/orbit_3d`) — quỹ đạo lượn quanh vật thể 3D / con dấu lập thể
- **Focus breathing** (`/focus_breathe`) — độ sâu trường ảnh nhấp nhô tìm nét mô phỏng ống kính quang học

### 4. Reveal Animation
- **Draw-on animation** (`/draw_on_line`) — nét cọ/vạch bút dạ/đường chỉ tự vẽ dần theo thời gian
- **Grow / Scale in** (`/scale_in_pop`) — vật chứng nở lớn từ tâm với độ nảy
- **Fade + slide in** (`/fade_slide_in`) — trượt vào kết hợp làm mờ êm ái
- **Staggered reveal** (`/staggered_reveal`) — nhiều hồ sơ tài liệu rơi xuống so le cách nhau vài frame
- **Path animation** (`/path_motion`) — luồng tiền/chứng cứ bay uốn lượn theo quỹ đạo định sẵn

### 5. Data / Chart Animation — đặc trưng Vox Data-Driven
- **Bar chart grow** (`/barchart_grow`) — cột biểu đồ kinh tế vươn cao
- **Line chart draw** (`/linechart_draw`) — đường biểu đồ xu hướng tự vạch nối các điểm mốc
- **Counter / Number count-up** (`/counter_countup`) — con số định lượng nhảy tăng tốc đến giá trị thực
- **Map pin drop / zoom** (`/map_pin_drop`) — ghim đồng rơi cắm xuống bản đồ, camera rướn tới
- **Callout circle radar** (`/callout_circle`) — vòng tròn radar nhắm trúng vị trí tọa độ trên bản đồ

---

## III. Bảng Tổng Hợp Theo Mục Đích Sử Dụng (Purpose Matrix)

| Cảm giác muốn tạo | Nhóm kỹ thuật tương ứng | Nhịp điệu và phối hợp điện ảnh |
|---|---|---|
| **Chuyên nghiệp, tin tức, dữ liệu** | Kinetic typography, data animation, whip pan, match cut, counter count-up | Nhịp dứt khoát, âm thanh click chuột/máy chữ, camera lia dứt điểm, số nhảy tăng tốc. |
| **Ấm áp, thủ công, gần gũi (Tactile Vox)** | Paper stop-motion, hand-drawn draw-on, texture grain, 12fps posterize, brass pin, scotch tape | Nhịp 12fps ngắt nhịp (on twos), sột soạt giấy báo, bóng đổ vật lý, đường chỉ đỏ điều tra. |
| **Hiện đại, công nghệ, bảo mật** | Glitch, RGB split, liquid morph, 3D transition, surveillance CRT | Tia quét scanline, camera an ninh, nhấp nháy tín hiệu, gián đoạn đường truyền dữ liệu. |
| **Xung đột, kịch tính, chấn động (High Stakes)** | Smash cut, whip zoom, dolly zoom, focus breathing, snap zoom | Đột ngột ngắt nhịp, ống kính thở quang học, giật hình cận cảnh, chấn động âm thanh đanh thép. |
| **Cinematic, suy ngẫm, kể chuyện sâu lắng** | Light leak, film burn, parallax scrolling, continuous drift, slow pull out | Ánh sáng vàng/xanh chạng vạng, chuyển động máy êm ái, kéo lùi vô tận lộ quy mô thể chế. |
