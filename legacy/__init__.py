#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""legacy/ — Isolated Legacy & Deprecated Code Repository (Rule 125 & Rule 137).

All modules moved here are strictly quarantined from the canonical pipeline.
Direct execution or import of any module in this package will trigger LegacyFlowError.
"""

from core.legacy_guard import forbid_legacy

# Block importing the legacy package itself
forbid_legacy(__name__)
