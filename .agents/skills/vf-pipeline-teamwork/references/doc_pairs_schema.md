# 📄 Biểu Mẫu Chuẩn Các Cặp Tài Liệu Pháp Lý (Doc Pairs Schema)

> **Tài liệu quy chuẩn cấu trúc văn bản (Progressive Disclosure Reference)** cho Skill `/vf-pipeline-teamwork`.
> Thiết lập mẫu chuẩn (Templates & Schemas) cho **3 Cặp Tài Liệu Pháp Lý** và **Biên Bản Hội Đồng (Council Matrix)** phục vụ kiểm toán CI/CD full luồng.

---

## 📑 I. CẶP 1: PLANNING ⇄ EXECUTION

### 1. Doc 1A: `TASK_SPEC.md` (Lập bởi Architect/Planner)
```markdown
# 📋 [TASK_SPEC] <TASK_ID> — <TASK_TITLE>

## 🎯 1. Mục Tiêu Nghiệp Vụ & Bối Cảnh
- **Mục tiêu**: <Mô tả mục tiêu kỹ thuật hoặc nghiệp vụ>
- **Pipeline Block**: <B1.0 .. B11.0 hoặc Infrastructure>
- **Nguyên lý chi phối**: <Rule 118, Rule 128, Rule 130...>

## 📐 2. Khế Ước Giao Diện (Interface Contract)
- **Đầu vào (Input Files/Schema)**:
  - `<file_path_in>`: `<schema / format>`
- **Đầu ra (Output Files/Schema)**:
  - `<file_path_out>`: `<schema / format>`
- **Generic Task ID Pattern**: `^[A-Z]{2}_EP\d{4}_[a-z0-9_]+$` (Rule 128)

## 🛑 3. Ranh Giới & Non-Goals
- **In-Scope (Phạm vi cho phép sửa)**:
  - `<relative_path_file_1>`
  - `<relative_path_file_2>`
- **Out-of-Scope (Ranh giới cấm chạm)**:
  - `<critical_core_file>` (Bất biến)

## ⚖️ 4. Đánh Đổi Kiến Trúc & Rủi Ro (Rule 129 Trade-Offs)
- **Option A vs Option B**: <Phân tích đánh đổi>
- **Biện pháp phòng ngừa rủi ro**: <Kế hoạch kiểm soát>
```

### 2. Doc 1B: `CHANGE_MANIFEST.md` (Lập bởi Builder/Implementer)
```markdown
# 🛠️ [CHANGE_MANIFEST] <TASK_ID> — <TASK_TITLE>

## 📌 1. Trạng Thái Thực Thi (Execution Metadata)
- **Builder Agent**: <Agent ID / Name>
- **Thời điểm hoàn tất**: <ISO 8601 Timestamp>
- **AST Py-Compile**: `EXIT CODE 0` (Bắt buộc)

## 📝 2. Chi Tiết File Sửa Đổi (Line-Level Changes)
### `path/to/file1.py`
- **Phạm vi dòng sửa**: L<StartLine> - L<EndLine>
- **Mục đích sửa**: <Giải thích ngắn gọn>
- **SHA256**: `<hash_file>`

## 🧹 3. Cam Kết Dọn Rác & Zero-Ghost (Rule 119 & 125)
- [x] Không để lại file tạm rác trong `/tmp/`
- [x] Không tạo file `.bak*`, `.backup*`, file shadow
- [x] Đã đồng bộ comment/docstring nội hàm (Rule 125 Single Truth)
```

---

## 📑 II. CẶP 2: TESTING ⇄ VERIFICATION

