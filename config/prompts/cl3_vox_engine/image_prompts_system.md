# 🏛️ CL3 CANONICAL PROMPT ENGINE: PAPER DIORAMA T2I PROMPT SYSTEM (KIM CHỈ NAM)

> **BẢN QUY CHUẨN MỸ THUẬT VÀ SINH ẢNH VOX TACTILE COLLAGE (T2I MASTER ARCHITECTURE).**  
> Hợp nhất tinh hoa của **CL3 Vox Video System** và **Vox Engine v3 (Rule 120, 122, 140, 141)**.  
> Mọi prompt sinh ảnh (Image Generation / Cutouts / Canvas) trong hệ thống AI Video Factory BẮT BUỘC tuân thủ cấu trúc này.

---

## 1. Cấu Trúc Bất Biến (Canonical 2-Block Structure)

Mọi prompt sinh ảnh đều được cấu thành từ 2 khối phân định rõ ràng:

```
[STYLE BLOCK]  — Khối phong cách cố định, dán nguyên văn (verbatim) không thay đổi
SHOT:          — Khối biến đổi theo từng phân cảnh, mô tả lớp lang vật lý theo công thức
```

- **Khối Style Block**: Giữ vững ngôn ngữ thị giác, chất liệu thớ giấy, kỹ thuật in ấn bán sắc (halftone) và độ sâu quang học. Không bao giờ thay đổi giữa các cảnh.
- **Khối SHOT**: Chứa toàn bộ sự biến đổi sáng tạo, chủ thể nhân vật, tài liệu điều tra, đạo cụ cơ học và số liệu lượng hóa.

---

## 2. Khối Style Block Chuẩn Mực (The Canonical Style Block - Copy Verbatim)

> Use the attached style sheet for materials only – aged-print collage textures on aged archival cream newsprint and tan kraft cardstock, halftone black-and-white cutout people with rough white keylines and offset ink accent strokes (crimson red, mustard gold), giant stat numbers rendered as physical hero characters, and authentic print grain. Do NOT copy the sheet's layout or its flatness: every scene is a deep 3D paper diorama – cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, dives, whips, racks focus – one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's muted archival palette (cream newsprint, tan kraft, ink black, halftone gray). Multi-plane stereoscopic depth: 1.4x fast foreground tool travel, 1.0x tack-sharp focal plane, 0.3x slow background drift in shallow depth of field. Motion: mechanical spring pop-ups with slight overshoot, staggered entrances, ticking counters, tactile paper contact residue. Audio: sound design only – paper pops, whooshes, stamps, ticks, newsroom hum. No music. No voice-over. Keep bottom 20% of the surface completely empty, plain bare cream paper only. No text, no objects, no cards in the bottom fifth.

### Giải mã chức năng từng mệnh đề (Tại sao không được xóa):

| Mệnh đề (Clause) | Chức năng kỹ thuật (Technical Job) |
| :--- | :--- |
| `"style sheet for materials only"` | Vay mượn chất liệu xúc giác (texture), không sao chép bố cục (layout). |
| `"Do NOT copy the sheet's layout or its flatness"` | Diệt trừ tử huyệt số 1: Tránh tạo ra ảnh phẳng 2D nhàm chán. |
| `"deep 3D paper diorama / physical layers in real space"` | Ép mô hình AI tạo ra hiệu ứng thị sai (parallax) và phân tách tầng lớp rõ rệt. |
| `"shallow depth of field / foreground crossing the lens"` | Bán độ chân thực 3D qua quang học ống kính máy quay macro. |
| `"camera is an actor / one committed move"` | Ngăn chặn hiện tượng lia camera lộn xộn hoặc trôi dạt mất phương hướng. |
| `"Backgrounds change per clip"` | Đảm bảo mỗi phân cảnh mang một bề mặt hồ sơ mới (bản đồ, sổ cái, báo chí, bản vẽ). |
| `"Multi-plane stereoscopic depth"` | Định danh phân lớp thị sai 3 tầng tốc độ (FG 1.4x, MG 1.0x, BG 0.3x). |
| `"springs with overshoot, staggered, ticking"` | Nhịp cử động stop-motion đặc trưng bứt tốc $\le 0.4\text{s}$, không trôi dạt. |
| `"sound design only, no music, no VO"` | Khóa âm thanh sạch cho Remotion ráp SFX/TTS ở hậu kỳ. |
| `"Keep bottom 20% empty, plain cream paper only"` | Bảo toàn khoảng trống hiển thị phụ đề karaoke 0ms drift mà không làm AI vẽ chữ phụ đề giả. |

---

## 3. Công Thức Viết Khối SHOT (The SHOT Formula)

Viết thành một đoạn văn xuôi 2–5 câu theo đúng thứ tự sau. Không dùng gạch đầu dòng, không ghi số thứ tự:

```
Background: [Bề mặt tài liệu nền + cự ly + trạng thái mờ nét (depth of field)].
MG: [Chủ thể nhân vật cắt dán halftone đen trắng + viền rách trắng + nét mực viền lệch].
FG: [Đạo cụ cơ học tương tác H1->H7 / Thẻ số liệu khổng lồ / Thước cặp / Con dấu / Kẹp sắt] đặt ở các cự ly sâu khác nhau.
[Hành động kết nối: Mũi tên đỏ vẽ vòng lặp, thước kẹp siết số liệu, dấu mộc dập lún giấy, dao trổ rạch lớp báo].
Camera [MỘT chuyển động duy nhất], focus [Hành vi chuyển nét / rack focus].
Settle [Điểm dừng khung hình cuối cùng].
```

