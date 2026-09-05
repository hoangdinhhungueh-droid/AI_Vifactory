#!/usr/bin/env python3
"""
Telegram Human Gate Integration Verification
Tests that HG1 and HG2 can access VPS Telegram credentials
"""
import sys
import os

sys.path.insert(0, "/root/video_factory")

def test_env_credentials():
    """Check VPS environment variables"""
    print("=== VPS Environment Check ===")
    
    vf_token = os.environ.get('VF_TG_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    legacy_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    print(f"VF_TG_BOT_TOKEN: {'SET ({}... chars)'.format(len(vf_token)) if vf_token else 'MISSING'}")
    print(f"TELEGRAM_CHAT_ID: {'SET ({})'.format(chat_id[:5] + '...' if len(chat_id) > 5 else chat_id) if chat_id else 'MISSING'}")
    print(f"TELEGRAM_BOT_TOKEN (legacy): {'SET' if legacy_token else 'NOT SET'}")
    
    return bool(vf_token and chat_id)

def test_telegram_notify_module():
    """Test telegram_notify module can load and read credentials"""
    print("\n=== telegram_notify Module Test ===")
    
    try:
        from app.services import telegram_notify as tn
        
        enabled = tn.is_enabled()
        print(f"telegram_notify.is_enabled(): {enabled}")
        
        # Check token/chat_id without exposing values
        token = tn._token()
        chat = tn._chat_id()
        print(f"telegram_notify._token(): {'OK ({} chars)'.format(len(token)) if token else 'EMPTY'}")
        print(f"telegram_notify._chat_id(): {'OK' if chat else 'EMPTY'}")
        
        return enabled
        
    except Exception as e:
        print(f"ERROR loading telegram_notify: {e}")
        return False

def test_telegram_buttons_module():
    """Test telegram_buttons module can load and read credentials"""
    print("\n=== telegram_buttons Module Test ===")
    
    try:
        from app.services import telegram_buttons as tb
        
        enabled = tb.is_enabled()
        print(f"telegram_buttons.is_enabled(): {enabled}")
        
        # Check token/chat_id without exposing values
        token = tb._token()
        chat = tb._chat_id()
        print(f"telegram_buttons._token(): {'OK ({} chars)'.format(len(token)) if token else 'EMPTY'}")
        print(f"telegram_buttons._chat_id(): {'OK' if chat else 'EMPTY'}")
        
        return enabled
        
    except Exception as e:
        print(f"ERROR loading telegram_buttons: {e}")
        return False

def test_hg1_imports():
    """Test HG1 script can import Telegram dependencies"""
    print("\n=== HG1 Import Test ===")
    
    try:
        # Simulate HG1 imports
        from app.services.telegram_buttons import send_gate2_card
        print("✓ HG1 import success: send_gate2_card")
        return True
        
    except Exception as e:
        print(f"✗ HG1 import failed: {e}")
        return False

def test_hg2_imports():
    """Test HG2 script can import Telegram dependencies"""
    print("\n=== HG2 Import Test ===")
    
    try:
        # Simulate HG2 imports
        from app.services import telegram_buttons as tb
        print("✓ HG2 import success: telegram_buttons")
        
        # Check send_with_buttons exists
        if hasattr(tb, 'send_with_buttons'):
            print("✓ HG2 function exists: send_with_buttons")
            return True
        else:
            print("✗ HG2 missing function: send_with_buttons")
            return False
        
    except Exception as e:
        print(f"✗ HG2 import failed: {e}")
        return False

def main():
    print("Telegram Human Gate Integration Verification")
    print("=" * 60)
    
    results = {
        "env_credentials": test_env_credentials(),
        "telegram_notify": test_telegram_notify_module(),
        "telegram_buttons": test_telegram_buttons_module(),
        "hg1_imports": test_hg1_imports(),
        "hg2_imports": test_hg2_imports(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    
    all_pass = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print("=" * 60)
    
    if all_pass:
        print("✓ ALL TESTS PASSED - HG1/HG2 Telegram integration verified")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Check configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())
