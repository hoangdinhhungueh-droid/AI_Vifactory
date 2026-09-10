# app/services/cost_tracker.py
"""
Cost Tracker for VF Pipeline - Pattern 3 Implementation.
Tracks model usage costs for passive telemetry and monthly reporting.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CostCapExceededError(Exception):
    """Retained for backward compatibility. No budget cap is enforced."""
    pass


class CostTracker:
    """
    Tracks model usage costs for passive telemetry.
    
    Storage: /var/vf/cost_tracker.json
    Format: {
        "2026-09": {
            "gpt-6-astra": 15000.00,
            "imagen3": 8000.00,
            "claude-3.5-sonnet": 2000.00
        },
        "2026-08": {...}
    }
    """
    
    # Pricing rates in VND (TODO: Update with actual HHTech/provider rates)
    RATES = {
        # LLM models (VND per 1k tokens)
        "gpt-6-astra": 100.0,          # ~$0.004/1k tokens * 25000 VND/USD (2x Sol rate)
        "claude-3.5-sonnet": 150.0,    # ~$0.006/1k tokens * 25000 VND/USD
        "claude-3-opus": 750.0,        # ~$0.030/1k tokens * 25000 VND/USD
        "claude-opus-5": 50.0,         # HHTech flat rate
        "claude-sonnet-5": 50.0,       # HHTech flat rate
        "kimi-k3": 50.0,               # HHTech flat rate
        
        # Image models (VND per image)
        "imagen3": 5000.0,             # ~$0.20/image * 25000 VND/USD
        "dall-e-3": 10000.0,           # ~$0.40/image * 25000 VND/USD
        
        # Default fallback
        "default": 50.0
    }
    
    def __init__(self, cap_vnd: Optional[int] = None, db_path: Optional[str] = None):
        """
        Initialize cost tracker for passive telemetry.
        
        Args:
            cap_vnd: Optional legacy parameter retained for signature compatibility.
            db_path: Path to cost database JSON file (default: /var/vf/cost_tracker.json)
        """
        self.cap_vnd = cap_vnd
        self.db_path = Path(db_path) if db_path else Path("/var/vf/cost_tracker.json")
        self.costs = self._load()
    
    def record(self, model: str, tokens: int, is_image: bool = False):
        """
        Record token/image usage for passive telemetry without any budget cap blocking.
        
        Args:
            model: Model identifier (e.g., "gpt-6-astra", "imagen3")
            tokens: Token count (for LLMs) or image count (for image models)
            is_image: True if recording image generation, False for LLM tokens
        """
        cost_vnd = self._calculate_cost(model, tokens, is_image)
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Initialize month if needed
        if current_month not in self.costs:
            self.costs[current_month] = {}
        
        # Initialize model if needed
        if model not in self.costs[current_month]:
            self.costs[current_month][model] = 0.0
        
        # Calculate new total
        new_model_cost = self.costs[current_month][model] + cost_vnd
        monthly_total = sum(self.costs[current_month].values()) + cost_vnd
        
        # Record cost (unlimited / passive telemetry)
        self.costs[current_month][model] = new_model_cost
        self._save()
        
        logger.info(
            f"[COST] Recorded {cost_vnd:,.2f} VND for {model} "
            f"({tokens} {'images' if is_image else 'tokens'}). "
            f"Monthly total: {monthly_total:,.2f} VND"
        )
    
    def _calculate_cost(self, model: str, tokens: int, is_image: bool) -> float:
        """Calculate cost in VND."""
        rate = self.RATES.get(model, self.RATES["default"])
        
        if is_image:
            # Image models: rate is per image, tokens = image count
            return rate * tokens
        else:
            # LLM models: rate is per 1k tokens
            return (rate * tokens) / 1000.0
    
    def monthly_report(self, month: Optional[str] = None) -> Dict[str, float]:
        """
        Get cost breakdown for a specific month.
        
        Args:
            month: Month in "YYYY-MM" format (default: current month)
        
        Returns:
            Dictionary of {model: cost_vnd}
        """
        if month is None:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self.costs.get(month, {})
    
    def get_monthly_total(self, month: Optional[str] = None) -> float:
        """Get total cost for a month."""
        report = self.monthly_report(month)
        return sum(report.values())
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget for current month (unlimited)."""
        return float('inf')
    
    def get_budget_usage_pct(self) -> float:
        """Get budget usage percentage for current month (unconstrained)."""
        return 0.0
    
    def _load(self) -> Dict:
        """Load cost database from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[COST] Error loading {self.db_path}: {e}")
                return {}
        return {}
    
    def _save(self):
        """Save cost database to disk."""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with pretty formatting
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.costs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[COST] Error saving {self.db_path}: {e}")


# Singleton instance for global access
_global_tracker: Optional[CostTracker] = None


def get_global_tracker() -> CostTracker:
    """Get or create the global cost tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker()
    return _global_tracker
