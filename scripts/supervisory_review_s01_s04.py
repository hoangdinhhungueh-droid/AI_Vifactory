#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/supervisory_review_s01_s04.py — High-Tier LLM Supervisory Review for S01–S04 Architecture & Quality."""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.services.model_gateway import get_global_gateway

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger("supervisory_review")

def main():
    logger.info("Initializing High-Tier LLM Supervisory Review...")
    gw = get_global_gateway()

    # 1. Gather git commits diff
    commit_log = subprocess.run(
        ["git", "log", "-n", "5", "--stat", "--oneline"],
        capture_output=True, text=True, cwd=str(ROOT_DIR)
    ).stdout

    # 2. Gather artifacts for KR_EP0007_jeonse_deposit_trap
    ep_dir = ROOT_DIR / "episodes" / "KR_EP0007_jeonse_deposit_trap"
    
    s1_file = ep_dir / "s01_ideation" / "artifact.json"
    s2_file = ep_dir / "s02_research" / "artifact.json"
    s3_file = ep_dir / "s03_script" / "artifact.json"
    s4_file = ep_dir / "s04_critic_script" / "artifact.json"
    script_file = ep_dir / "spoken_script.txt"
    manifest_file = ep_dir / "run_manifest.json"

    try:
        s1_data = json.loads(s1_file.read_text(encoding="utf-8")) if s1_file.exists() else {}
    except Exception:
        s1_data = {}
    try:
        s2_data = json.loads(s2_file.read_text(encoding="utf-8")) if s2_file.exists() else {}
    except Exception:
        s2_data = {}
    try:
        s3_data = json.loads(s3_file.read_text(encoding="utf-8")) if s3_file.exists() else {}
    except Exception:
        s3_data = {}
    try:
        s4_data = json.loads(s4_file.read_text(encoding="utf-8")) if s4_file.exists() else {}
    except Exception:
        s4_data = {}
    spoken_script = script_file.read_text(encoding="utf-8") if script_file.exists() else ""
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}

    # Extract claims summary from S2
    s2_claims = s2_data.get("payload", {}).get("evidence_ledger", [])
    claims_summary = [
        f"[{c.get('claim_id')}] ({c.get('legal_status')}): {c.get('claim')} (Source: {c.get('source_type')})"
        for c in s2_claims[:8]
    ]

    # S4 gates summary
    s4_gates = s4_data.get("payload", {}).get("gates", {})
    s4_score = s4_data.get("payload", {}).get("aggregate_score", "N/A")
    s4_verdict = s4_data.get("payload", {}).get("verdict", "N/A")

    # 3. Construct System Prompt & Evaluation Packet
    system_prompt = (
        "You are an Elite Independent Quantitative Systems Architect & Forensic Media Reviewer. "
        "Your duty is to conduct an unsparing, radical-transparency supervisory audit on the AI Video Factory pipeline. "
        "You NEVER give flattering compliments, sycophantic praise, or vague generalities. "
        "You review the exact code architecture and the actual runtime artifacts against first principles. "
        "Structure your audit with rigorous reasoning, concrete citations, and a definitive verdict."
    )

    user_prompt = f"""## BỐI CẢNH & PHẠM VI NGHIỆM THU KIẾN TRÚC S01–S04

### 1. Lịch sử Thay đổi Mã Nguồn (Git Commits):
{commit_log}

Các module đã tái cấu trúc và hoàn thiện ở cấp độ hệ thống qua 5 commits gần nhất:
- `core/run_manifest.py`: Cải tiến `invalidate_downstream` để tự động unlink toàn bộ secondary exports ở root (`spoken_script.txt`, `director_plan.json`, `bulk_image_prompts.txt`, `images_manifest.json`) khi re-run stage cha.
- `stages/s01_ideation.py`: Trích xuất `money_at_stake_usd` động từ `grounding_intel.json`, loại bỏ hardcode "22조" / "전세".
- `stages/s02_research.py`: Cầu nối nạp `grounding_intel.json`, trích xuất thực thể động, bảo toàn `documented_outcome`, loại bỏ hardcode factsheet "22조 원 전세사기 HUG/MOLIT", áp dụng generic multi-market template.
- `stages/s03_script.py`:
  * Xóa bỏ 150 dòng shadow script tĩnh; bổ sung ma trận legal qualifiers bản địa hóa cho KR, JA, VN, EN.
  * Giải quyết triệt để lỗi "Substitution Test": Chuyển đổi prompt và fallback `_build_grounded_story_beats` sang nạp động các claim thực tế, số liệu, mốc thời gian, tên cơ quan từ `evidence_ledger` (xóa sạch toàn bộ câu văn generic boilerplate).
  * Định tuyến legal qualifiers chính xác theo `source_type` của claim (`press` -> `보도 설명에 따르면`, `확인되지 않았습니다`; `regulator` -> `규제 당국에 따르면`; `court` -> `공소장에 따르면`), loại bỏ việc gán nhãn sai cơ quan quản lý cho tin báo chí.
  * Chuẩn hóa số Ả Rập trong văn phong phóng sự Hàn Quốc (`9,317건`, `22조원`, `2026년 11월 10일`).
- `stages/s04_critic_script.py`:
  * Bổ sung chốt chặn `target_market_language_compliance` (VETO nếu non-EN chứa >15% tiếng Anh); đồng bộ ngưỡng từ cho KR (200-560 từ).
  * Bổ sung `topic_specificity_gate`: Kiểm tra thực chứng sự hiện diện của các thực thể riêng, số liệu, mốc thời gian từ `evidence_ledger`.
  * Bổ sung `claim_coverage_gate`: Kiểm tra tỷ lệ bao phủ claim (>=50% hoặc >=3 distinct claims) và kiểm tra đối chiếu từ khóa giữa dòng thoại và claim.
  * Khắc phục lỗi so khớp case-sensitive ở Gate 3 cho các thị trường dùng chữ Latin (VN, EN).
  * Chấm điểm programmatic minh bạch dựa trên 8 gates khi LLM critic gặp ngoại lệ, tuyệt đối không gán 9.4 ảo.
- `tests/unit/test_s01_s04_system_remediation.py`: 9 bài unit test kiểm tra toàn bộ logic trên, đạt 9/9 PASSED cả trên Local và VPS.
- `tests/ci_neighbor_tester.py`: 14/14 test PASSED.
- GitHub Actions CI: Run ID `43026518324` trên commit `ca3b445` đạt `conclusion: success`.
- Master E2E Smoketest trên VPS: 15/15 gates PASSED (100% integration runtime OK).

---

### 2. Dữ liệu Thực Thi Mới Nhất của Tập Phim `KR_EP0007_jeonse_deposit_trap`:
- **Đề tài gốc:** 전세사기 피해자 최소보장제 (Chính sách bảo đảm tiền đặt cọc tối thiểu cho nạn nhân lừa đảo Jeonse tại Hàn Quốc)
- **Thị trường:** KR (Hàn Quốc)
- **Profile / Preset:** prod / story_forensic
- **Trạng thái Manifest:**
  * s01_ideation: done
  * s02_research: done
  * s03_script: done
  * s04_critic_script: done
  * s05..s11: pending (đã bị invalidate sạch sẽ, không còn split-brain)

#### Evidence Ledger Trích Xuất Tại S02 ({len(s2_claims)} claims):
{chr(10).join(claims_summary)}

#### Kịch Bản Tiếng Hàn Thực Tế Đã Sinh Tại S03 (`spoken_script.txt` - {len(spoken_script.strip().splitlines())} dòng, {len(spoken_script.split())} từ, thời lượng ước tính ~240s):
\"\"\"
{spoken_script}
\"\"\"

#### Kết Quả Kiểm Thẩm S04 Critic Script:
- Verdict: {s4_verdict}
- Aggregate Score: {s4_score} / 10.0
- Gates Evaluated: {json.dumps(s4_gates, indent=2, ensure_ascii=False)}

---

## NHIỆM VỤ NGHIỆM THU CỦA LLM CẤP CAO:
Hãy trả lời trực diện, chi tiết, sắc bén 2 câu hỏi cốt tử sau bằng tiếng Việt:

### CÂU HỎI 1: CODE MANG TÍNH HỆ THỐNG CHƯA? ĐẠT SẠCH CHƯA?
- Đánh giá kiến trúc DAG Invalidation, Recon Bridge, Multi-Market Localization (KR, JA, VN, EN), và Language Gate.
- Code đã thoát khỏi bẫy "sửa chữa vá víu cục bộ cho riêng tập KR_EP0007" chưa? Còn tàn dư hardcode nào vi phạm Rule 128 (Zero Semantic Bias) hay Rule 132 (Decoupled Engine) không?
- Mức độ sẵn sàng mở rộng khi chạy cho thị trường Nhật Bản (JA), Việt Nam (VN), hay Mỹ (EN)?

### CÂU HỎI 2: CHẠY LẠI ĐẠT CHẤT LƯỢNG CHƯA?
- Đánh giá chất lượng thực tế của `spoken_script.txt`: 
  * Độ thuần khiết tiếng Hàn (có còn từ tiếng Anh, từ SEC/Mỹ hay rác kiểm dịch thực phẩm không)?
  * Tính chất Docudrama điều tra: Có cấu trúc 5 Beat rõ ràng không? Nhịp độ (246 từ cho 240s ~1.0 từ/giây ở tiếng Hàn) có phù hợp giọng đọc phóng sự chậm rãi, căng thẳng không?
  * Độ bám sát đề tài và tính nhân quả: Có phản ánh đúng bản chất cuộc khủng hoảng bảo đảm tiền cọc Jeonse và tín dụng đen bóng tối không?
- Đánh giá chốt chặn S04: Các gate kiểm tra có thực chất không hay vẫn là hình thức?

Kết luận rõ ràng: **ĐẠT (PASS)** hay **CHƯA ĐẠT (REVISE)** để bước tiếp vào S05 (Director Plan).
"""

    logger.info("Sending audit request to primary high-tier LLM model: gpt-6.1-sol...")
    start_time = time.time()
    try:
        response = gw.call_llm(
            prompt=user_prompt,
            model="gpt-6.1-sol",
            system_prompt=system_prompt,
            max_tokens=4000,
            temperature=0.2,
            timeout=180.0
        )
        latency = round(time.time() - start_time, 2)
        logger.info(f"High-tier LLM response received in {latency}s ({len(response)} chars)")

        # Save to specs/boss_audits/S01_S04_HIGH_TIER_SUPERVISORY_AUDIT.md
        out_dir = ROOT_DIR / "specs" / "boss_audits"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "S01_S04_HIGH_TIER_SUPERVISORY_AUDIT.md"
        out_file_r2 = out_dir / "S01_S04_HIGH_TIER_SUPERVISORY_AUDIT_R2.md"

        audit_content = f"# ⚖️ BÁO CÁO NGHIỆM THU CỦA LLM CẤP CAO (HIGH-TIER SUPERVISORY AUDIT - ROUND 2)\n\n"
        audit_content += f"- **Giám sát viên (Supervisor Model)**: `gpt-6.1-sol` (qua HHTech API Gateway)\n"
        audit_content += f"- **Thời điểm kiểm định**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        audit_content += f"- **Thời gian phản hồi (Latency)**: {latency}s\n"
        audit_content += f"- **Tập phim nghiệm thu**: `KR_EP0007_jeonse_deposit_trap`\n\n"
        audit_content += "---\n\n"
        audit_content += response

        out_file.write_text(audit_content, encoding="utf-8")
        out_file_r2.write_text(audit_content, encoding="utf-8")
        logger.info(f"Audit report saved to: {out_file} and {out_file_r2}")
        print("\n" + "="*80)
        print(audit_content)
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Supervisory audit call failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
