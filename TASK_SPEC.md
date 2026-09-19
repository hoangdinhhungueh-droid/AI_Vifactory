# 📐 [TASK_SPEC] INFRA_3D_PROCEDURAL_VOX_INTEGRATION_AND_COT_HARNESS

## 📌 1. Bối Cảnh & Ranh Giới (Context & Boundaries)
- **Feature Title**: 3D Procedural Evidence Prop Engine & DeepSeek-R1 CoT Forensic Auditor
- **Primary Blocks Impacted**:
  - `B3.0` (`app/services/director_planner_b3.py`): Nhận diện và gán lớp đồ họa pháp y `evidence_3d_prop`.
  - `B6.0` (`app/services/build_remotion_props.py`): Đóng gói trường `forensicOverlay` cho Remotion.
  - `B7.0` (`remotion/src/components/vox/VoxOverlayLayer.tsx`): Kết xuất `<EvidenceProp3D />` theo tọa độ layout.
  - `Audit / Council Engine` (`app/audit/deepseek_reasoner.py` & `.agents/skills/vf-pipeline-teamwork/`): Tích hợp DeepSeek-R1 CoT.
- **In-Scope**:
  - Tích hợp `EvidenceProp3D` vào `VoxOverlayLayer.tsx` (chế độ `split_right`, `split_left`, `full_bleed_focus`).
  - Mở rộng `detect_forensic_overlay()` trong `director_planner_b3.py` để tự động nhận diện từ khóa ấn phẩm/vật chứng bản địa (`hanko`, `seal`, `stamp`, `con dấu`, `triện`, `mộc đỏ`, `vật chứng`, `chứng thực`).
  - Viết test suite `tests/test_evidence_3d_prop_pipeline.py` thẩm định trọn vẹn B3 ➔ B6 ➔ B7.
  - Xác lập bộ 3 Cặp Docs Pháp Lý Hội Đồng theo `/vf-pipeline-teamwork`.
- **Non-Goals**:
  - Không phá vỡ kiến trúc Two-Layer (`Layer 1 BG 16:9 + Layer 2 FG 1:1 + Subtitle HUD`).
  - Không đụng chạm Audio Spine Hard Gate B2.6/B3 (Rule 120).
  - Không nạp file mesh nhị phân 3D cồng kềnh (`.glb`/`.obj`); 100% procedural Three.js.

---

## 🎯 2. Yêu Cầu Kỹ Thuật (Requirements R1 - R5)
- **R1 (3D Procedural Wiring)**: `EvidenceProp3D` được gắn trực tiếp vào `VoxOverlayLayer.tsx` dưới `rawType === "evidence_3d_prop" | "3d_hanko_seal" | "3d_evidence_prop"`.
- **R2 (Responsive Layout Frame)**: Khi kích hoạt, component 3D co giãn theo layout (`isFullBleed ? 1200x750 : 700x500`), giữ vững viền noir và shadow card.
- **R3 (B3 Director Detection)**: `director_planner_b3.py` tự động kích hoạt `evidence_3d_prop` khi kịch bản nhắc tới tang vật con dấu/triện đỏ/vật chứng chứng thực.
- **R4 (DeepSeek-R1 CoT Auditor)**: `app/audit/deepseek_reasoner.py` trích xuất `reasoning_content` để thẩm định Rule 130, Rule 125, Rule 136.
- **R5 (VPS & CI/CD Parity)**: Biên dịch bundle và render test trên VPS Hetzner đạt Exit Code 0, CPU SWangle 6.0 fps, 0 VRAM.

---

## 🔒 3. Khế Ước Dữ Liệu (Interface Contracts)
- **Overlay Type**: `evidence_3d_prop`
- **Schema `forensicOverlay`**:
  ```json
  {
    "type": "evidence_3d_prop",
    "legacy_type": "evidence_board",
    "theme": "vox_paper",
    "layout": "split_right",
    "title": "CONFIDENTIAL EVIDENCE // FORENSIC ARTIFACT",
    "badge": "PHYSICAL EXHIBIT",
    "sfx_cue": "stamp_slam",
    "label": "AUTHENTICATED IMPERIAL SEAL // 3D PROCEDURAL ARTIFACT",
    "payload": {
      "prop_type": "hanko_seal",
      "evidence_id": "EXHIBIT-3D-01",
      "authentication": "VERIFIED PHYSICAL TAMPER-PROOF"
    }
  }
  ```
