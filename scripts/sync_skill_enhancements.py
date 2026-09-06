#!/usr/bin/env python3
"""
sync_skill_enhancements.py -- Reverse-sync gate: code/audit -> Skill AI Notion page.

This is now the ONLY sanctioned path for writing learned rules back into the Skill AI
page (replaces ad-hoc sync_rule118_notion.py / sync_all_sot_notion.py-style one-off
per-episode writes going forward).

Flow:
  1. app/audit/learn.py's run_learn_cycle() already looks at RECURRING issues across
     MANY episodes (min_occurrences over N days) -- never a single EP -- and saves a
     'pending' proposal to skill_enhancements, notifying a human via Telegram.
  2. A human approves the proposal (existing flow: scripts/run-learn.py --queue, then
     app.audit.db.approve_enhancement(id) marks it 'approved').
  3. THIS script picks up every 'approved' (not yet applied) proposal, and asks
     GPT-6-Astra to run one more absolute strict audit pass:
       - Confirm the proposed rule is GENERALIZED (must not mention a specific
         episode_id/task_id/slug) so it scales to future episodes, not just one EP.
       - Confirm it does not conflict with or duplicate an existing Skill AI rule
         (uses a LIVE fetch of the current Skill AI page -- never a cached copy).
       - Produce final, clean rule text ready to append.
  4. Only on GPT-6-Astra PASS does it append the rule to the live Skill AI page and
     mark the enhancement 'applied'. On FAIL it leaves status='approved' for a human
     to revise, and sends a Telegram explanation.

Usage: python3 scripts/sync_skill_enhancements.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.audit import db as audit_db
from app.audit.notifier import send_skill_ai_sync_result
from app.services.hhtech_reasoner import call_gpt56_sol
from scripts.skill_ai_live import load_skill_ai_live, append_skill_ai_rule

STRICT_AUDITOR_SYSTEM = '''Ban la Chief Rule Auditor tuyet doi nghiem ngat cua Video Factory Skill AI.
Nhiem vu: xet duyet MOT de xuat enhancement da duoc con nguoi approve, truoc khi no duoc ghi
vinh vien vao trang Skill AI (nguon quy tac chung cho toan bo pipeline nhieu episode).

Quy tac audit TUYET DOI:
1. TU CHOI (FAIL) neu de xuat gan voi 1 episode_id/task_id/slug cu the, hoac chi giai quyet
   truong hop rieng le -- de xuat PHAI duoc tong quat hoa de ap dung cho MOI episode tuong lai
   (dreaming/scale-up, khong hardcode rieng 1 EP).
2. TU CHOI (FAIL) neu de xuat mau thuan hoac trung lap voi bat ky rule nao dang co trong
   SKILL AI HIEN TAI (cung cap ben duoi, la ban LIVE moi nhat, khong phai ban cache).
3. Neu PASS, hay viet lai de xuat thanh 1 doan rule ngan gon, ro rang, tong quat, dat ten
   theo dung phong cach cac rule hien co (khong tu dat so hieu Rule N -- he thong Notion se
   quan ly thu tu).
4. Tra ve DUY NHAT 1 JSON object hop le, khong markdown fence, dung dinh dang:
{"verdict": "PASS hoac FAIL", "reason": "...", "final_rule_title": "...", "final_rule_body": "..."}'''


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def run_sync():
    approved = audit_db.get_approved_awaiting_sync()
    if not approved:
        print("No approved enhancements awaiting Skill AI sync.")
        return {"synced": 0, "rejected": 0}

    live_skill_digest = load_skill_ai_live(max_chars=16000)
    synced, rejected = 0, 0

    for row in approved:
        enh_id, skill_name, enhancement_type, current_value, proposed_value, rationale, confidence = row

        user_prompt = (
            f"{live_skill_digest}\n\n"
            f"--- DE XUAT ENHANCEMENT CAN AUDIT ---\n"
            f"Skill: {skill_name}\n"
            f"Loai: {enhancement_type}\n"
            f"Gia tri hien tai: {current_value}\n"
            f"De xuat moi: {proposed_value}\n"
            f"Ly do (tu learn cycle, dua tren cac loi lap lai qua nhieu episode): {rationale}\n"
            f"Do tin cay tu pattern-matching: {confidence}"
        )

        try:
            raw = call_gpt56_sol(user_prompt, system_prompt=STRICT_AUDITOR_SYSTEM, max_tokens=800)
            result = _extract_json(raw)
        except Exception as e:
            print(f"[sync_skill_enhancements] GPT-6-Astra audit call failed for {enh_id}: {e}")
            send_skill_ai_sync_result(skill_name, "AUDIT_ERROR", proposed_value[:60], str(e))
            continue

        verdict = result.get("verdict", "FAIL")
        if verdict != "PASS":
            reason = result.get("reason", "Khong ro ly do.")
            print(f"[sync_skill_enhancements] REJECTED {enh_id} ({skill_name}): {reason}")
            send_skill_ai_sync_result(skill_name, "REJECTED", proposed_value[:60], reason)
            rejected += 1
            continue

        title = result.get("final_rule_title") or f"Auto-learned rule ({skill_name})"
        body = result.get("final_rule_body") or proposed_value
        append_skill_ai_rule(title, body)
        audit_db.apply_enhancement(enh_id)
        print(f"[sync_skill_enhancements] APPLIED {enh_id} ({skill_name}) -> Skill AI: {title}")
        send_skill_ai_sync_result(skill_name, "APPLIED", title, body)
        synced += 1

    return {"synced": synced, "rejected": rejected}


if __name__ == "__main__":
    result = run_sync()
    print(f"\nDone. Synced={result['synced']} Rejected={result['rejected']}")
