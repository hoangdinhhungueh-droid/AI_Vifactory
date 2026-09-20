# 🛡️ [ADVERSARIAL_AUDIT_CHECKLIST] VOX_PARALLAX_ATMOSPHERE_AND_AI_TIMELINE_EDITOR

> **Vai trò**: Adversarial Auditor (Red Team, Strictly Review-Only, VETO Authority).
> **Tiêu chí**: Rà soát 18 Kỷ luật thép (Rule 118 – Rule 136), không thỏa hiệp, không nghiệm thu hình thức.

---

## 🔍 I. BẢNG KIỂM TRA ĐỐI KHÁNG 18 KỶ LUẬT THÉP

| Kỷ Luật Thép | Nội Dung Trọng Tâm Cần Soát | Trạng Thái Dự Kiến | Ghi Chú Pháp Y |
| :--- | :--- | :---: | :--- |
| **Rule 118** | Zero-Mock Data; Dừng lại hỏi User khi lệch luồng; Graceful fallback không fake số liệu. | ⏳ PENDING | Timeline Editor phải dùng dữ liệu live từ `whisper_segments.json`. Cấm giả định timestamps. |
| **Rule 119** | Strict Existing Codebase; dọn sạch `/tmp/` qua `resource_recycler.py`. | ⏳ PENDING | Mọi file tạm kiểm thử Remotion phải lưu tại `/tmp/` và dọn dẹp sạch sẽ. |
| **Rule 120** | Audio-Anchored Hard Gate; cấm heuristic 5.0s thô; khóa theo Whisper word timestamps. | ⏳ PENDING | Pacing edits bắt buộc tôn trọng tổng thời lượng của từng câu thoại TTS. |
| **Rule 121** | Strict Verification; Exit Code 0, logs thực tế; cấm nghiệm thu bằng mắt suông. | ⏳ PENDING | Bắt buộc in Exit Code 0 từ `pytest`, `remotion bundle`, và `runner.py --mode ci`. |
| **Rule 122** | Pixel-Level Visual Audit; 0% UI dính lỗi, viền mịn, đúng phong cách Graphic Novel. | ⏳ PENDING | 2.5D Parallax và Atmospheric Lighting phải giữ vững cel-shading comic noir, cấm lem màu. |
| **Rule 124** | Atomic Code-ification; chốt là code ngay; cấm hứa hẹn suông. | ⏳ PENDING | Thực thi code xuống đĩa VPS & Local ngay trong cùng phiên làm việc. |
| **Rule 125** | Single Truth & Zero-Ghost Remnant; cấm `.bak*`, orphan scripts, dead code. | ⏳ PENDING | Chạy `ghost_code_detector.py` quét toàn bộ đĩa cứng vật lý; 0 defect mới được pass. |
| **Rule 126** | Three-Way Physical Sync (VPS ⇄ GitHub CI ⇄ Local bit-for-bit SHA256). | ⏳ PENDING | Bắt buộc đối soát `git status` clean và GitHub Actions Workflow run thành công. |
| **Rule 127** | Anti-Tunnel-Vision; bắt buộc thực thi hàm sống runtime, cấm chỉ dựa vào `py_compile`. | ⏳ PENDING | Chạy trực tiếp `python3 -c "from app.services.timeline_editor_agent import ..."` trên VPS. |
| **Rule 128** | Anti-Semantic-Bias & Generic Contract; cấm hardcode tên tập/nhân vật/vụ án vào prompt. | ⏳ PENDING | Prompts và schemas của Timeline Editor phải generic 100% (dùng placeholders `<MARKET>`, `<TOPIC>`). |
| **Rule 130** | Factual Causal Integrity; cấm bịa đặt quan hệ nhân quả. | ⏳ PENDING | AI Editor chỉ tối ưu hóa visual presentation, không được tự ý sửa văn bản narration gốc. |
| **Rule 132** | Decoupled Engine; code là ống dẫn thuần túy, prompt lưu tại config/Notion. | ⏳ PENDING | Toàn bộ prompt chỉ đạo đạo diễn hậu kỳ lưu tại `config/prompts/` hoặc Notion SoT. |
| **Rule 134** | Exact Parity Sweep; đồng nhất hằng số và schema trên toàn bộ repo. | ⏳ PENDING | Khế ước `remotion_props.json` phải đồng nhất trên cả TypeScript component và Python builder. |
| **Rule 136** | Zero-Asset-Leak; cấm rò rỉ mã asset, reuse_key, hash lên video render. | ⏳ PENDING | Speaker tag chỉ hiển thị `TÊN // VAI TRÒ` hoặc `BEAT <X>: <TIÊU ĐỀ>`, cấm lộ mã nội bộ. |

---

## ⚖️ II. ĐIỀU KIỆN KÍCH HOẠT QUYỀN PHỦ QUYẾT (VETO TRIGGERS)
1. Phát hiện file `.bak*` hoặc orphan files trong repo.
2. `remotion bundle` trả exit code $\neq 0$ hoặc có cảnh báo TypeScript missing properties.
3. Audio Spine bị lệch > 0.1s so với file âm thanh thực tế.
4. Có biến chuỗi prompt nghiệp vụ bị hardcode trực tiếp vào file `.py` vi phạm Rule 132.
