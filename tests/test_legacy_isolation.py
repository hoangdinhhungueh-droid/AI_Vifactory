#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_legacy_isolation.py — Unit test for Anti-Ghost Isolation (Rule 125 & AVF-STAB-001)."""

import pytest
from core.legacy_guard import LegacyFlowError, forbid_legacy
from tools.ghost_scan import main as run_ghost_scan, scan_canonical_imports, scan_ghost_files


def test_forbid_legacy_raises():
    """Direct invocation of forbid_legacy must raise LegacyFlowError."""
    with pytest.raises(LegacyFlowError) as exc_info:
        forbid_legacy("test_module")
    assert "[ANTI-GHOST]" in str(exc_info.value)
    assert "test_module" in str(exc_info.value)


def test_ghost_scanner_clean():
    """Ghost scanner must report 0 violations in active codebase."""
    import_errors = scan_canonical_imports()
    ghost_errors = scan_ghost_files()
    assert len(import_errors) == 0, f"Prohibited imports found: {import_errors}"
    assert len(ghost_errors) == 0, f"Ghost files found: {ghost_errors}"
    assert run_ghost_scan() == 0


def test_import_legacy_module_blocked():
    """Legacy package is completely removed from active repo (Rule 125)."""
    with pytest.raises((LegacyFlowError, ModuleNotFoundError)):
        import legacy  # noqa: F401
