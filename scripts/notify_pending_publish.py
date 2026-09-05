#!/usr/bin/env python3
"""CLI: gui 1 tin nhan Telegram liet ke TAT CA video dang cho public (private/
unlisted), moi video kem 1 nut "Cong khai (Public)" rieng + 1 nut
"PUBLIC ALL" o cuoi de cong khai het trong 1 lan bam.

Xay 07/08/2026 theo yeu cau Hand-off Moc 3.2 ("giu 1 cham tay nhu hien tai,
nhung them thong bao list cac video chua public, moi video 1 nut public va
co nut public all"). KHONG thay the scripts/send_publish_button.py (van dung
tot cho 1 video ngay sau khi upload) -- script nay la lop bo sung, doc tu
app/services/publish_ledger.py (ledger duoc tu dong ghi boi
youtube_upload.upload_from_payload() moi lan upload thanh cong o che do
private/unlisted).

Tai su dung dung co che approval-loop DA CO SAN va DANG CHAY that tren VPS:
  - app/services/telegram_buttons.py  (send_with_buttons: gui inline keyboard)
  - app/services/telegram_actions.py  ("pub:<videoId>" cong khai 1 video;
    "puball" cong khai TAT CA video con pending trong ledger)
  - app/services/telegram_poller.py   (background poller, da chay trong pm2
    vf-api, tu dong route callback_query toi dispatch())

Script nay CHI la trigger doc-va-gui: khong tu dong public gi ca, nguoi dung
phai bam nut tren Telegram.

Usage:
  python3 scripts/notify_pending_publish.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_env(path="/root/secrets/.env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                os.environ[k] = v


_load_env()

from app.services import telegram_buttons as tb  # noqa: E402
from app.services import publish_ledger  # noqa: E402


async def main():
    pending = publish_ledger.load_pending()
    if not pending:
        print("OK: khong co video nao dang cho public.")
        return
    if not tb.is_enabled():
        print("DISABLED: thieu VF_TG_BOT_TOKEN hoac TELEGRAM_CHAT_ID", file=sys.stderr)
        sys.exit(1)
    lines = ["\U0001F4CB <b>Video dang cho public (%d)</b>" % len(pending)]
    rows = []
    for rec in pending:
        vid = rec.get("video_id", "")
        title = rec.get("title") or vid
        lines.append("\u2022 " + title + "\nhttps://youtu.be/" + vid)
        rows.append([
            ("\U0001F680 Public: " + title[:40], "pub:" + vid),
            ("\U0001F512 Giu Private", "kp:" + vid),
        ])
    rows.append([("\U0001F680 PUBLIC ALL (%d video)" % len(pending), "puball")])
    text = "\n\n".join(lines)
    msg_id = await tb.send_with_buttons(text, rows)
    if msg_id:
        print("OK message_id=" + str(msg_id) + " pending_count=" + str(len(pending)))
    else:
        print("FAILED: send_with_buttons tra ve None (kiem tra token/chat_id)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
