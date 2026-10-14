#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/codemap/approval.py — Forensic Approval Freezing and Audit Tracker.

Freezes approved user/agent decisions with bit-for-bit SHA256 hashes and field maps.
"""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Union

from tools.codemap.hashing import field_hashes, redact, sha256_of
from tools.codemap.schema import Approval


def record_approval(
    run_id: str,
    target_stage: str,
    payload: Any,
    actor: Literal["user", "agent"] = "user",
    channel: str = "chat",
    repo_root: Optional[Path] = None,
) -> Approval:
    """Freezes an approval decision to disk and returns the Approval object."""
    root = (repo_root or Path.cwd()).resolve()
    run_dir = root / ".codemap" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = run_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    approval_id = f"appr_{uuid.uuid4().hex[:12]}"
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    p_hash = sha256_of(payload)
    f_hashes = field_hashes(payload)

    # Save redacted snapshot
    snapshot_file = snapshot_dir / f"{approval_id}.approved.json"
    snapshot_file.write_text(
        json.dumps(redact(payload), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    rel_snapshot = snapshot_file.relative_to(root).as_posix()

    approval = Approval(
        approval_id=approval_id,
        run_id=run_id,
        target_stage=target_stage,
        actor=actor,
        channel=channel,
        ts=ts,
        payload_hash=p_hash,
        field_hashes=f_hashes,
        payload_snapshot=rel_snapshot,
    )

    # Append to approvals.jsonl
    approvals_file = run_dir / "approvals.jsonl"
    with open(approvals_file, "a", encoding="utf-8") as f:
        f.write(approval.model_dump_json() + "\n")
        f.flush()

    return approval
