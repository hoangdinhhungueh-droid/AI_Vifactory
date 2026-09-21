"""
QuantFlow Post-Trade Dreaming & Continuous Self-Evolution Engine
================================================================
Implements autonomous post-mortem trade reflection, multi-tier strategy
refinement, dynamic parameter adaptation, and permanent journaling.
"""

from .trade_ledger import TradeLedger
from .adaptive_config import AdaptiveConfig
from .engine import DreamingEngine

__all__ = ["TradeLedger", "AdaptiveConfig", "DreamingEngine"]
