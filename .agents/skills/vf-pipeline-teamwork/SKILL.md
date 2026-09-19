---
name: vf-pipeline-teamwork
description: >-
  Điều phối Hội Đồng Multi-Agent Harness 4 vai (Architect, Builder, QA Test Harness, Adversarial Auditor - strictly review), 3 Cặp Docs, Thẩm định Đồng thời và Alibaba OCR Engine.
  Kích hoạt khi nhận /vf-pipeline-teamwork, /teamwork:pipeline, /run:teamwork, /vf:teamwork hoặc yêu cầu council review, CI/CD gates, sync VPS-GitHub-Local cho B1..B11.
---

# 🛡️ VF Pipeline Multi-Agent Harness Council Engine (`/vf-pipeline-teamwork`)

> **Master Council & Harness Engine** cho dây chuyền video **AI Video Factory (VF Pipeline)**.
> Mô hình Hội Đồng 4 Vai Độc Lập • 3 Cặp Docs Pháp Lý • Thẩm Định Đối Kháng Đồng Thời • Alibaba OCR Engine • Hiến Pháp **Rule 118 – Rule 136**.

---

## 👥 I. HỘI ĐỒNG 4 VAI TRÒ ĐỘC LẬP & TRÁCH NHIỆM PHÁP LÝ

| Vai Trò Hội Đồng | Tôn Chỉ & Ranh Giới | Nhiệm Vụ Kỹ Thuật Trọng Tâm | Cặp Tài Liệu Neo Giữ |
| :--- | :--- | :--- | :--- |
| **1. Architect / Planner** | *Defines What/Why; Sets Rigid Boundaries* | Thiết kế khế ước In/Out (`PIPELINE_CONTRACTS.md`); xác lập In-Scope & Non-Goals; phân tích đánh đổi kiến trúc (Rule 129 Trade-offs). | **Doc 1A**: `TASK_SPEC.md` |
| **2. Builder / Implementer** | *Implements to Spec; Zero Ghost Code* | Viết/sửa code bám sát spec; Atomic Commit (Rule 124); dọn sạch `/tmp/` (Rule 119); cấm `.bak*`/shadow code (Rule 125); quét sạch 4 tầng qua `ghost_code_detector.py`; AST `py_compile` exit 0. | **Doc 1B**: `CHANGE_MANIFEST.md` |
| **3. QA & Test Harness** | *Trust Nothing; Verify Dynamically* | Soạn test matrix; chạy kiểm thử động trên sandbox/live data (Rule 123); ISO Neighbor-Testing [N-1, N, N+1], Master Smoke Gate, Runtime Live Function Gate (Rule 127); kiểm tra Audio Spine Hard Gate B2.6/B3; trích xuất log Exit Code 0. | **Doc 2A**: `TEST_HARNESS_PLAN.md`<br>⇄ **Doc 2B**: `TEST_VERIFICATION_REPORT.md` |
| **4. Adversarial Auditor** | *Red Team Mindset; Strictly Review-Only* | **CẤM SỬA CODE**. Rà soát AST & Alibaba OCR; kiểm toán 18 Kỷ luật (Rule 118 Zero-Mock, Rule 120 Audio Spine, Rule 125 Zero-Ghost, Rule 128 Anti-Bias, Rule 134 Parity, Rule 136 Zero-Asset-Leak); **Quyền Phủ Quyết Tuyệt Đối (Absolute VETO)**. | **Doc 3A**: `ADVERSARIAL_AUDIT_CHECKLIST.md`<br>⇄ **Doc 3B**: `FORENSIC_VERDICT.md` |

> [!IMPORTANT]
> **Three-Way Physical Sync Gate (Rule 126)**: Hậu kiểm kỹ thuật CHỈ mở khi Hội đồng đạt **Quorum 4/4 Unanimous Pass (0 VETO)** để commit Git từ VPS, push GitHub, CI Watcher green, và đối soát SHA256 bit-for-bit.

---

## 📑 II. KIẾN TRÚC 3 CẶP TÀI LIỆU PHÁP LÝ & BIÊN BẢN HỘI ĐỒNG

Mọi can thiệp mã nguồn bắt buộc sinh đủ bộ hồ sơ pháp lý đối ứng 2 chiều:
1. **Cặp 1 (Planning ⇄ Execution)**: `TASK_SPEC.md` (Spec, ranh giới, khế ước) ⇄ `CHANGE_MANIFEST.md` (Line diffs, AST exit 0, zero-ghost).
2. **Cặp 2 (Testing ⇄ Verification)**: `TEST_HARNESS_PLAN.md` (Test matrix unit/neighbor/smoke) ⇄ `TEST_VERIFICATION_REPORT.md` (Logs live, Exit Code 0).
3. **Cặp 3 (Audit Checklist ⇄ Forensic Verdict)**: `ADVERSARIAL_AUDIT_CHECKLIST.md` (18 Kỷ luật & OCR) ⇄ `FORENSIC_VERDICT.md` (Phán quyết `CLEAR` / `VETO` file:line; cấm sửa code).
4. **Văn Bản Hội Đồng Cấp Cao**: `COUNCIL_DECISION_MATRIX.md` (Tổng hợp 4 phiếu bầu; điều kiện bắt buộc để mở cổng Three-Way Sync).
*👉 Chi tiết template & schema: [doc_pairs_schema.md](./references/doc_pairs_schema.md).*

---

## ⚡ III. QUY TRÌNH THẨM ĐỊNH ĐỒNG THỜI (SIMULTANEOUS VERIFICATION)

