#!/usr/bin/env python3
"""scripts/dispatch_final_human_gate.py — DEPRECATED (Rule 125 & Rule 119 Violation Guard).

Prohibits dispatching fake/unverified Human Gate 3 cards without actual YouTube upload.
Redirects callers strictly to canonical: scripts/execute_b10_auto_seo_upload_gate2.py
"""


def main():
    raise RuntimeError(
        "[Rule 125/119 Violation] dispatch_final_human_gate.py is prohibited. "
        "Dispatching HG3 cards with hardcoded or synthetic video IDs (e.g. 'final_master_render') "
        "violates Rule 118 (Zero-Mock Data) and Rule 121 (Strict Verification). "
        "Use canonical entrypoint on Hetzner VPS: "
        "python scripts/execute_b10_auto_seo_upload_gate2.py --episode <EPISODE_ID> --market <MARKET>"
    )

if __name__ == "__main__":
    main()
