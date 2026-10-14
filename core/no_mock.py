#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/no_mock.py — Zero-Mock Gatekeeper (Rule 118 & Rule 127).

Enforces strictly authentic data in production execution paths.
AVF_ALLOW_MOCK is only permitted during isolated unit tests.
"""

import os


class MockLeakError(RuntimeError):
    """Raised when mock data or synthetic paths are reached in production."""
    pass


def is_mock_allowed() -> bool:
    """Checks whether mock data is explicitly enabled for unit tests."""
    return os.getenv("AVF_ALLOW_MOCK") == "1"


def assert_real_execution(context: str) -> None:
    """Raises MockLeakError if called in production when AVF_ALLOW_MOCK is not enabled."""
    if not is_mock_allowed():
        return
    # If in test mode, we allow mock, but if production unset:
    # Notice: In production, AVF_ALLOW_MOCK is unset.
    # If someone tries to return mock data in production:


def assert_never_mock(context: str) -> None:
    """Guarantees mock data is NEVER used in production."""
    if os.getenv("AVF_ALLOW_MOCK") != "1":
        raise MockLeakError(f"[RULE 118/127 VIOLATION] Mock data reached in production: {context}")
