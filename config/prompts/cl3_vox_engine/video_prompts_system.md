# 🏛️ CL3 CANONICAL PROMPT ENGINE: PAPER DIORAMA I2V VIDEO PROMPT SYSTEM (KIM CHỈ NAM)

> **BẢN QUY CHUẨN ĐẠO DIỄN VÀ SINH VIDEO CHUYỂN ĐỘNG VOX COLLAGE (I2V MASTER ARCHITECTURE).**  
> Hợp nhất tinh hoa của **CL3 Vox Video System** và **Vox Engine v3 (Rule 120, 122, 135, 140, 141)**.  
> Áp dụng trực tiếp cho Google Flow (Veo 3.1 - Fast / Omni 1.1 Flash) và Remotion Engine trong toàn bộ hệ thống.

---

## 1. Cấu Trúc Bất Biến 4 Khối (Canonical 4-Block Architecture)

Mọi prompt sinh video I2V đều được xây dựng theo đúng thứ tự 4 khối sau:

```
[STYLE BLOCK]  ──► Lựa chọn 1 trong 3 phong cách (Flat Parallax / Deep Diorama / Locked Stage)
SHOT:          ──► Mô tả 5 thành phần động học: Background -> MG -> FG -> Camera -> Settle
AUDIO:         ──► Thiết kế âm thanh xúc giác (Sound Design only, no music, no VO)
AVOID:         ──► Bộ lọc triệt tiêu rủi ro tiêu cực (Negative Constraints khớp với Style)
```

---

## 2. Bước 1: Chọn 1 Khối Style Block Phù Hợp Cho Phân Cảnh

Tùy theo tính chất nhịp điệu của cảnh trong cấu trúc 5 Beat Docudrama, đạo diễn chọn 1 trong 3 Style Block sau (dán nguyên văn - verbatim):

