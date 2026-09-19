# 🧪 [TEST_HARNESS_PLAN] INFRA_3D_PROCEDURAL_VOX_INTEGRATION_AND_COT_HARNESS

## 📌 1. Chiến Lược Kiểm Thử (Testing Strategy)
- **Author Role**: QA & Test Harness
- **Tiêu Chí Nghiệm Thu**:
  - Không dựa vào giả định, bắt buộc kiểm thử runtime bằng code sống (Rule 127).
  - Kiểm tra tính tương thích ngược tuyệt đối (Zero-Regression): Các scene 2D truyền thống không bị ảnh hưởng.
  - Đo đạc hiệu năng vật lý trên VPS Hetzner CPU-only: Tốc độ FPS, RAM buffer, tính ổn định không sập OOM.

---

## 📋 2. Ma Trận Kiểm Thử (Test Matrix)

| Test ID | Hạng Mục Kiểm Thử | Dữ Liệu Đầu Vào | Kết Quả Kỳ Vọng | Môi Trường |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | B3 Keyword Detection (EN) | Narration chứa `"hanko seal"` | `ov["type"] == "evidence_3d_prop"` | Local & VPS Python |
| **TC-02** | B3 Keyword Detection (VN) | Narration chứa `"con dấu mộc đỏ"` | `ov["type"] == "evidence_3d_prop"` | Local & VPS Python |
| **TC-03** | B3 Keyword Detection (KR) | Narration chứa `"인감 도장"` | `ov["type"] == "evidence_3d_prop"` | Local & VPS Python |
| **TC-04** | B3 Zero-Regression (Bank Check) | Narration chứa `"$12,500,000"` | `ov["type"] == "bank_check"` | Local & VPS Python |
| **TC-05** | B3 Zero-Regression (Dossier) | Narration chứa `"classified report"` | `ov["type"] == "paper_dossier"` | Local & VPS Python |
| **TC-06** | Remotion Bundle Compilation | `remotion/src/index.tsx` | Exit Code 0, Webpack bundle clean | VPS Headless Shell |
| **TC-07** | Remotion Still Frame QA | `EvidenceProp3DTest` @ frame 45 | JPEG 1080p sinh ra trong < 3s, Exit Code 0 | VPS SWangle OpenGL |
| **TC-08** | Remotion Video Render | 90 frames (3s @ 30fps) | MP4 1080p rendered, >= 4.0 FPS, 0 VRAM | VPS Hetzner CPU |
| **TC-09** | DeepSeek Reasoner Runtime | `app/audit/deepseek_reasoner.py` | Import clean, contract response dict, Exit Code 0 | VPS Python Runtime |
