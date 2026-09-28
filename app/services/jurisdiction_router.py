"""
app/services/jurisdiction_router.py — DYNAMIC JURISDICTION & AUTHORITY ROUTER
Rule 128 (Anti-Semantic Bias) & Rule 130 (Factual Integrity).

Architecture:
  - Dynamically routes ports, customs, and regulatory authorities based on market and locational entities.
  - Prevents geographic cross-jurisdiction mismatches (e.g. Yokohama Port must map to Yokohama Quarantine & Yokohama Customs, NOT Tokyo Customs).
  - ZERO hardcoded single-episode assumptions.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AuthorityContext:
    market: str
    quarantine_authority: Optional[str] = None
    customs_authority: Optional[str] = None
    regulatory_division: Optional[str] = None
    judicial_authority: Optional[str] = None
    port_name: Optional[str] = None


# Canonical Jurisdictional Directory (Factual Geographic SSOT)
_JURISDICTION_REGISTRY: dict[str, dict[str, Any]] = {
    "JP": {
        "ports": {
            "yokohama": {
                "keywords": ["yokohama", "横浜", "横浜港", "横浜検疫所"],
                "port_name": "横浜港 (Yokohama Port)",
                "quarantine": "厚生労働省 横浜検疫所 食品監視課",
                "customs": "財務省 横浜税関",
            },
            "tokyo": {
                "keywords": ["tokyo", "東京", "東京港", "東京税関"],
                "port_name": "東京港 (Tokyo Port)",
                "quarantine": "厚生労働省 東京検疫所",
                "customs": "財務省 東京税関",
            },
            "kobe": {
                "keywords": ["kobe", "神戸", "神戸港"],
                "port_name": "神戸港 (Kobe Port)",
                "quarantine": "厚生労働省 神戸検疫所",
                "customs": "財務省 神戸税関",
            },
            "osaka": {
                "keywords": ["osaka", "大阪", "大阪港"],
                "port_name": "大阪港 (Osaka Port)",
                "quarantine": "厚生労働省 大阪検疫所",
                "customs": "財務省 大阪税関",
            },
            "nagoya": {
                "keywords": ["nagoya", "名古屋", "名古屋港"],
                "port_name": "名古屋港 (Nagoya Port)",
                "quarantine": "厚生労働省 名古屋検疫所",
                "customs": "財務省 名古屋税関",
            }
        },
        "default_quarantine": "厚生労働省 検疫所 食品監視課",
        "default_customs": "財務省 税関",
        "default_judicial": "東京地方裁判所",
    },
    "KR": {
        "ports": {
            "busan": {
                "keywords": ["busan", "부산", "부산항"],
                "port_name": "부산항 (Busan Port)",
                "quarantine": "식품의약품안전처 부산지방식약청",
                "customs": "관세청 부산세관",
            },
            "incheon": {
                "keywords": ["incheon", "인천", "인천항"],
                "port_name": "인천항 (Incheon Port)",
                "quarantine": "식품의약품안전처 경인지방식약청",
                "customs": "관세청 인천세관",
            }
        },
        "default_quarantine": "식품의약품안전처 (MFDS)",
        "default_customs": "관세청 (Korea Customs Service)",
        "default_judicial": "서울중앙지방법원",
    },
    "EN": {
        "ports": {
            "los_angeles": {
                "keywords": ["los angeles", "long beach", "la port"],
                "port_name": "Port of Los Angeles / Long Beach",
                "quarantine": "U.S. Food and Drug Administration (FDA) Import Operations",
                "customs": "U.S. Customs and Border Protection (CBP) Los Angeles",
            },
            "new_york": {
                "keywords": ["new york", "new jersey", "ny port"],
                "port_name": "Port of New York and New Jersey",
                "quarantine": "U.S. FDA Northeast Import District",
                "customs": "U.S. CBP New York Field Operations",
            }
        },
        "default_quarantine": "Regulatory Oversight & Inspection Agency",
        "default_customs": "Border & Customs Enforcement Administration",
        "default_judicial": "Federal District Court",
    }
}


def resolve_jurisdiction(text: str = "", market: str = "EN", metadata: Optional[dict] = None) -> AuthorityContext:
    """Resolve correct regulatory and customs authorities based on text entities and market.
    Guarantees 100% geographic consistency (Rule 130).
    """
    mkt = (market or (metadata.get("market") if metadata else "") or "EN").upper()
    reg = _JURISDICTION_REGISTRY.get(mkt, _JURISDICTION_REGISTRY["EN"])
    t_low = (text or "").lower()

    # Search for port matches
    for port_id, p_info in reg.get("ports", {}).items():
        if any(kw in t_low for kw in p_info["keywords"]):
            return AuthorityContext(
                market=mkt,
                quarantine_authority=p_info["quarantine"],
                customs_authority=p_info["customs"],
                port_name=p_info["port_name"],
                judicial_authority=reg.get("default_judicial")
            )

    # Fallback to general market defaults if no specific port mentioned
    return AuthorityContext(
        market=mkt,
        quarantine_authority=reg.get("default_quarantine"),
        customs_authority=reg.get("default_customs"),
        port_name=None,
        judicial_authority=reg.get("default_judicial")
    )
