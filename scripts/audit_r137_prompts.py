#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit generated prompts against Rule 137 strict constraints."""

import json
import re
import sys
from pathlib import Path

def audit_file(path_str):
    p = Path(path_str)
    if not p.exists():
        print(f"File not found: {path_str}")
        return
    
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    bgs = data.get("backgrounds", {})
    fgs = data.get("foregrounds", {})
    print(f"\n==================================================")
    print(f"AUDITING: {p.name} ({len(bgs)} BGs, {len(fgs)} FGs)")
    print(f"==================================================")
    
    clean_banned = [
        r"\$[0-9]",
        r"[0-9]+\s*(?:원|won|KRW|₩)",
        r"[0-9]+[조억만백천]",
        r"[0-9]+\s*(?:billion|trillion|million|USD)",
        r"[0-9]+\s*%",
    ]
    
    violations = []
    for k, text in {**bgs, **fgs}.items():
        for pat in clean_banned:
            m = re.findall(pat, text, re.IGNORECASE)
            if m:
                violations.append((k, pat, m))
                
    if violations:
        print(f"❌ RULE 137 VIOLATIONS DETECTED: {len(violations)}")
        for v in violations[:10]:
            print(f"   Asset: {v[0]} | Pattern: {v[1]} | Found: {v[2]}")
    else:
        print("✅ RULE 137 STRICT AUDIT PASSED: 0% numbers/currencies in prompts!")
        
    # Check blank document template conformance
    doc_matches = 0
    blank_matches = 0
    doc_keywords = ["document", "contract", "filing", "paper", "form", "sheet", "record", "dossier"]
    for k, text in {**bgs, **fgs}.items():
        if any(dk in text.lower() for dk in doc_keywords):
            doc_matches += 1
            if "unfilled" in text.lower() or "blank" in text.lower() or "clean white" in text.lower():
                blank_matches += 1
                
    print(f"Forensic Document Props: {doc_matches} detected, {blank_matches} confirmed blank/unfilled.")
    
    # Print sample
    if bgs:
        sample_k = list(bgs.keys())[0]
        print(f"\n[Sample BG - {sample_k}]:\n{bgs[sample_k][:220]}...")
    if fgs:
        sample_k = list(fgs.keys())[0]
        print(f"\n[Sample FG - {sample_k}]:\n{fgs[sample_k][:220]}...")

if __name__ == "__main__":
    for target in sys.argv[1:]:
        audit_file(target)
