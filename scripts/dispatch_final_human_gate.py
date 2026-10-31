#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/dispatch_final_human_gate.py
Dispatches the final human gate notification and interactive review card to Telegram.
"""

import sys
import asyncio
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.vox_telegram_gates import send_gate_sync
from app.services.telegram_buttons import send_gate3_card

def main():
    episode_id = "JP_EP0006_crypto_exchange_heist"
    print(f"Dispatching Human Gate 4 for {episode_id}...")
    res_hg4 = send_gate_sync(4, episode_id, video_count=145, runtime_s=593.8)
    print(f"Human Gate 4 dispatched: {res_hg4}")

    title_a = "コインチェック580億円流出事件の真実：史上最大のハッキングはいかにして起きたか"
    title_b = "暗号資産580億円が一瞬で消えた日：NEM流出の全記録と追跡の結末"
    duration_str = "09:53"

    print(f"Dispatching Interactive Human Gate Card (Gate 3) for {episode_id}...")
    try:
        msg_id = asyncio.run(send_gate3_card(
            episode_id=episode_id,
            video_id="final_master_render",
            title_a=title_a,
            title_b=title_b,
            duration_str=duration_str,
            market="JA"
        ))
        print(f"Interactive Gate Card Message ID: {msg_id}")
    except Exception as e:
        print(f"Interactive Gate Card notice: {e}")

if __name__ == "__main__":
    main()
