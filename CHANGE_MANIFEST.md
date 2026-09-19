# 📝 [CHANGE_MANIFEST] INFRA_3D_PROCEDURAL_VOX_INTEGRATION_AND_COT_HARNESS

## 📌 1. Thông Tin Bản Thay Đổi (Change Metadata)
- **Author Role**: Builder / Implementer
- **Target Task**: `INFRA_3D_PROCEDURAL_VOX_INTEGRATION_AND_COT_HARNESS`
- **Scope**: Nối 3D Procedural Three.js vào `VoxOverlayLayer.tsx`, mở rộng `director_planner_b3.py`, tích hợp `deepseek_reasoner.py`, và dọn dẹp Option A.

---

## 📂 2. Danh Mục File Đã Thay Đổi (Touched Files)

### A. Core Pipeline & Remotion Video Engine
1. **[NEW] `remotion/src/components/EvidenceProp3D.tsx`**:
   - Dựng hình procedural con dấu triện đỏ Hanko / Asian Imperial Seal bằng code Three.js thuần túy (`CylinderGeometry`, `SphereGeometry`, `TorusGeometry`).
   - Phối màu Stylized Comic Noir cel-shading với viền mực đen inverted hull, 0% photorealistic (Rule 122).
   - Diễn hoạt camera orbit 360° đồng bộ từng frame bằng `useCurrentFrame()`.
2. **[MODIFY] `remotion/src/components/vox/VoxOverlayLayer.tsx`**:
   - Nhập khẩu `EvidenceProp3D`.
   - Bổ sung nhánh render cho `rawType === "evidence_3d_prop" | "3d_hanko_seal" | "3d_evidence_prop"`.
   - Thiết lập khung hiển thị card noir bo góc có viền phát sáng cyan (`width: isFullBleed ? 1200 : 700`, `height: isFullBleed ? 750 : 480`).
3. **[MODIFY] `remotion/src/index.tsx`**:
   - Đăng ký composition độc lập `EvidenceProp3DTest` phục vụ kiểm định trực quan nhanh.
4. **[MODIFY] `app/services/director_planner_b3.py`**:
   - Bổ sung quy tắc nhận diện số 5 trong `detect_forensic_overlay()` cho các từ khóa tang vật bản địa (`hanko`, `seal`, `stamp`, `con dấu`, `triện`, `mộc đỏ`, `vật chứng`, `tang vật`, `도장`, `인감`, `증거물`).
   - Trả về payload chuẩn: `type: "evidence_3d_prop"`, `layout: "split_right"`, `badge: "PHYSICAL EXHIBIT"`, `sfx_cue: "stamp_slam"`.

### B. Audit & Multi-Agent Council Engine
5. **[NEW] `app/audit/deepseek_reasoner.py`**:
   - Module chuyên trách cho vai *Adversarial Auditor* trong hội đồng multi-agent.
   - Hỗ trợ gọi API DeepSeek Reasoner (`deepseek-reasoner`), bóc tách tường minh cả 2 trường `reasoning_content` (CoT chain) và `content` (phán quyết `CLEAR` / `VETO`).
   - Tích hợp bộ prompt kiểm toán đối kháng 3 trục thép: Rule 130 (Causal Integrity), Rule 125 & 128 (Ghost Code & Bias), Rule 136 (Zero Asset Leak).
6. **[MODIFY] `.agents/skills/vf-pipeline-teamwork/SKILL.md`**:
   - Chuẩn hóa vai trò số 4: *Adversarial Auditor powered by DeepSeek-R1 CoT*.
7. **[MODIFY] `C:\Users\hunghd2\.gemini\config\skills\remotion\SKILL.md`**:
   - Hợp nhất cẩm nang Remotion duy nhất: bổ sung chunking 5-Beat, still frame preview runbook, background render VPS.
8. **[DELETE] `.agents/skills/remotion-*` (13 folders)**:
   - Dọn sạch 13 thư mục generic boilerplate không dùng theo Option A.

### C. Test Harness
9. **[NEW] `tests/test_evidence_3d_prop_pipeline.py`**:
   - 5 bài kiểm thử unit & integration cho 3D prop detection trên các ngôn ngữ (EN, VN, KR) và bảo toàn tính tương thích ngược cho các overlay 2D cũ.

---

## 🛡️ 3. Kiểm Tra Ghost Code & Biên Dịch (Rule 125 & Rule 127)
- `python3 -m py_compile app/services/director_planner_b3.py` ➔ **Exit code 0**
- `python3 -m py_compile app/audit/deepseek_reasoner.py` ➔ **Exit code 0**
- `pytest tests/test_evidence_3d_prop_pipeline.py` ➔ **5/5 PASSED trên cả Local và VPS**
- `npx remotion bundle` ➔ **Exit code 0**
