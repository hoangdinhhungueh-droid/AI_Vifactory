#!/usr/bin/env python3
"""One-time doc sync: append the Rule 121 (Skill AI live-load gate + reverse-sync
loop) process update and diagram onto the LIVE Architecture Notion page.
Run once manually: python3 scripts/apply_architecture_skillai_update.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.ag_notion_bridge import append_children_blocks

ARCH_PAGE_ID = "3c301989-2400-815c-b22f-f4ced65469bf"


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


def code_block(text, language="mermaid"):
    return {"type": "code", "code": {"rich_text": [rt(text)], "language": language}}


MERMAID = """graph TD
    classDef notion fill:#EFEFEF,stroke:#333
    classDef vps fill:#D4E6F1,stroke:#2874A6
    classDef agy fill:#D5F5E3,stroke:#229954
    classDef hum fill:#FAD7A1,stroke:#D68910
    classDef gate fill:#F5B7B1,stroke:#C0392B

    SkillAI[(Skill AI Page - Notion)]:::notion

    subgraph Forward [Nap Skill AI Live truoc khi sinh - Rule 121]
        LoadGate{Live Fetch Skill AI}:::gate
        B2n[B2: 5-Arc Story]:::vps
        B3n[B3: Director Plan]:::vps
        B35n[B3.5: Prompt Forge]:::agy
        B4n[B4: Antigravity Image Gen]:::agy
    end

    SkillAI -->|GET live, khong cache| LoadGate
    LoadGate -->|OK: prepend context vao system prompt| B2n --> B3n --> B35n --> B4n
    LoadGate -.->|FAIL: fetch loi| StopNode[[\"DUNG lai + bao loi ro rang, khong tu suy dien\"]]

    subgraph Reverse [Reverse-Sync co kiem soat]
        LearnN[app/audit/learn.py: Loi LAP LAI qua nhieu episode]:::vps
        ApproveN{Human Approve}:::hum
        AuditN{GPT-6-Astra Chief Rule Auditor - audit tuyet doi nghiem ngat}:::gate
        SyncN[sync_skill_enhancements.py]:::vps
    end

    LearnN --> ApproveN -->|approved| AuditN
    AuditN -->|PASS: da tong quat hoa, khong xung dot| SyncN --> SkillAI
    AuditN -.->|FAIL: con hardcode 1 EP hoac xung dot| RejectedN[[\"Giu status approved, bao Telegram FAIL\"]]
"""

CHILDREN = [
    heading_2(
        "\U0001F4CC C\u1EACP NH\u1EACT 23/08/2026 (t\u1ED1i): C\u1ED5ng N\u1EA1p Skill AI Live B\u1EAFt Bu\u1ED9c Tr\u01B0\u1EDBc B2-B4 (Rule 121) & V\u00F2ng Reverse-Sync"
    ),
    paragraph(
        [
            rt(
                "B\u1ED5 sung l\u01B0u \u0111\u1ED3 Rule 121: m\u1ECDi b\u01B0\u1EDBc B2 (5-Arc Story), B3 (Director Plan), B3.5 (Prompt Forge), B4 (Antigravity sinh \u1EA3nh) \u0111\u1EC1u \u0111i qua m\u1ED9t c\u1ED5ng b\u1EAFt bu\u1ED9c live-fetch to\u00E0n b\u1ED9 trang Skill AI tr\u01B0\u1EDBc khi sinh n\u1ED9i dung; n\u1EBFu fetch l\u1ED7i, pipeline d\u1EEBng l\u1EA1i v\u00E0 b\u00E1o l\u1ED7i thay v\u00EC t\u1EF1 suy di\u1EC5n. Chi\u1EC1u ng\u01B0\u1EE3c l\u1EA1i (ghi rule m\u1EDBi v\u00E0o Skill AI) ch\u1EC9 \u0111i qua c\u1ED5ng audit GPT-6-Astra tuy\u1EC7t \u0111\u1ED1i nghi\u00EAm ng\u1EB7t, xu\u1EA5t ph\u00E1t t\u1EEB chu k\u1EF3 h\u1ECDc t\u1ED5ng qu\u00E1t h\u00F3a (nhi\u1EC1u episode), kh\u00F4ng ph\u1EE5c v\u1EE5 ri\u00EAng 1 EP."
            )
        ]
    ),
    code_block(MERMAID, "mermaid"),
    paragraph(
        [
            rt("Chi ti\u1EBFt quy t\u1EAFc: xem Rule 121 tr\u00EAn trang "),
            rt("Skill AI", code=True),
            rt(" v\u00E0 "),
            rt("scripts/sync_skill_enhancements.py", code=True),
            rt("."),
        ]
    ),
]

if __name__ == "__main__":
    result = append_children_blocks(ARCH_PAGE_ID, CHILDREN)
    print(result)
