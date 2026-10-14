#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/legacy_guard.py — Anti-Ghost & Anti-Bypass Guard (Rule 125 & AVF-STAB-001).

Injected into every legacy module in legacy/ to strictly forbid runtime execution or import.
"""

from typing import NoReturn


class LegacyFlowError(RuntimeError):
    """Raised when an isolated legacy module or bypass pipeline is invoked."""
    pass


def forbid_legacy(module_name: str) -> NoReturn:
    """Raises LegacyFlowError to block runtime execution of dead/ghost code."""
    raise LegacyFlowError(
        f"[ANTI-GHOST] Module '{module_name}' thuộc luồng cũ đã bị cô lập. "
        f"Vui lòng sử dụng orchestrator/run_pipeline.py theo kiến trúc chuẩn. "
        f"Xem chi tiết tại docs/PIPELINE_CANONICAL.md"
    )
