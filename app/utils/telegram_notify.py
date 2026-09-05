#!/usr/bin/env python3
"""
Standardized Telegram Notification Helper
Used by all Human Gates (HG1, HG2, HG3) and utility scripts

This is a synchronous wrapper around the async telegram services,
suitable for simple scripts that don't use async/await patterns.

For async code, use app.services.telegram_notify directly.
"""
import requests
import os
import sys
from typing import Optional, List, Dict, Any


def send_telegram(message: str, parse_mode: str = "Markdown") -> dict:
    """
    Send message to VPS Telegram channel (synchronous)
    
    Args:
        message: Text content (max 4096 chars, will be truncated)
        parse_mode: "Markdown" or "HTML" (default: Markdown)
    
    Returns:
        dict: Telegram API response or error dict
        
    Example:
        result = send_telegram("✓ HG1 trend approved: EN_EP0251")
        if result.get("ok"):
            print(f"Sent message ID: {result['result']['message_id']}")
    """
    # Read from VPS environment (standardized)
    bot_token = os.environ.get('VF_TG_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ Missing VF_TG_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return {"ok": False, "error": "Missing credentials"}
    
    # Send via Telegram API
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message[:4096],  # Telegram limit
            "parse_mode": parse_mode
        }, timeout=10)
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            msg_id = result['result']['message_id']
            print(f"✓ Telegram sent: Message ID {msg_id}")
            return result
        else:
            print(f"❌ Telegram API error: {result}", file=sys.stderr)
            return result
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram network error: {e}", file=sys.stderr)
        return {"ok": False, "error": str(e)}


def send_telegram_buttons(message: str, buttons: List[List[Dict[str, str]]]) -> dict:
    """
    Send message with inline keyboard buttons (synchronous)
    
    Args:
        message: Text content
        buttons: List of button rows, each row is list of button dicts
        
    Button format:
        {"text": "Button Label", "callback_data": "action:data"}
        OR {"text": "Button Label", "url": "https://..."}
    
    Example:
        buttons = [
            [{"text": "✅ Approve", "callback_data": "ap:EN_EP0251"}],
            [{"text": "❌ Reject", "callback_data": "rj:EN_EP0251"}]
        ]
        result = send_telegram_buttons("HG1 Approval Required", buttons)
    
    Returns:
        dict: Telegram API response
    """
    bot_token = os.environ.get('VF_TG_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        return {"ok": False, "error": "Missing credentials"}
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": buttons}
        }, timeout=10)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": str(e)}


def is_enabled() -> bool:
    """
    Check if Telegram notifications are configured and enabled
    
    Returns:
        bool: True if credentials are available
    """
    if os.environ.get("TELEGRAM_ENABLED", "").strip() == "0":
        return False
    
    bot_token = os.environ.get('VF_TG_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    return bool(bot_token and chat_id)


# Convenience function for quick testing
def test_connection() -> bool:
    """
    Send a test message to verify Telegram connection
    
    Returns:
        bool: True if test message sent successfully
    """
    result = send_telegram("🔧 [TEST] Telegram notification system online")
    return result.get("ok", False)


if __name__ == "__main__":
    # Smoke test: python3 -m app.utils.telegram_notify
    print("Testing Telegram connection...")
    print(f"Enabled: {is_enabled()}")
    
    if is_enabled():
        success = test_connection()
        print(f"Test message sent: {success}")
        sys.exit(0 if success else 1)
    else:
        print("Telegram not configured (missing VF_TG_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        sys.exit(1)