### 1. Doc 2A: `TEST_HARNESS_PLAN.md` (Lập bởi QA & Test Harness Agent)
```markdown
# 🧪 [TEST_HARNESS_PLAN] <TASK_ID> — <TASK_TITLE>

## 🎯 1. Chiến Lược Kiểm Thử (Test Strategy)
- **Phạm vi bao phủ**: Unit, Neighbor Testing, Boundary, Contract Schema.
- **Môi trường**: Sandbox cách ly (Rule 119) / Live Data (Rule 123).

## 📊 2. Ma Trận Test Cases
| ID | Hạng Mục Kiểm Thử | Lệnh Thực Thi (Command) | Kết Quả Kỳ Vọng | Ngưỡng Timeout |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Unit Syntax & Types | `pytest tests/test_<module>.py` | 100% Passed, Exit 0 | 30s |
| **TC-02** | ISO Neighbor-Testing | `python3 tests/ci_neighbor_tester.py --block <X>` | All Neighbors Pass | 60s |
| **TC-03** | Runtime Execution Gate | `python3 -c "from <mod> import <func>; <func>()"` | Exit 0 (Rule 127) | 15s |
| **TC-04** | Master Smoke Gate | `python3 scripts/e2e_pipeline_smoketest.py` | Exit 0 | 120s |
```

### 2. Doc 2B: `TEST_VERIFICATION_REPORT.md` (Lập bởi QA & Test Harness Agent)
```markdown
# 📊 [TEST_VERIFICATION_REPORT] <TASK_ID> — <TASK_TITLE>

## 📌 1. Tổng Kết Pháp Y Kiểm Thử
- **Tổng số test cases**: <N>
- **Passed**: <N_PASS> | **Failed**: <N_FAIL> (Bắt buộc = 0)
- **Exit Code Chung**: `0`
- **Thời lượng thực thi**: <Total Seconds>s

## 🔍 2. Bằng Chứng Thực Thi Từng Hạng Mục (Forensic Logs)
### [TC-01] Pytest Unit
```text
<Trích dẫn stdout pytest: N passed in X.XXs>
```
Exit Code: `0`

### [TC-02] ISO Neighbor-Testing
```text
<Trích dẫn log neighbor: Gate 1 PASS, Gate 2 PASS>
```
Exit Code: `0`

### [TC-03] Runtime Execution Gate (Rule 127)
```text
<Trích dẫn kết quả chạy hàm sống>
```
Exit Code: `0`

## 🏁 3. Kết Luận Của Test Harness Agent
- **Đánh giá**: `READY_FOR_COUNCIL` (Chỉ khi 100% TC đạt Exit Code 0).
```

---

## 📑 III. CẶP 3: AUDIT CHECKLIST ⇄ FORENSIC VERDICT

### 1. Doc 3A: `ADVERSARIAL_AUDIT_CHECKLIST.md` (Nắm giữ bởi Adversarial Auditor)
```markdown
# 🔍 [ADVERSARIAL_AUDIT_CHECKLIST] <TASK_ID>

## ⚖️ 1. Kiểm Toán 18 Kỷ Luật Thép (AGENTS.md)
- [ ] **Rule 118 (Zero-Mock Data)**: 0 hardcoded views, 0 fake metrics.
- [ ] **Rule 119 (Existing Codebase Only)**: 0 shadow scripts, clean temp.
- [ ] **Rule 121 (Forensic Verification)**: Có bằng chứng exit 0, file:line rõ ràng.
- [ ] **Rule 124 (Atomic Commitment)**: Không để lại TODOs hoặc logic dở dang.
- [ ] **Rule 125 (Single Truth & Zero-Ghost)**: 0 file `.bak*`, 0 logic cũ tồn tại song song.
- [ ] **Rule 127 (Runtime Live Execution)**: Đã kiểm chứng hàm sống trên Python runtime.
- [ ] **Rule 128 (Generic Contract)**: 0 hardcoded topic bias/tropes trong code & prompt.
- [ ] **Rule 130/131 (Story Purity)**: Hook 60s, 5-beat docudrama, không mở đầu bằng "Imagine".
- [ ] **Rule 134 (Full-Text Consistency)**: Không lệch pha hằng số, threshold, schema.
- [ ] **Rule 136 (Zero-Asset-Leak)**: 0 rò rỉ asset hash, key, đuôi `.png` lên video/subtitle.

## 🛡️ 2. Tiêu Chuẩn OCR Code Review (Alibaba OCR Engine)
- [ ] Memory Management: Buffer giải phóng an toàn (Sharp, Pillow, OpenCV).
- [ ] Resource & FD Leaks: Đóng 100% subprocess pipes & audio streams.
- [ ] Concurrency Safety: Không có race conditions.
- [ ] Encoding: 100% UTF-8 explicit I/O.
- [ ] Error Handling: Không có bare `except:` hoặc `pass` câm.
```

