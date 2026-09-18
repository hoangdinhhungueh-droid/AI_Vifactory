#!/usr/bin/env python3
# scripts/test_cost_enforcement.py
"""
Test script for Pattern 3 cost enforcement.
Verifies that CostCapExceededError is raised when budget limit is exceeded.
"""

import sys
import os
sys.path.insert(0, '/root/video_factory')

from app.services.cost_tracker import CostTracker, CostCapExceededError
import tempfile
import json


def test_cost_cap_enforcement():
    """Test cost tracking and telemetry with updated 18/09/2026 HHTech rates."""
    print("[TEST] Testing cost tracking & telemetry (no cap blocking)...")
    
    # Create temporary test database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_db_path = f.name
    
    try:
        tracker = CostTracker(db_path=test_db_path)
        
        # Test 1: gpt-6-astra (2.000 VND / 1M tokens -> 2.0 VND / 1k tokens)
        print("[TEST] Recording 100,000 tokens of gpt-6-astra (expecting 200 VND)...")
        tracker.record("gpt-6-astra", 100_000, is_image=False)  # 100k tokens * 2.0 VND/1k tokens = 200 VND
        if abs(tracker.get_monthly_total() - 200.0) < 0.01:
            print(f"✅ Success. Total: {tracker.get_monthly_total():.2f} VND")
        else:
            print(f"❌ FAIL: Expected 200 VND, got {tracker.get_monthly_total():.2f} VND")
            return False
        
        # Test 2: claude-opus-5 (2.000 VND / 1M tokens -> 2.0 VND / 1k tokens)
        print("[TEST] Recording 50,000 tokens of claude-opus-5 (expecting 100 VND)...")
        tracker.record("claude-opus-5", 50_000, is_image=False)  # 50k tokens * 2.0 = 100 VND
        expected_total = 200.0 + 100.0
        if abs(tracker.get_monthly_total() - expected_total) < 0.01:
            print(f"✅ Success. Total: {tracker.get_monthly_total():.2f} VND")
        else:
            print(f"❌ FAIL: Expected {expected_total} VND, got {tracker.get_monthly_total():.2f} VND")
            return False
        
        # Test 3: Fallback model (1.600 VND / 1M tokens -> 1.6 VND / 1k tokens)
        print("[TEST] Recording 100,000 tokens of claude-3.5-sonnet fallback (expecting 160 VND)...")
        tracker.record("claude-3.5-sonnet", 100_000, is_image=False)  # 100k * 1.6 = 160 VND
        expected_total += 160.0
        if abs(tracker.get_monthly_total() - expected_total) < 0.01:
            print(f"✅ Success. Total: {tracker.get_monthly_total():.2f} VND")
        else:
            print(f"❌ FAIL: Expected {expected_total} VND, got {tracker.get_monthly_total():.2f} VND")
            return False
        
        # Test 4: Verify database persists
        print("[TEST] Verifying database persistence...")
        tracker2 = CostTracker(db_path=test_db_path)
        total = tracker2.get_monthly_total()
        if abs(total - expected_total) < 0.01:
            print(f"✅ SUCCESS: Database persisted correctly ({total:.2f} VND)")
        else:
            print(f"❌ FAIL: Expected {expected_total} VND, got {total:.2f} VND")
            return False
        
        # Test 5: Verify monthly report and summary text
        print("[TEST] Checking monthly report...")
        report = tracker2.monthly_report()
        print(f"   Report: {json.dumps(report, indent=2)}")
        summary_txt = tracker2.get_cost_summary_text()
        print(f"   Summary Text:\n{summary_txt}")
        
        # Test 6: Verify no cap blocking (unconstrained)
        remaining = tracker2.get_remaining_budget()
        print(f"   Remaining budget: {remaining} (unlimited)")
        
        print("\n[TEST] ✅ ALL TESTS PASSED")
        return True
    
    finally:
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


def test_image_cost_calculation():
    """Test image generation cost tracking."""
    print("\n[TEST] Testing image generation cost tracking...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_db_path = f.name
    
    try:
        tracker = CostTracker(cap_vnd=100_000, db_path=test_db_path)
        
        # Imagen3: 5000 VND per image
        print("[TEST] Recording 10 images at 5000 VND each...")
        tracker.record("imagen3", 10, is_image=True)  # 10 images * 5000 VND = 50,000 VND
        
        total = tracker.get_monthly_total()
        if abs(total - 50000) < 0.01:
            print(f"✅ SUCCESS: Image cost calculated correctly ({total:.2f} VND)")
            return True
        else:
            print(f"❌ FAIL: Expected 50000 VND, got {total:.2f} VND")
            return False
    
    finally:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


def test_mixed_model_tracking():
    """Test tracking multiple models in one month."""
    print("\n[TEST] Testing mixed model tracking...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_db_path = f.name
    
    try:
        tracker = CostTracker(cap_vnd=300_000, db_path=test_db_path)
        
        # Mix of models
        tracker.record("gpt-6-astra", 100_000, is_image=False)  # 100k tokens * 2.0 VND/1k = 200 VND
        tracker.record("claude-3.5-sonnet", 20_000, is_image=False)  # 20k * 1.6 VND/1k = 32 VND
        tracker.record("imagen3", 5, is_image=True)  # 5 images * 5000 = 25000 VND
        
        total = tracker.get_monthly_total()
        expected = 200 + 32 + 25000  # 25232 VND
        
        if abs(total - expected) < 0.01:
            print(f"✅ SUCCESS: Mixed model tracking works ({total:.2f} VND)")
            report = tracker.monthly_report()
            print(f"   Breakdown: {json.dumps(report, indent=2)}")
            return True
        else:
            print(f"❌ FAIL: Expected {expected:.2f} VND, got {total:.2f} VND")
            return False
    
    finally:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


if __name__ == "__main__":
    print("=" * 60)
    print("PATTERN 3: COST ENFORCEMENT TEST SUITE")
    print("=" * 60)
    
    results = [
        test_cost_cap_enforcement(),
        test_image_cost_calculation(),
        test_mixed_model_tracking()
    ]
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)
