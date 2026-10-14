# 🎨 DESIGN & INTERFACE SPECIFICATION TEMPLATE (STEP 2: DESIGN)

> **Mục đích**: Bản vẽ thiết kế kiến trúc và giao diện chi tiết trước khi code.  
> *Áp dụng theo Bước 2 của quy chuẩn Vibe Coding chuẩn (chống AI tự bịa giao diện xấu/lộn xộn).*

---

## 1. NGUYÊN TẮC THỊ GIÁC / GIAO DIỆN (DESIGN TOKENS)
- **Hệ màu chủ đạo**:
  - Primary / Brand: `#1F4E78` (Navy), `#0866FF` (Blue)
  - Success / Pass: `#31A24C` (Green)
  - Warning / Attention: `#F7B928` (Lemon/Amber)
  - Critical / Error: `#FA383E` (Red)
  - Dark Mode Surfaces: `#18191A`, `#242526`, `#3A3B3C`
- **Typography & Font**: `Inter`, `SF Pro`, `Segoe UI`, `monospace` cho code/metrics.
- **Tỉ lệ khung hình (Video/Canvas)**:
  - Long-form YouTube: `16:9` (`1920x1080` @ 30 FPS).
  - Shorts / Reels: `9:16` (`1080x1920` @ 30 FPS).
  - Nhân vật Foreground: `1:1` (`1024x1024` PNG trong suốt).

---

## 2. BỐ CỤC GIAO DIỆN / THÀNH PHẦN (COMPONENT HIERARCHY)
- **Header / Meta**: Tiêu đề phân cảnh, nhãn Beat (`BEAT X // TITLE`), speaker tag (`TÊN // VAI TRÒ`).
- **Khung chính (Body)**:
  - Layer 1 (Background): Parallax panning 1.05x -> 1.0x, cel-shaded illustration.
  - Layer 2 (Foreground): Kinetic character entry, dynamic drop shadow, zero edge spill.
  - Typographic Callouts: Ticker counter, fact cards, document stamp highlight.
- **Lower-third / Subtitles**: Karaoke word-level highlight, font size cân đối, an toàn mép màn hình (Safe Margin 10%).

---

## 3. KHẾ ƯỚC PROPS & COMPONENT SCHEMA (REMOTION / UI PROPS)
```typescript
interface ComponentProps {
  sceneId: string;
  durationInFrames: number;
  fps: number;
  market: 'EN' | 'JP' | 'KR' | 'VN';
  theme: {
    primaryColor: string;
    accentColor: string;
  };
  audioPath: string;
  subtitles: Array<{
    word: string;
    start: number;
    end: number;
  }>;
}
```
