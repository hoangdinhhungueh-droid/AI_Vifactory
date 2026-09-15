"""
Compatibility forwarder for app.services.telegram_buttons.
Prevents any legacy ImportError if scripts.telegram_buttons is imported.
Canonical implementation lives in app/services/telegram_buttons.py.
"""
from app.services.telegram_buttons import *