### Khối A: Flat Parallax (Tài liệu điều tra, Bảng số liệu, Nhịp tĩnh kiểm toán)
> Use the attached style sheet as the strict visual system — match its aged-newsprint collage surface (#F4F1EA), desaturated archival palette with one hot accent (#D62E1F), condensed headline caps with giant stat numbers, halftone black-and-white cutout people with rough white keylines and offset accent strokes, and its print-grain finish. Do NOT copy the sheet's layout; it defines the language, not the composition. Layers sit at distinct depths like a paper diorama — true parallax, never glossy 3D. Backgrounds are muted archival fields, varying per clip within this palette. ALERT WASH means the whole frame floods toward the hot accent tone. Motion: snappy spring pop-ups with overshoot within 0.2s - 0.4s, staggered entrances, ticking counters, underline swipes; one slow camera move per clip. Objects lock into a dead-stop hold with subtle 12fps paper grain flutter and micro shadow breathing <= 2px. Audio: sound design only — paper pops, thwips, stamps, ticks, low newsroom hum. No music. No voice-over. Preserves bottom 20% vertical safe zone.

### Khối B: Deep Diorama (Điểm bùng nổ, Bước ngoặt, Khủng hoảng, Góc quay điện ảnh)
> Use the attached style sheet for materials only — aged-print collage textures (#F4F1EA / #C9BB9C), halftone black-and-white cutout people with rough keylines and offset accent strokes, giant stat numbers, authentic print grain. Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama — cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, dives, whips, racks focus — one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's palette. ALERT WASH means the entire frame floods to the hot accent tone (#D62E1F) in one beat. Motion: snappy stop-motion strikes <= 0.4s with overshoot, staggered entrances, mechanical contact dynamics leaving physical residue, locking into 12fps living texture hold on twos. Audio: sound design only — paper pops, whooshes, stamps, ticks. No music. No voice-over. Preserves bottom 20% vertical safe zone.

### Khối C: Locked Stage (Sân khấu phẳng tự định nghĩa — Dùng khi không đính kèm file ảnh mẫu)
> Documentary cutout-collage stage: a locked, muted archival map/texture background that never changes (#F4F1EA). Midground: black-and-white halftone cutouts with a rough white keyline and an offset red marker stroke behind each. Foreground: structures, props, and big stat numbers in full color. Condensed bold headline caps; numbers rendered huge, as physical hero characters. Desaturated palette plus one hot red accent (#D62E1F), secondary mustard (#D9A441). Spring pop-ups with slight overshoot <= 0.4s, staggered entrances, counters ticking up, red underline swipes. Locked into 12fps living hold on twos with paper grain vibration <= 2px. Camera: subtle slow drift only, never cuts, ending with a precise settle. Audio: sound design only. No music, no narration.

---

## 3. Bước 2: Viết Khối SHOT (5 Thành Phần Động Học)

Một đoạn văn liền mạch 2–5 câu, bắt buộc chứa đủ 5 thành phần theo đúng thứ tự:

| Thành phần | Chức năng đạo diễn | Cú pháp mẫu chuẩn mực |
| :--- | :--- | :--- |
| **1. Background** | Thiết lập trường sâu hậu cảnh | `Background: a faded world map tilted in perspective, far out of focus.` |
| **2. MG (Midground)** | Chủ thể cắt dán nhân vật/hồ sơ | `MG: halftone cutout of [CHARACTER] and unpermitted lease dossier enter at staggered depths.` |
| **3. FG (Foreground)** | Đạo cụ cơ học $H_1 \to H_7$ / Số liệu | `FG: giant stat number "$42.8M" (giant number) and archival brass document clamp (interacting tool).` |
| **4. Kinetic Action** | Va chạm cơ học bứt tốc $\le 0.4\text{s}$ | `The brass binder clamp slides briskly and snaps tightly over the metric margin, crimping cardstock edges, leaving a sharp crimp indentation.` |
| **5. Camera & Settle** | Một cú máy duy nhất + Điểm đỗ | `Camera pushes in through the paper gap, focus racking front to back. Settle on the verified metric figure in sharp focus.` |

### Thư Viện Cú Máy Chuẩn (Chỉ chọn ĐÚNG 1 cú máy):
- `push-in`: Tiến máy chậm rãi xuyên qua khe giấy tầng trước.
- `slow drift lateral`: Trôi ngang chậm rãi $\le 2\%$, giữ trường nét ổn định.
- `dive through a layer`: Bổ nhào từ trên cao xuyên qua lỗ rách tài liệu.
- `orbit quarter turn`: Xoay máy một phần tư cung quanh trục diorama.
- `whip x2-3`: Lia máy tốc độ cao bứt tốc, hạ cánh dứt khoát tại điểm chạm.
- `fast lateral track then hard stop with overshoot`: Trượt ngang nhanh rồi khựng lại có độ nảy cơ học.
- `macro slide along an object, rack focus tip -> subject`: Trượt cận cảnh dọc theo thân thước/bút, chuyển nét từ đầu ngòi sang khuôn mặt nhân vật.

---

## 4. Bước 3: Viết Khối AUDIO (Thiết Kế Âm Thanh Xúc Giác)

**Cú pháp bắt buộc**:
`AUDIO: [sound 1], [sound 2], [sound 3] — sound design only, no music, no narration.`

Âm thanh BẮT BUỘC phản chiếu đúng hành động cơ học:
- **Cú máy Dive / Bổ nhào**: `submerge whoosh, deep pressure hum, paper flutter`
- **Cú máy Whip / Lia nhanh**: `whip whoosh, crisp paper snap, mechanical click`
- **Va chạm Stamp / Dập dấu ($H_1$)**: `heavy wooden thud, paper compression crack, oily ink squelch`
- **Kẹp tài liệu / Siết kẹp ($H_2$)**: `steel spring snap, metallic clamp click, cardstock crimp crunch`
- **Cắt xé Dao / Kéo ($H_3$)**: `clean shear slice, fiber tearing rip, falling paper flutter`
- **Sợi chỉ đỏ căng ($H_4$)**: `pushpin wooden tap, string tension twang, taut hum`
- **Kính lúp lướt ($H_5$)**: `smooth glass glide, brass friction rub, optical focus chime`
- **Bút dạ quang ($H_6$)**: `felt nib squeak, ink saturation hiss, neon pulse whoosh`
- **Số đếm tăng tốc (Counter)**: `rapid mechanical ticker clicks, bell ring at peak, air release`
- **Nền không gian**: `low newsroom hum` hoặc `quiet archival room tone`.

---

## 5. Bước 4: Viết Khối AVOID (Bộ Lọc Triệt Tiêu Tiêu Cực)

### Dành cho Khối A (Flat Parallax) và Khối C (Locked Stage):
> AVOID: no glossy CG 3D, no plastic specular shine, no lens flares, no camera cuts within the clip, no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, no invented logos, no watermarks, no simultaneous entrances, no music, no soundtrack, no voice-over, no narration, no lyrics, no UI or glass dashboard widgets.

### Dành cho Khối B (Deep Diorama):
> AVOID: no flat single-plane composition, no static locked-off camera, no glossy plastic CG (depth stays pure papercraft), no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, no invented logos, no watermarks, no music, no soundtrack, no voice-over, no narration, no lyrics, no futuristic holograms, no digital screen glows.

---

## 6. Mẫu Điền Khuyết Hoàn Chỉnh (Complete Fill-In Template)

```markdown
[STYLE BLOCK B — Deep Diorama]
Use the attached style sheet for materials only — aged-print collage textures (#F4F1EA / #C9BB9C), halftone black-and-white cutout people with rough keylines and offset accent strokes, giant stat numbers, authentic print grain. Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama — cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, dives, whips, racks focus — one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's palette. ALERT WASH means the entire frame floods to the hot accent tone (#D62E1F) in one beat. Motion: snappy stop-motion strikes <= 0.4s with overshoot, staggered entrances, mechanical contact dynamics leaving physical residue, locking into 12fps living texture hold on twos. Audio: sound design only — paper pops, whooshes, stamps, ticks. No music. No voice-over. Preserves bottom 20% vertical safe zone.

SHOT:
Background: a torn financial ledger page with verified quantitative metric columns tilted away in soft focus.
MG: halftone cutout of the regulatory investigator entering from left, white deckle border with offset red ink stroke.
FG: giant stat number "$42.8M" (giant number) and archival brass document clamp (interacting tool) stacked at distinct depths.
Action: The brass binder clamp slides briskly in 0.3s and snaps tightly over the flagged figure, crimping cardstock edges, leaving a sharp crimp indentation. All elements lock into dead-stop hold with 12fps living paper grain vibration.
Camera: pushes in through the paper gap beside the number, focus racking from brass clamp to the investigator's eyes. Settle on the verified metric figure in sharp focus.

AUDIO: steel spring snap, crisp cardstock crimp, placement click, low archival room tone — sound design only, no music, no narration.

AVOID: no flat single-plane composition, no static locked-off camera, no glossy plastic CG, no full-color portraits, no warped gibberish text, no invented logos, no watermarks, no music, no voice-over.
```

---

## 7. Quy Tắc Chuỗi Phân Cảnh (Video Sequencing & Continuity)

1. **Luân chuyển Phong cách theo Nhịp**: Dùng `Deep Diorama` cho các cảnh mở màn (Hook), bước ngoặt và đỉnh điểm (Climax); dùng `Flat Parallax` cho các phân đoạn phân tích số liệu tài chính hoặc bóc tách hồ sơ chứng cứ.
2. **Đổi Bề mặt Nền mỗi Cảnh**: Tuyệt đối không để 2 cảnh liên tiếp dùng chung 1 mặt bàn bản đồ. Luân chuyển giữa bản đồ, trang báo, sổ cái, giấy nháp điều tra.
3. **Luân chuyển Cú máy**: Không bao giờ dùng 2 cú `dive` hoặc 2 cú `whip` liên tiếp.
4. **Kế thừa Động học (Causal Handoff Law)**: Vật thể hoặc tồn dư (residue) của Scene $N$ phải là điểm tựa hoặc nguồn tương tác cho Scene $N+1$.
5. **Tiết kiệm ALERT WASH**: Chỉ dùng `ALERT WASH` cho đúng 1–2 khoảnh khắc chấn động nhất của toàn bộ tập phim (Act I ngòi nổ hoặc Act IV vạch trần).
6. **Kết thúc bằng Khung Căng thẳng (Tension Hold)**: Cảnh cuối mỗi Block luôn dừng lại ở trạng thái giữ lực (thước kẹp siết chặt, dấu vừa chạm giấy, sợi chỉ vừa kéo căng) thay vì trạng thái thả lỏng.
