"""
Module: ict_micro_cards.py
Dynamic Micro-Cards Routing for Astra 6 / Claude Opus Gatekeeper and Autonomous Dreaming.
Loads formal criteria from ict_distilled.json and formats compact prompt injections (~150 tokens).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_KNOWLEDGE_DIR = Path(__file__).resolve().parent
_JSON_PATH = _KNOWLEDGE_DIR / "ict_distilled.json"

_CACHE: Optional[Dict[str, Any]] = None


def _load_data() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _JSON_PATH.exists():
        try:
            with open(_JSON_PATH, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
                return _CACHE
        except Exception:
            pass
    # Fallback default
    return {
        "micro_cards": {
            "BASELINE_CONFIRMATION": {
                "model_name": "ICT Dynamic Liquidity Sweep + MSS Confirmation",
                "token_prompt_injection": "FORMAL CRITERIA: Sweep >= 0.25 ATR, Displacement >= 0.85 ATR, FVG >= 0.15 ATR, Runway >= 1.20R.",
            },
            "BREAKER_BLOCK_CONFLUENCE": {
                "model_name": "ICT Breaker Block + FVG Confluence",
                "token_prompt_injection": "FORMAL CRITERIA: Prior swing swept (Turtle soup >= 0.25 ATR), violent displacement broke originating OB, retest touches Breaker with FVG confluence and holds.",
            },
            "INVERSION_FVG": {
                "model_name": "ICT Inversion FVG (IFVG) Polarity Flip",
                "token_prompt_injection": "FORMAL CRITERIA: Prior opposing FVG was violated and closed through by displacement, polarity inverted to support/resistance, retest wicks into IFVG and closes favorably.",
            },
        }
    }


def get_audit_card(setup_name: str, compact: bool = True) -> str:
    """
    Returns formal criteria and invalidation rules for LLM prompt injection
    based on the specific setup model detected by Tier 1.
    - If compact=True (default for Gatekeeper entry audit): Returns concise mathematical criteria & VETO triggers (~200-250 tokens).
    - If compact=False (for Dreaming deep research): Returns full 5-part institutional dossier (~700 tokens).
    """
    data = _load_data()
    cards = data.get("micro_cards", {})

    s_upper = setup_name.upper()
    if "BREAKER" in s_upper:
        card = cards.get("BREAKER_BLOCK_CONFLUENCE", {})
    elif "INVERSION" in s_upper or "IFVG" in s_upper:
        card = cards.get("INVERSION_FVG", {})
    else:
        card = cards.get("BASELINE_CONFIRMATION", {})

    if compact:
        model_name = card.get("model_name", setup_name)
        formal_criteria = card.get("formal_criteria", [])
        invals = card.get("invalidation_rules", [])
        crit_subset = formal_criteria[:4] if formal_criteria else []
        inval_subset = invals[:3] if invals else []
        crit_str = "\n".join([f"  • {c}" for c in crit_subset]) if crit_subset else f"  • {card.get('token_prompt_injection', '')[:200]}"
        inval_str = "\n".join([f"  ⛔ {r}" for r in inval_subset]) if inval_subset else ""
        return (
            f"=== INSTITUTIONAL MODEL: {model_name.upper()} ===\n"
            f"CORE ATR SCALE-INVARIANT CRITERIA:\n{crit_str}\n\n"
            f"CRITICAL INVALIDATIONS (MANDATORY VETO):\n{inval_str}"
        )

    base_criteria = card.get("token_prompt_injection", "")
    invals = card.get("invalidation_rules", [])
    if invals:
        inval_str = "\n".join([f"- {r}" for r in invals])
        return f"{base_criteria}\nCRITICAL STRUCTURAL INVALIDATIONS (VETO IF ANY MET):\n{inval_str}"
    return base_criteria


def get_invalidation_rules(setup_name: str) -> list:
    """Returns list of specific structural invalidations for the model."""
    data = _load_data()
    cards = data.get("micro_cards", {})

    s_upper = setup_name.upper()
    if "BREAKER" in s_upper:
        card = cards.get("BREAKER_BLOCK_CONFLUENCE", {})
    elif "INVERSION" in s_upper or "IFVG" in s_upper:
        card = cards.get("INVERSION_FVG", {})
    else:
        card = cards.get("BASELINE_CONFIRMATION", {})

    return card.get("invalidation_rules", [])


def get_model_definition(setup_name: str) -> Dict[str, Any]:
    """Returns full metadata for the model."""
    data = _load_data()
    cards = data.get("micro_cards", {})

    s_upper = setup_name.upper()
    if "BREAKER" in s_upper:
        return cards.get("BREAKER_BLOCK_CONFLUENCE", {})
    elif "INVERSION" in s_upper or "IFVG" in s_upper:
        return cards.get("INVERSION_FVG", {})
    return cards.get("BASELINE_CONFIRMATION", {})
