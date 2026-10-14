#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/export_schema.py — Export Pydantic Schemas to JSON Schema for Remotion (AVF-STAB-001).

Guarantees single source of truth between Python and TypeScript.
Run with --check to verify parity in CI.
"""

import sys
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.contracts.render_props import RemotionRenderProps


def export_remotion_schema(check_only: bool = False) -> int:
    target_dir = ROOT_DIR / "remotion" / "src" / "generated"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "render-props.schema.json"

    # Generate JSON schema from Pydantic model
    schema_dict = RemotionRenderProps.model_json_schema()
    new_schema_str = json.dumps(schema_dict, indent=2, ensure_ascii=False) + "\n"

    if check_only:
        if not target_file.exists():
            print(f"[-] Schema check failed: {target_file} does not exist.")
            return 1
        existing_str = target_file.read_text(encoding="utf-8")
        if existing_str.strip() != new_schema_str.strip():
            print(f"[-] Schema drift detected between Pydantic RemotionRenderProps and {target_file}.")
            return 1
        print("[+] Remotion schema parity verified (Zero Drift).")
        return 0

    target_file.write_text(new_schema_str, encoding="utf-8")
    print(f"[+] Successfully exported Remotion JSON Schema to: {target_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Export Remotion Render Props Schema")
    parser.add_argument("--check", action="store_true", help="Check parity without overwriting")
    args = parser.parse_args()

    sys.exit(export_remotion_schema(check_only=args.check))


if __name__ == "__main__":
    main()