### 2. Doc 3B: `FORENSIC_VERDICT.md` (Ban hành bởi Adversarial Auditor)
```markdown
# ⚖️ [FORENSIC_VERDICT] <TASK_ID> — <TASK_TITLE>

## 🛡️ 1. Nguyên Tắc Thẩm Định Độc Lập
- **Auditor Role**: *Strictly Review-Only — Red Team Mindset. KHÔNG VIẾT CODE SỬA CHỮA.*
- **Thời điểm kiểm toán**: <ISO 8601 Timestamp>

## 🚨 2. Bảng Khuyết Tật Đối Kháng (Defect Findings)
| ID | Mức Độ | File & Line | Nguyên Nhân & Vi Phạm Kỷ Luật | Yêu Cầu Khắc Phục (Dành cho Builder) |
| :--- | :--- | :--- | :--- | :--- |
| *DEF-01* | `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` | `path/to/file.py:L12-18` | Vi phạm Rule ... | Sửa lại logic ... |

*(Nếu không có khuyết tật: Ghi nhận "Zero Defects Detected")*

## ⚖️ 3. Phán Quyết Cuối Cùng (Auditor Ruling)
- **Trạng thái**: `CLEAR` (Đồng ý thông qua) HOẶC `VETO` (Phủ quyết - Bắt buộc sửa lại).
- **Lý do phán quyết**: <Tóm tắt căn cứ pháp lý>
```

---

## 🏛️ IV. VĂN BẢN HỘI ĐỒNG: `COUNCIL_DECISION_MATRIX.md`

```markdown
# 🏛️ [COUNCIL_DECISION_MATRIX] <TASK_ID> — <TASK_TITLE>

## 🗳️ 1. Ma Trận Biểu Quyết Hội Đồng (Council Quorum)
| Thành Viên Hội Đồng | Vai Trò | Căn Cứ Bỏ Phiếu | Lá Phiếu | Chữ Ký / Trạng Thái |
| :--- | :--- | :--- | :---: | :---: |
| **Agent 1** | Architect / Planner | `TASK_SPEC.md` | `AGREE` / `DISAGREE` | [SIGNED] |
| **Agent 2** | Builder / Implementer | `CHANGE_MANIFEST.md` | `COMMITTED` | [SIGNED] |
| **Agent 3** | QA & Test Harness | `TEST_VERIFICATION_REPORT.md` | `PASS` / `FAIL` | [SIGNED] |
| **Agent 4** | Adversarial Auditor | `FORENSIC_VERDICT.md` | `CLEAR` / `VETO` | [SIGNED] |

## ⚖️ 2. Kết Quả Hội Đồng (Council Consensus Verdict)
- **Trạng thái**: `APPROVED_FOR_SYNC` (Đạt 4/4 Unanimous Pass) HOẶC `REVISE_REQUIRED` (Có VETO / Defect).
- **Hành động kế tiếp**:
  - Nếu `APPROVED_FOR_SYNC`: Kích hoạt **Three-Way Physical Sync Gate** (VPS commit/push, GitHub CI Watcher, Local parity).
  - Nếu `REVISE_REQUIRED`: Chuyển task về Builder cho Vòng Lặp Sửa Chữa (Remediation Loop #<iteration>/3).
```
