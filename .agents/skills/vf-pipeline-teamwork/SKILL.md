---
name: vf-pipeline-teamwork
description: >-
  Điều phối đội ngũ Multi-Agent 4 vai (Debugger Squad, Forensic Auditor, CI Gatekeeper, 3-Way Sync) và Alibaba Open Code Review (OCR).
  Kích hoạt khi nhận các lệnh /vf-pipeline-teamwork, /teamwork:pipeline, /run:teamwork, /vf:teamwork hoặc yêu cầu review code, CI/CD gates, sync VPS-GitHub-Local cho B1..B11.
---

# 🛡️ VF Pipeline Multi-Agent Teamwork Skill (`/vf-pipeline-teamwork`)

> **Master Orchestrator Engine** dành cho dây chuyền sản xuất video tự động **AI Video Factory (VF Pipeline)**.
> Tích hợp động cơ **Alibaba Open Code Review (OCR)**, CLI Runner `scripts/orchestrator/runner.py`, và tuân thủ Hiến pháp **Rule 118 – Rule 136**.

---

## 🎯 I. CƠ CHẾ 4 VAI TRÒ ĐỘC LẬP (4 AUTONOMOUS ROLES)

| Vai Trò | Nhiệm Vụ Cốt Lõi | Công Cụ & Chốt Chặn Bắt Buộc |
| :--- | :--- | :--- |
| **1. Parallel Debuggers Squad** | Chẩn đoán và sửa lỗi trực tiếp trên mã nguồn chuẩn VPS (`/root/video_factory`), bóc tách theo từng khối B1..B11. | Thu hồi sạch `/tmp/` (Rule 119); cấm script shadow/file `.bak*` (Rule 125). |
| **2. Forensic Auditor & OCR Judge** | Thẩm định khách quan kịch bản (Story Gate 12/12, Rule 444 Hook), visual 4 trục (Rule 122), và kiểm toán mã nguồn line-level diff qua OCR. | Zero Trust; kiểm tra `.opencodereview/rule.json`; cấm rò rỉ ngữ cảnh (Rule 128); chặn memory/FD leaks. |
| **3. CI/CD Quality Gatekeeper** | Tự động kích hoạt toàn bộ các chốt chặn kiểm thử tự động trước khi phê duyệt. | **Chốt 1**: ISO Neighbor-Testing `ci_neighbor_tester.py`<br>**Chốt 2**: Master Smoke Gate `e2e_pipeline_smoketest.py`<br>**Chốt 3**: OCR Gate (Zero High/Critical Defect). |
| **4. Three-Way Sync Coordinator** | Bảo chứng đồng bộ dữ liệu 3 chiều tuyệt đối: **VPS ⇄ GitHub ⇄ Local/Notion**. | `py_compile` AST + Runtime hàm sống (Rule 127) + Git commit/push từ VPS + GitHub Actions CI Watcher `success` + SHA256 parity. |

---

## ⚡ II. CÚ PHÁP & RUNBOOK NHANH (INVOCATION RUNBOOK)

### 1. Chat UI Antigravity
```markdown
/vf-pipeline-teamwork review                               # Quét mã nguồn vừa sửa đổi qua OCR Engine
/vf-pipeline-teamwork ci                                   # Chạy toàn trình CI Quality Gates (ISO + Smoke + OCR)
/vf-pipeline-teamwork sync                                 # Kích hoạt quy trình Đồng Bộ Vật Lý 3 Chiều
/vf-pipeline-teamwork 1.0..3.5 task:<EP_ID>                # Chạy full đội 4 vai cho Block 1.0 đến 3.5
/vf-pipeline-teamwork 4.0,5.0 task:<EP_ID>                 # Chạy kiểm thử & audit Block 4.0 (Sinh ảnh) & 5.0 (Chroma HSV)
/vf-pipeline-teamwork audit task:<EP_ID>                   # Kiểm toán độc lập kịch bản và đạo diễn phân cảnh
```

### 2. Dòng Lệnh CLI Tiêu Chuẩn Trên VPS (`scripts/orchestrator/runner.py`)
```bash
python3 scripts/orchestrator/runner.py --mode review                 # Chạy Open Code Review
python3 scripts/orchestrator/runner.py --mode ci                     # Chạy trọn bộ CI Quality Gates
python3 scripts/orchestrator/runner.py --mode sync                   # Kiểm tra & Đồng bộ 3 Chiều
python3 scripts/orchestrator/runner.py --mode pipeline --blocks 1.0..3.5 --task-id <EP_ID>
python3 scripts/orchestrator/runner.py --cleanup-tmp                 # Dọn sạch file rác /tmp (Rule 119)
```
*Ghi chú từ máy Windows qua VPS runner*:
```powershell
python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode review"
python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode ci"
```

---

## 📚 III. TÀI LIỆU THAM CHIẾU CHUYÊN SÂU (PROGRESSIVE DISCLOSURE)

Để tối ưu hóa token và độ sâu ngữ cảnh, chỉ nạp thêm tài liệu chi tiết khi có nhu cầu:
- **Chi tiết từng Block B1.0 ➔ B11.0**: Mở [block_matrix.md](./references/block_matrix.md) khi cần xem chi tiết nhiệm vụ từng block.
- **Chi tiết Quy Chuẩn & Cú Pháp OCR**: Mở [ocr_rules.md](./references/ocr_rules.md) khi cần cấu hình hoặc đối soát luật `.opencodereview/rule.json`.
- **Khế Ước Dữ Liệu Liên Khối (Data Schema)**: Tra cứu tại [PIPELINE_CONTRACTS.md](../../../PIPELINE_CONTRACTS.md).

---

## ⚖️ IV. KỶ LUẬT THÉP BẮT BUỘC
Mọi Agent/Subagent bắt buộc tuân thủ 100% Hiến pháp **Rule 118 – Rule 136** trong `AGENTS.md`:
- Rule 118 (Zero-Mock Data) & Rule 119 (Dọn rác `/tmp/`).
- Rule 121 (Bằng chứng pháp y HTTP 200/Exit 0/File Line) & Rule 125 (Zero-Ghost / Single Truth).
- Rule 126 (Đồng bộ 3 chiều + GitHub Actions CI Watcher Green) & Rule 127 (Thực thi hàm sống).
- Rule OCR (Zero Critical/High Defect Gate trước khi chuyển giao).