Khi Builder nộp `CHANGE_MANIFEST.md`:
1. **Kích hoạt song song**: `QA Test Harness` (chạy test động runtime) và `Adversarial Auditor` (rà soát tĩnh qua AST/OCR/Rule 118-136) vận hành độc lập, không thông đồng, triệt tiêu điểm mù nhận thức (Anti-Bias).
2. **Biểu Quyết Hội Đồng**: Nếu có bất kỳ lỗi nào hoặc lệnh `VETO` từ Auditor ➔ chuyển task về **Remediation Loop** cho Builder sửa (tối đa 3 vòng trước khi hỏi User theo Rule 118/129).
3. **Cấp phép Sync**: Đạt 4/4 Unanimous Pass ➔ Kích hoạt Three-Way Sync đẩy lên VPS & GitHub CI.
*👉 Chi tiết giao thức & state machine: [harness_council_protocol.md](./references/harness_council_protocol.md).*

---

## 🚀 IV. RUNBOOK & CÚ PHÁP ĐIỀU PHỐI NHANH

### 1. Antigravity Slash Commands
| Lệnh | Ý Nghĩa Điều Phối |
| :--- | :--- |
| `/vf-pipeline-teamwork council task:<EP_ID>` | Họp toàn thể Hội Đồng 4 Agent, thẩm định đồng thời và xuất Council Matrix |
| `/vf-pipeline-teamwork plan task:<EP_ID>` | Kích hoạt Agent 1 lập `TASK_SPEC.md` |
| `/vf-pipeline-teamwork build task:<EP_ID>` | Kích hoạt Agent 2 code và nộp `CHANGE_MANIFEST.md` |
| `/vf-pipeline-teamwork test task:<EP_ID>` | Kích hoạt Agent 3 chạy trọn bộ Test Harness (Unit, Neighbor, Smoke) |
| `/vf-pipeline-teamwork audit task:<EP_ID>` | Kích hoạt Agent 4 kiểm toán đối kháng độc lập (chỉ review, có quyền VETO) |
| `/vf-pipeline-teamwork review` | Quét nhanh diff mã nguồn qua Alibaba OCR Engine |
| `/vf-pipeline-teamwork ci` | Chạy bộ 3 CI Quality Gates (ISO Neighbor + E2E Smoke + OCR Direct) |
| `/vf-pipeline-teamwork sync` | Kích hoạt Three-Way Physical Sync (Rule 126) sau khi Council PASS |

### 2. Dòng Lệnh CLI Trên VPS (`scripts/orchestrator/runner.py`)
```bash
python3 scripts/orchestrator/runner.py --mode council --task-id <EP_ID>   # Xuất Council Decision Matrix
python3 scripts/orchestrator/runner.py --mode review                     # Chạy Open Code Review
python3 scripts/orchestrator/runner.py --mode ci                         # Chạy full CI Quality Gates
python3 scripts/orchestrator/runner.py --mode sync                       # Kiểm tra & Đồng bộ 3 Chiều
python3 scripts/orchestrator/runner.py --cleanup-tmp                     # Dọn sạch /tmp (Rule 119)
```
*Gõ từ Windows qua VPS Runner*: `python scripts/vps_runner.py "python3 scripts/orchestrator/runner.py --mode council --task-id <EP_ID>"`

---

## 📚 V. BẢN ĐỒ TRI THỨC SÂU (PROGRESSIVE DISCLOSURE POINTERS)

Nạp chi tiết từng tài liệu Just-in-Time khi thực thi tác vụ cụ thể:
- **Biểu Mẫu Chuẩn 3 Cặp Docs**: [doc_pairs_schema.md](./references/doc_pairs_schema.md)
- **Giao Thức Hội Đồng & Remediation Loop**: [harness_council_protocol.md](./references/harness_council_protocol.md)
- **Ma Trận Phân Nhiệm B1..B11**: [block_matrix.md](./references/block_matrix.md)
- **Tiêu Chuẩn OCR Engine & Invariants**: [ocr_rules.md](./references/ocr_rules.md)
- **Khế Ước Giao Diện Pipeline**: [PIPELINE_CONTRACTS.md](../../../PIPELINE_CONTRACTS.md)

---

## ⚖️ VI. KỶ LUẬT THÉP BẤT BIẾN (RULE 118 – RULE 136)
1. **Rule 118**: Zero-Mock Data; dừng lại hỏi User khi lệch luồng.
2. **Rule 119**: Chỉ dùng codebase chuẩn VPS; dọn sạch `/tmp/`.
3. **Rule 120**: Audio-Anchored Pipeline (Hollywood Audio Spine B2.6/B3; timecode-locked Edge-TTS; Hard Gate cấm 5.0s heuristic).
4. **Rule 121**: Nghiệm thu bằng Exit Code 0, HTTP 200, file:line rõ ràng.
5. **Rule 124**: Atomic commit; chốt giải pháp là code ngay.
6. **Rule 125**: Single Truth; zero ghost code; cấm file `.bak*`; 4-Layer Ghost Hunter (`ghost_code_detector.py`) với quyền VETO tuyệt đối.
7. **Rule 126**: Three-Way Physical Sync (VPS ⇄ GitHub CI ⇄ Local bit-for-bit).
8. **Rule 127**: Bắt buộc kiểm thử runtime hàm sống, cấm chỉ dựa vào `py_compile`.
9. **Rule 128**: Generic contract pattern; cấm hardcode đề tài/tropes vào schema & prompt.
10. **Rule 129**: Phân tích đánh đổi 3 trục trước khi can thiệp kiến trúc.
11. **Rule 134**: Exact Parity sweep toàn diện codebase khi đổi hằng số/schema.
12. **Rule 136**: Zero-Asset-Leak; cấm rò rỉ mã hash, key, đuôi `.png` lên video render.
