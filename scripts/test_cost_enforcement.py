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
    """Test that cost cap is enforced correctly."""
    print("[TEST] Testing cost cap enforcement...")
    
    # Create temporary test database
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_db_path = f.name
    
    try:
        # Create tracker with low cap for testing (1000 VND)
        tracker = CostTracker(cap_vnd=1000, db_path=test_db_path)
        
        # Test 1: Record within budget
        print("[TEST] Recording 500 VND (within budget)...")
        tracker.record("gpt-5.6-sol", 10000, is_image=False)  # 10k tokens * 0.05 VND/token = 500 VND
        print(f"✅ Success. Total: {tracker.get_monthly_total():.2f} VND")
        
        # Test 2: Record another 300 VND (still within budget)
        print("[TEST] Recording another 300 VND (total 800/1000)...")
        tracker.record("gpt-5.6-sol", 6000, is_image=False)  # 6k tokens * 0.05 VND/token = 300 VND
        print(f"✅ Success. Total: {tracker.get_monthly_total():.2f} VND")
        
        # Test 3: Try to exceed budget (should fail)
        print("[TEST] Attempting to record 500 VND (would exceed cap)...")
        try:
            tracker.record("gpt-5.6-sol", 10000, is_image=False)  # Would total 1300 VND > 1000 cap
            print("❌ FAIL: Should have raised CostCapExceededError")
            return False
        except CostCapExceededError as e:
            print(f"✅ SUCCESS: Cost cap enforced correctly")
            print(f"   Error message: {e}")
        
        # Test 4: Verify database persists
        print("[TEST] Verifying database persistence...")
        tracker2 = CostTracker(cap_vnd=1000, db_path=test_db_path)
        total = tracker2.get_monthly_total()
        if abs(total - 800) < 0.01:  # Allow for floating point error
            print(f"✅ SUCCESS: Database persisted correctly ({total:.2f} VND)")
        else:
            print(f"❌ FAIL: Expected 800 VND, got {total:.2f} VND")
            return False
        
        # Test 5: Verify monthly report
        print("[TEST] Checking monthly report...")
        report = tracker2.monthly_report()
        print(f"   Report: {json.dumps(report, indent=2)}")
        
        # Test 6: Budget usage percentage
        usage_pct = tracker2.get_budget_usage_pct()
        print(f"   Budget usage: {usage_pct:.1f}%")
        
        remaining = tracker2.get_remaining_budget()
        print(f"   Remaining: {remaining:.2f} VND")
        
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
        tracker.record("gpt-5.6-sol", 100_000, is_image=False)  # 100k tokens * 0.05 = 5000 VND
        tracker.record("claude-3.5-sonnet", 20_000, is_image=False)  # 20k * 0.15 = 3000 VND
        tracker.record("imagen3", 5, is_image=True)  # 5 images * 5000 = 25000 VND
        
        total = tracker.get_monthly_total()
        expected = 5000 + 3000 + 25000  # 33000 VND
        
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
