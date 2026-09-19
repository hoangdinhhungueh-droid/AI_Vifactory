# 🕵️ [ADVERSARIAL_AUDIT_CHECKLIST] INFRA_3D_PROCEDURAL_VOX_INTEGRATION_AND_COT_HARNESS

## 📌 1. Bối Cảnh Kiểm Toán Pháp Y (Forensic Audit Scope)
- **Auditor Role**: Adversarial Auditor (Red Team Mindset, Strictly Review-Only, Powered by DeepSeek-R1 CoT Harness)
- **Nguyên Tắc**: Quyền phủ quyết tuyệt đối (Absolute VETO). Không sửa code, chỉ soi xét lỗi và cấp phán quyết.
- **Đối Tượng Rà Soát**: Toàn bộ diffs mã nguồn trong `remotion/`, `app/services/director_planner_b3.py`, `app/audit/deepseek_reasoner.py`, và `.agents/skills/`.

---

## ⚖️ 2. Bảng Đối Soát 18 Kỷ Luật Thép (Iron Laws Audit Matrix)

| Kỷ Luật Thép | Tiêu Chuẩn Rà Soát | Bằng Chứng Pháp Y | Đánh Giá |
| :--- | :--- | :--- | :--- |
| **Rule 118** (Zero-Mock Data) | Không tạo mock data hay giả lập số liệu | Không tạo mock CTR hay số liệu ảo; toàn bộ test dựa trên input text thực tế | ✅ PASS |
| **Rule 119** (Strict VPS Codebase & Cleanup) | File tạm `/tmp/` phải được dọn sạch sẽ | Toàn bộ bundle test và render test `/tmp/poc_3d*` đã được dọn sạch | ✅ PASS |
| **Rule 120** (Hollywood Audio Spine) | Cấm phá vỡ timing `durationInFrames` | 3D Evidence Prop gắn vào `VoxOverlayLayer`, tuân thủ 100% frame duration của scene do Whisper cấp | ✅ PASS |
| **Rule 121** (Strict Verification Protocol) | Bằng chứng Exit Code 0 thực tế | Pytest 5/5 PASSED, bundle exit 0, render exit 0 | ✅ PASS |
| **Rule 122** (Pixel-Level Visual Audit) | 100% Stylized Comic Noir, 0% photorealistic | `EvidenceProp3D` dùng `MeshToonMaterial` + ink outline black, không dùng photorealistic mesh | ✅ PASS |
| **Rule 124** (Atomic Code-ification) | Chốt giải pháp là code ngay xuống đĩa | Đã code và đồng bộ bit-for-bit xuống cả Local và VPS | ✅ PASS |
| **Rule 125** (Zero Ghost Code) | Cấm `.bak*`, orphan scripts, shadow code | Không sinh file backup rác, 13 folder generic đã được xóa sạch | ✅ PASS |
| **Rule 126** (Three-Way Physical Sync) | VPS ⇄ GitHub ⇄ Local parity | SHA256 đối soát khớp 100% qua `sync_file_to_vps.py` | ✅ PASS |
| **Rule 127** (Runtime Function Execution) | Cấm chỉ dựa vào `py_compile` đơn thuần | Đã chạy sống pytest và render headless video 90 frames trên VPS | ✅ PASS |
| **Rule 128** (Anti-Semantic Bias) | Schema generic, cấm hardcode tropes | `evidence_3d_prop` hỗ trợ đa ngôn ngữ EN, VN, KR qua regex tổng quát | ✅ PASS |
| **Rule 130** (Factual Causal Integrity) | Catalyst vs Transmission; cấm bịa twist | Module `deepseek_reasoner.py` bổ sung chốt chặn CoT kiểm toán nhân quả | ✅ PASS |
| **Rule 134** (Exact Parity & Sweep) | Không để lệch pha cấu hình giữa các file | Cả Local và VPS đều đồng bộ Three.js 0.160.1 và TSX components | ✅ PASS |
| **Rule 136** (Zero-Asset-Leak) | Cấm rò rỉ mã hash, filename lên video | Thẻ tiêu đề 3D Prop chỉ hiển thị `title` và `subtitle` chuẩn, 0% file name `.png` | ✅ PASS |
