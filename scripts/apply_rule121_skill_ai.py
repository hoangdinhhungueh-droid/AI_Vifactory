#!/usr/bin/env python3
"""One-time governance seed: append the Rule 121 block onto the LIVE Skill AI
Notion page. Run once manually: `python3 scripts/apply_rule121_skill_ai.py`.

This is the concrete rule text that makes the entire pipeline (B2/B3/B3.5, and any
Antigravity-driven step such as B4 image generation) mandatory-load Skill AI live
before acting, and defines the only sanctioned reverse-sync path back into this page.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.skill_ai_live import append_skill_ai_rule

RULE_TITLE = "Rule 121 - Mandatory Fresh Skill Load Before Execution (23/08/2026)"
RULE_BODY = (
    "Truoc khi thuc hien B2 (5-Arc Story), B3 (Director Plan), B3.5 (Prompt Forge), "
    "hoac B4 (sinh anh trong Antigravity qua Google Image Native Forge), MOI agent/session "
    "(bao gom Antigravity, GPT-6-Astra goi qua HHTech, va moi script VPS lien quan) BAT BUOC phai "
    "nap MOI (live fetch truc tiep tu Notion API, KHONG dung file cache/dump/hardcode) toan bo "
    "noi dung trang Skill AI nay truoc khi sinh noi dung. Nghiem cam tu suy dien hoac suy doan "
    "khong co can cu tu trang Skill AI. Neu khong the fetch duoc Skill AI live thi phai DUNG lai "
    "va bao loi ro rang, khong duoc tiep tuc bang gia dinh rieng.\n\n"
    "Viec cap nhat nguoc (reverse-sync) tu code/audit vao trang Skill AI nay CHI duoc thuc hien "
    "qua scripts/sync_skill_enhancements.py, va chi khi: (1) mot de xuat enhancement da duoc "
    "chu ky hoc tap tong quat hoa app/audit/learn.py sinh ra tu cac loi LAP LAI qua nhieu episode "
    "(khong hardcode rieng cho 1 EP don le - phai dreaming/scale-up), (2) con nguoi da approve de "
    "xuat do, va (3) GPT-6-Astra thuc hien mot audit tuyet doi nghiem ngat xac nhan rule de xuat "
    "da duoc tong quat hoa dung cach va khong xung dot voi cac rule hien co, truoc khi duoc ghi "
    "vao trang nay. Cac script dong bo mot chieu, rieng le cho tung EP (kieu sync_rule118_notion.py, "
    "sync_all_sot_notion.py) khong duoc dung de cap nhat Skill AI ke tu ngay ap dung rule nay."
)

if __name__ == "__main__":
    result = append_skill_ai_rule(RULE_TITLE, RULE_BODY)
    print(result)
