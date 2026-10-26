#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/market_resolver.py — Canonical Single Source of Truth Market Resolver (Rule 128, Rule 134).

Governed by Rule 128 (Generic Contract Architecture) and Rule 134 (Exact Parity & Single Truth).
Resolves strictly from manifest or config. Fails closed (raises ValueError) if missing or invalid.
Enforces canonical market set: {"EN", "JA", "KR", "VN"}.
"""

from __future__ import annotations

from typing import Any, Optional, Set

CANONICAL_MARKETS: Set[str] = {"EN", "JA", "KR", "VN"}

_CANONICAL_MARKET_ALIASES: dict[str, str] = {
    "EN": "EN",
    "ENGLISH": "EN",
    "US": "EN",
    "JA": "JA",
    "JP": "JA",
    "JAPAN": "JA",
    "JAPANESE": "JA",
    "KR": "KR",
    "KO": "KR",
    "KOREA": "KR",
    "KOREAN": "KR",
    "VN": "VN",
    "VI": "VN",
    "VIETNAM": "VN",
    "VIETNAMESE": "VN",
}


def resolve_canonical_market(
    ctx: Optional[Any] = None,
    market_raw: Optional[str] = None
) -> str:
    """Strictly resolves canonical market ('EN', 'JA', 'KR', 'VN') from manifest or config.

    Fail-closed (Rule 118, 128, 134):
    1. If market_raw is provided explicitly, validate and normalize it.
    2. Otherwise, check ctx.manifest.market (or ctx.manifest dict).
    3. If still absent, check ctx.config.market (or ctx.config dict).
    4. If absent in both, raise ValueError (no run_id heuristics, no silent default).
    5. Normalizes aliases (JP -> JA, KO -> KR, VI -> VN) to canonical {"EN", "JA", "KR", "VN"}.
    """
    candidate: Optional[str] = market_raw

    if not candidate and ctx is not None:
        # 1. Check ctx.manifest
        manifest = getattr(ctx, "manifest", None)
        if manifest is not None:
            candidate = getattr(manifest, "market", None)
            if not candidate and isinstance(manifest, dict):
                candidate = manifest.get("market")

        # 2. Check ctx.config
        if not candidate:
            config = getattr(ctx, "config", None)
            if config is not None:
                candidate = getattr(config, "market", None)
                if not candidate and isinstance(config, dict):
                    candidate = config.get("market")

    if not candidate or not str(candidate).strip():
        raise ValueError(
            "Market resolution failed closed (Rule 118, 128, 134): "
            "No market specified in manifest or config. "
            "Silent defaults and run_id substring heuristics are strictly forbidden."
        )

    norm = str(candidate).strip().upper()
    resolved = _CANONICAL_MARKET_ALIASES.get(norm, norm)

    if resolved not in CANONICAL_MARKETS:
        raise ValueError(
            f"Invalid market '{candidate}' (normalized: '{resolved}'). "
            f"Must be one of canonical set: {sorted(CANONICAL_MARKETS)} (Rule 134)."
        )

    return resolved
