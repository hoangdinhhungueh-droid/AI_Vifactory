#!/usr/bin/env python3
"""One-time doc sync: append official decision entry for Rule 121 (Skill AI Live
Load + Reverse-Sync governance) onto the LIVE Decision Log Notion page.
Run once manually: python3 scripts/apply_decision_log_skillai_entry.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.ag_notion_bridge import resolve_id, append_children_blocks


def rt(text, bold=False, code=False):
    obj = {"type": "text", "text": {"content": text}}
    ann = {}
    if bold:
        ann["bold"] = True
    if code:
        ann["code"] = True
    if ann:
        obj["annotations"] = ann
    return obj


def heading_2(text):
    return {"type": "heading_2", "heading_2": {"rich_text": [rt(text)]}}


def paragraph(runs):
    return {"type": "paragraph", "paragraph": {"rich_text": runs}}


def bulleted(runs):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": runs}}


def callout(text, emoji="\u26a0\ufe0f"):
    return {
        "type": "callout",
        "callout": {"rich_text": [rt(text)], "icon": {"type": "emoji", "emoji": emoji}},
    }


CHILDREN = [
    heading_2(
        "\U0001F4CC C\u1EACP NH\u1EACT 23/08/2026 (t\u1ED1i): N\u1EA1p Skill AI Live B\u1EAFt Bu\u1ED9c (Rule 121) & C\u1ED5ng Reverse-Sync C\u00F3 Ki\u1EC3m So\u00E1t"
    ),
    paragraph(
        [
            rt(
                "Quy\u1EBFt \u0111\u1ECBnh ch\u1ED1t sau khi audit to\u00E0n b\u1ED9 lu\u1ED3ng B2\u2192B5 v\u00E0 c\u01A1 ch\u1EBF Antigravity: lo\u1EA1i b\u1ECF r\u1EE7i ro LLM/Antigravity t\u1EF1 suy di\u1EC5n khi thi\u1EBFu \u0111\u1ECBnh h\u01B0\u1EDBng t\u1EEB Skill AI. Chi ti\u1EBFt k\u1EF9 thu\u1EADt \u0111\u1EA7y \u0111\u1EE7 n\u1EB1m t\u1EA1i Rule 121 tr\u00EAn trang Skill AI."
            )
        ]
    ),
    bulleted(
        [
            rt("1. N\u1EA1p m\u1EDBi (live) b\u1EAFt bu\u1ED9c t\u1EA1i B2/B3/B3.5/B4: ", bold=True),
            rt(
                "Th\u00EAm scripts/skill_ai_live.py \u2014 m\u1ED7i l\u1EA7n ch\u1EA1y B2 (5-Arc Story), B3 (Director Plan), B3.5 (Prompt Forge) \u0111\u1EC1u live-fetch to\u00E0n b\u1ED9 trang Skill AI t\u1EEB Notion API v\u00E0 prepend v\u00E0o system prompt g\u1ECDi GPT-6-Astra; kh\u00F4ng c\u00F2n \u0111\u1ECDc file cache c\u1EE5c b\u1ED9 hay ch\u1EC9 d\u1EF1a rule vi\u1EBFt c\u1EE9ng trong code. N\u1EBFu fetch l\u1ED7i, script d\u1EEBng h\u1EB3n (RuntimeError) thay v\u00EC t\u1EF1 suy di\u1EC5n."
            ),
        ]
    ),
    bulleted(
        [
            rt("2. C\u1ED5ng Reverse-Sync 3 l\u1EDBp: ", bold=True),
            rt(
                "Th\u00EAm scripts/sync_skill_enhancements.py. Ch\u1EC9 ghi ng\u01B0\u1EE3c v\u00E0o Skill AI khi: (a) \u0111\u1EC1 xu\u1EA5t \u0111\u1EBFn t\u1EEB chu k\u1EF3 h\u1ECDc t\u1ED5ng qu\u00E1t h\u00F3a app/audit/learn.py (l\u1ED7i l\u1EB7p l\u1EA1i qua nhi\u1EC1u episode, kh\u00F4ng ph\u1EE5c v\u1EE5 ri\u00EAng 1 EP), (b) con ng\u01B0\u1EDDi \u0111\u00E3 approve, (c) GPT-6-Astra th\u1EF1c hi\u1EC7n audit tuy\u1EC7t \u0111\u1ED1i nghi\u00EAm ng\u1EB7t x\u00E1c nh\u1EADn \u0111\u1EC1 xu\u1EA5t \u0111\u00E3 t\u1ED5ng qu\u00E1t h\u00F3a \u0111\u00FAng c\u00E1ch v\u00E0 kh\u00F4ng xung \u0111\u1ED9t rule hi\u1EC7n c\u00F3."
            ),
        ]
    ),
    bulleted(
        [
            rt("3. Rule 121 \u0111\u00E3 ghi tr\u1EF1c ti\u1EBFp v\u00E0o Skill AI: ", bold=True),
            rt(
                "B\u1EAFt bu\u1ED9c n\u1EA1p live tr\u01B0\u1EDBc khi th\u1EF1c thi B2-B4, c\u1EA5m suy di\u1EC5n khi kh\u00F4ng fetch \u0111\u01B0\u1EE3c, v\u00E0 gi\u1EDBi h\u1EA1n reverse-sync ch\u1EC9 qua sync_skill_enhancements.py \u2014 c\u00E1c script \u0111\u1ED3ng b\u1ED9 m\u1ED9t chi\u1EC1u c\u0169 (sync_rule118_notion.py, sync_all_sot_notion.py) kh\u00F4ng c\u00F2n \u0111\u01B0\u1EE3c d\u00F9ng \u0111\u1EC3 c\u1EADp nh\u1EADt Skill AI k\u1EC3 t\u1EEB nay."
            ),
        ]
    ),
    callout(
        "\u0110\u00E1nh \u0111\u1ED5i c\u00F3 ch\u1EE7 \u0111\u00EDch: n\u1EBFu Notion API l\u1ED7i/token h\u1EBFt h\u1EA1n, B2/B3/B3.5 s\u1EBD D\u1EEANG H\u1EA8N thay v\u00EC t\u1EF1 ch\u1EA1y ti\u1EBFp b\u1EB1ng rule c\u0169 vi\u1EBFt c\u1EE9ng trong code \u2014 \u0111\u00FAng theo y\u00EAu c\u1EA7u \"kh\u00F4ng \u0111\u01B0\u1EE3c t\u1EF1 suy di\u1EC5n\" c\u1EE7a user."
    ),
    paragraph(
        [
            rt("File \u0111\u00E3 s\u1EEDa/t\u1EA1o: "),
            rt(
                "scripts/skill_ai_live.py (moi), scripts/produce_episode_hg1.py, app/services/prompt_forge.py, app/audit/db.py, app/audit/notifier.py, scripts/sync_skill_enhancements.py (moi), scripts/apply_rule121_skill_ai.py (moi, one-off seed)",
                code=True,
            ),
            rt(
                ". Da py_compile toan bo 7 file (COMPILE_OK) + chay thu skill_ai_live.py live: fetch thanh cong 215.700 ky tu tu Skill AI, xac nhan co Rule 121. Rule 121 da duoc append truc tiep vao trang Skill AI goc qua Notion API."
            ),
        ]
    ),
]

if __name__ == "__main__":
    result = append_children_blocks(resolve_id("decision_log"), CHILDREN)
    print(result)
