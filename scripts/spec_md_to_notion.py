#!/usr/bin/env python3
"""One-shot: convert a Markdown SPEC file to Notion blocks and create a sibling page.
Usage: python3 spec_md_to_notion.py <parent_page_id> <md_path> "<title>"
Read-only w.r.t. code; writes ONLY to Notion via ag_notion_bridge helpers."""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ag_notion_bridge as B

MAXRT = 1900  # keep under Notion 2000 char rich_text cap

def _rt(text):
    """Parse a line into Notion rich_text with **bold**, `code`, [t](url)."""
    out = []
    # token pattern: bold, code, link, plain
    pat = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))')
    pos = 0
    for m in pat.finditer(text):
        if m.start() > pos:
            out.append(("plain", text[pos:m.start()]))
        tok = m.group(0)
        if tok.startswith("**"):
            out.append(("bold", tok[2:-2]))
        elif tok.startswith("`"):
            out.append(("code", tok[1:-1]))
        else:
            lm = re.match(r'\[([^\]]+)\]\(([^)]+)\)', tok)
            out.append(("link", (lm.group(1), lm.group(2))))
        pos = m.end()
    if pos < len(text):
        out.append(("plain", text[pos:]))
    rich = []
    for kind, val in out:
        if kind == "link":
            content, url = val
            rich.append({"type": "text", "text": {"content": content[:MAXRT], "link": {"url": url}}})
        else:
            ann = {}
            if kind == "bold":
                ann = {"bold": True}
            elif kind == "code":
                ann = {"code": True}
            s = val
            while s:
                chunk = s[:MAXRT]
                s = s[MAXRT:]
                obj = {"type": "text", "text": {"content": chunk}}
                if ann:
                    obj["annotations"] = ann
                rich.append(obj)
    if not rich:
        rich = [{"type": "text", "text": {"content": ""}}]
    return rich

def _para(text):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rt(text)}}

def _heading(level, text):
    key = {1: "heading_1", 2: "heading_2", 3: "heading_3"}[min(level, 3)]
    return {"object": "block", "type": key, key: {"rich_text": _rt(text)}}

def _bullet(text):
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _rt(text)}}

def _numbered(text):
    return {"object": "block", "type": "numbered_list_item", "numbered_list_item": {"rich_text": _rt(text)}}

def _quote(text):
    return {"object": "block", "type": "quote", "quote": {"rich_text": _rt(text)}}

def _divider():
    return {"object": "block", "type": "divider", "divider": {}}

def _code(text, lang="plain text"):
    return {"object": "block", "type": "code", "code": {"rich_text": [{"type": "text", "text": {"content": text[:MAXRT]}}], "language": lang}}

def _table(rows):
    # rows: list of list[str]; first row is header
    width = max(len(r) for r in rows)
    children = []
    for r in rows:
        cells = []
        for i in range(width):
            cell = r[i] if i < len(r) else ""
            cells.append(_rt(cell.strip()))
        children.append({"object": "block", "type": "table_row", "table_row": {"cells": cells}})
    return {"object": "block", "type": "table",
            "table": {"table_width": width, "has_column_header": True, "has_row_header": False, "children": children}}

def parse(md):
    lines = md.split("\n")
    blocks = []
    i = 0
    saw_title = False
    while i < len(lines):
        line = lines[i]
        s = line.rstrip()
        # fenced code
        if s.startswith("```"):
            lang = s[3:].strip() or "plain text"
            buf = []
            i += 1
            while i < len(lines) and not lines[i].rstrip().startswith("```"):
                buf.append(lines[i]); i += 1
            blocks.append(_code("\n".join(buf), lang if lang else "plain text"))
            i += 1
            continue
        # table
        if s.lstrip().startswith("|"):
            tbl = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                row = lines[i].strip().strip("|")
                cols = [c.strip() for c in row.split("|")]
                if not re.match(r'^[\s:\-]+$', "".join(cols).replace("-", "-")) or not set("".join(cols)) <= set("-: "):
                    tbl.append(cols)
                i += 1
            # drop separator rows (all dashes/colons)
            tbl = [r for r in tbl if not (r and set("".join(r)) <= set("-: "))]
            if tbl:
                blocks.append(_table(tbl))
            continue
        if not s.strip():
            i += 1; continue
        if s.startswith("#"):
            m = re.match(r'^(#+)\s+(.*)$', s)
            level = len(m.group(1)); txt = m.group(2)
            if level == 1 and not saw_title:
                saw_title = True; i += 1; continue  # page title handled separately
            blocks.append(_heading(level - 1 if level > 1 else 1, txt))
            i += 1; continue
        if s.strip() == "---":
            blocks.append(_divider()); i += 1; continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip()); i += 1
            blocks.append(_quote(" ".join(buf))); continue
        mnum = re.match(r'^\s*\d+\.\s+(.*)$', s)
        if mnum:
            blocks.append(_numbered(mnum.group(1))); i += 1; continue
        mbul = re.match(r'^\s*[-*]\s+(.*)$', s)
        if mbul:
            blocks.append(_bullet(mbul.group(1))); i += 1; continue
        blocks.append(_para(s.strip())); i += 1
    return blocks

def main():
    parent = sys.argv[1]; md_path = sys.argv[2]; title = sys.argv[3]
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    blocks = parse(md)
    page = B._req("POST", "pages", {
        "parent": {"page_id": parent},
        "icon": {"type": "emoji", "emoji": "🔬"},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
    })
    pid = page["id"]
    print("PAGE_ID", pid)
    print("PAGE_URL", page.get("url"))
    for b in range(0, len(blocks), 90):
        batch = blocks[b:b+90]
        B._req("PATCH", f"blocks/{pid}/children", {"children": batch})
        print("appended", b, "-", b+len(batch))
    print("DONE total_blocks", len(blocks))

if __name__ == "__main__":
    main()
