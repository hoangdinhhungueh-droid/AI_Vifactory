#!/usr/bin/env python3
"""
skill_ai_live.py -- Rule 121 (Mandatory Fresh Skill Load Before Execution)

ALWAYS fetches the Skill AI Notion page LIVE at call time via the Notion API.
Never reads a cached or pre-dumped local file (unlike ag_notion_bridge.read_skill_rule(),
which reads a static data/notion_audit/skill_ai.md snapshot that can go stale).

Used by:
  - scripts/produce_b1_b2_b3_gpt56_sol.py  (B2 story acts + B3 director plan)
  - app/services/prompt_forge.py           (B3.5 prompt forge)
  - scripts/sync_skill_enhancements.py     (reverse-sync GPT-5.6-Sol strict-audit gate)

Any script that calls GPT-5.6-Sol to generate story/director/prompt content MUST call
load_skill_ai_live() once per run and prepend its output to the system prompt. Do NOT
cache the result across runs/episodes -- fetch fresh every single execution.

On fetch failure this raises instead of silently falling back to hardcoded rules --
the pipeline must stop and surface the error rather than let the LLM infer on its own.
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ag_notion_bridge import get_blocks, append_children_blocks

logger = logging.getLogger("skill_ai_live")

SKILL_AI_KEY = "skill_ai"


def load_skill_ai_live(max_chars: int = 20000) -> str:
    """Fetch the LIVE Skill AI page fresh from Notion (no local cache/file).
    Returns a compact plain-text digest (headings + rule bullets) ready to prepend
    to any GPT-5.6-Sol system prompt.

    If the digest is larger than max_chars, keep BOTH the head (foundational rules,
    e.g. Rule 1 Zero-Mock-Data) AND the tail (most recently appended rules, e.g. new
    learn-cycle rules or Rule 121 itself) instead of truncating from the end only --
    otherwise newly-appended governance rules would silently disappear from every
    future run as the page keeps growing.

    Raises RuntimeError on any fetch failure or empty page -- callers must NOT
    silently fall back to hardcoded rules on failure.
    """
    res = get_blocks(SKILL_AI_KEY)
    if isinstance(res, dict) and res.get("error"):
        raise RuntimeError(
            f"[skill_ai_live] LIVE fetch of Skill AI page failed: {res}. "
            f"Refusing to proceed with a stale/hardcoded rule set."
        )

    lines = []
    for b in res.get("results", []):
        btype = b.get("type")
        block = b.get(btype, {}) if btype else {}
        rich = block.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich).strip()
        if not text:
            continue
        if btype in ("heading_1", "heading_2", "heading_3"):
            lines.append(f"\n## {text}")
        elif btype in ("bulleted_list_item", "numbered_list_item", "to_do"):
            lines.append(f"- {text}")
        else:
            lines.append(text)

    digest = "\n".join(lines).strip()
    if not digest:
        raise RuntimeError(
            "[skill_ai_live] Skill AI page returned 0 usable text blocks. "
            "Refusing to run without live skill context."
        )

    if len(digest) <= max_chars:
        body = digest
        truncated = False
    else:
        head_budget = int(max_chars * 0.6)
        tail_budget = max_chars - head_budget
        body = (
            digest[:head_budget]
            + "\n\n...[middle of Skill AI page omitted for length -- see full page in Notion for complete rule set]...\n\n"
            + digest[-tail_budget:]
        )
        truncated = True

    header = "=== SKILL AI (LIVE -- fetched fresh from Notion this run, do NOT rely on any cached/hardcoded copy) ===\n"
    footer = "\n=== END SKILL AI -- you MUST follow every applicable rule above exactly; do not infer, guess, or deviate ===\n"
    logger.info(f"[skill_ai_live] Loaded {len(digest)} chars live from Skill AI page (truncated={truncated}).")
    return header + body + footer


def append_skill_ai_rule(title: str, body_text: str):
    """Reverse-sync write: append ONE new generalized rule block to the LIVE Skill AI
    page. Intended to be called ONLY from scripts/sync_skill_enhancements.py (after a
    GPT-5.6-Sol strict audit confirms the rule is generalized -- not tied to a single
    episode -- and does not conflict with existing rules), or from the one-off
    scripts/bootstrap_rule121.py governance bootstrap. Never call this directly from
    per-episode pipeline scripts.
    """
    children = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": title}}]},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": body_text}}]},
        },
    ]
    return append_children_blocks(SKILL_AI_KEY, children)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(load_skill_ai_live())
