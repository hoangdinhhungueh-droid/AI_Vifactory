#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core/market_resolver.py — Canonical Single Source of Truth Market Resolver (Rule 128, Rule 134).

Governed by Rule 128 (Generic Contract Architecture) and Rule 134 (Exact Parity & Single Truth).
Resolves strictly from manifest or config. Fails closed (raises ValueError) if missing or invalid.
Enforces canonical market set: {"EN", "JA", "KR", "VN"}.
"""

from __future__ import annotations

from typing import Any, Optional, Set, Union

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
    market_raw: Optional[Union[str, Any]] = None,
    *,
    ctx: Optional[Any] = None
) -> str:
    """Strictly resolves canonical market ('EN', 'JA', 'KR', 'VN') from manifest or config.

    Fail-closed (Rule 118, 128, 134):
    1. If market_raw is provided explicitly as str, validate and normalize it.
    2. If first arg is a context (has manifest/config), use it as ctx.
    3. Check ctx.manifest.market (or ctx.manifest dict).
    4. If still absent, check ctx.config.market (or ctx.config dict).
    5. If absent in both, raise ValueError (no run_id heuristics, no silent default).
    6. Normalizes aliases (JP -> JA, KO -> KR, VI -> VN) to canonical {"EN", "JA", "KR", "VN"}.
    """
    effective_ctx = ctx
    candidate: Optional[str] = None

    if market_raw is not None:
        if hasattr(market_raw, "manifest") or hasattr(market_raw, "config"):
            effective_ctx = market_raw
        elif isinstance(market_raw, str):
            candidate = market_raw

    if not candidate and effective_ctx is not None:
        # 1. Check ctx.manifest
        manifest = getattr(effective_ctx, "manifest", None)
        if manifest is not None:
            candidate = getattr(manifest, "market", None)
            if not candidate and isinstance(manifest, dict):
                candidate = manifest.get("market")

        # 2. Check ctx.config
        if not candidate:
            config = getattr(effective_ctx, "config", None)
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