---

## 4. Tủ Menu Thành Phần (Component Slot Menus)

### A. Background (Chọn 1, đặt nghiêng góc phối cảnh, mờ nét ở hậu cảnh):
- `faded world map tilted in deep perspective, far out of focus`
- `torn financial ledger page with verified quantitative metric columns`
- `newspaper column wall with aged deckle borders receding into soft blur`
- `architectural blueprint grid under warm 3200K tungsten wash`
- `engraved stock chart with faded metric coordinate lines`
- `passport stamp field with authentic regional ink cancellations`
- `circuit trace print on fibrous cream parchment`
- `topographic elevation survey map on aged cream cardstock`
- `shipping manifest table with hand-annotated clearance marks`

### B. Foreground & Midground Elements (Lớp lang đối kháng):
- **Midground (MG)**: Nhân vật cắt dán bán sắc đen trắng (Halftone B&W Cutout Figures) với đường viền cắt thô (rough white deckle keyline) và nét bóng mực đỏ/vàng lệch sau lưng (`offset stroke pop`).
- **Foreground (FG)**: 
  - Thẻ số liệu khổng lồ: `giant stat number [TEXT] (giant number)`
  - Kẹp tài liệu bằng đồng: `precision archival brass document clamp (interacting tool)`
  - Dấu mộc điều tra đỏ thắm: `turned-wood vermilion docket seal stamp (interacting tool)`
  - Kẹp lò xo thép công nghiệp: `blackened steel spring clamp (interacting tool)`
  - Dao trổ / Kéo biên tập: `machined steel editorial shears (interacting tool)`
  - Sợi chỉ đỏ điều tra: `red evidence yarn pinned taut between brass pushpins (tether)`
  - Kính lúp quang học: `brass magnifying loupe revealing micro-print text (optical)`
  - Bút chì sáp đỏ / Dấu kiểm chứng: `archival crimson graphite pencil / official registry seal (mark)`

### C. 7 Họ Tương Tác Cơ Học ($H_1 \to H_7$ Kinetic Couplings):
1. **$H_1$ (Impact / Percussion)**: Con dấu dập mạnh $\to$ Giấy lún, mực loang nhẹ, camera giật 1 frame.
2. **$H_2$ (Constraint / Clamp)**: Kẹp tài liệu hoặc chốt giữ siết mép giấy $\to$ Mép cardstock nhăn, chốt khóa cứng.
3. **$H_3$ (Sever / Cut / Tear)**: Kéo kim loại cắt xé $\to$ Mảnh giấy tách rời làm lộ chứng cứ tầng bên dưới.
4. **$H_4$ (Tether / Tension)**: Sợi chỉ đỏ kéo căng giữa 2 ghim đồng $\to$ Hai đối tượng bị kéo nghiêng về nhau.
5. **$H_5$ (Optical / Refraction)**: Kính lúp trượt qua $\to$ Phóng đại $1.4\times$, méo cong rìa barrel distortion.
6. **$H_6$ (Mark / Ink Transfer)**: Bút chì sáp đỏ kẻ đậm / Dấu kiểm chứng $\to$ Thớ giấy lún nhẹ, vệt sáp đỏ mờ lì ăn vào thớ báo cũ không phát quang giả tạo.
7. **$H_7$ (Displace / Unfold)**: Lực đẩy ma sát $\to$ Chồng ảnh xòe quạt, tài liệu bung nếp gấp accordion.

### D. Camera Move (BẮT BUỘC chọn đúng MỘT chuyển động):
- `orbits a quarter turn`
- `flies between physical paper layers`
- `dives from high angle above`
- `whips decisively from left to right`
- `pushes in smoothly through a torn aperture`
- `pulls back to reveal the expanding diorama`
- `cranes upward over the stacked dossier`
- `racks focus sharply from foreground clamp to background figure`

### E. Settle (Điểm kết thúc bắt buộc):
- `Settle on the giant stat number.`
- `Settle mid-orbit facing the verified document.`
- `Settle on the cutout's eyes in sharp focus.`
- `Settle wide on the fully assembled forensic desk.`

---

## 5. Các Bất Biến & Kỷ Luật Thép (Iron Rules)

1. **Một chuyển động camera duy nhất**: CẤM 2 chuyển động trong 1 cảnh. Không lia lung tung.
2. **Luôn chỉ định tối thiểu 2 tầng sâu**: Nếu không mô tả "at different depths" hoặc "foreground crossing the lens", AI sẽ ép dẹp thành tranh phẳng 2D.
3. **Logo giữ nguyên dạng phẳng, không biến tính**: "attached... flat, unmodified".
4. **Số liệu là nhân vật chính (Hero Character)**: Số liệu thống kê được tạo hình khổng lồ, nổi bật, có bóng đổ vật lý.
5. **Luôn kết thúc bằng "Settle on..."**: Đây là điểm neo bắt buộc giúp AI biết dừng lại ở đâu.
6. **Đổi bề mặt nền (Background) mỗi cảnh**: Cùng hệ màu tin tức, nhưng đổi giữa bản đồ, sổ cái, trang báo, hợp đồng.
7. **Động từ chủ động ở thì hiện tại**: "snaps in", "slices", "clamps", "stamps", "races".
8. **Cấm tuyệt đối thẻ đạo diễn rác**: Không ghi `[Shot 1]`, `(5 seconds)`, `Camera angle: 45 deg`.
