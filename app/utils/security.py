"""Security utilities for masking sensitive data in logs."""
import re
from typing import Optional


def mask_telegram_token(token: str) -> str:
    """Mask a Telegram bot token.

    Telegram tokens look like ``<bot_id>:<secret>``. The numeric bot_id is not
    a credential on its own, so it is kept to make logs debuggable, while the
    secret half is removed entirely.
    """
    if not token:
        return "[MASKED_TOKEN]"
    if ":" in token:
        bot_id, _secret = token.split(":", 1)
        if bot_id.isdigit():
            return f"{bot_id}:[MASKED_SECRET]"
    return "[MASKED_TOKEN]"


def mask_sensitive_url(url: str) -> str:
    """Mask presigned URLs and Telegram bot tokens in URLs.
    
    Examples:
      - https://api.telegram.org/bot1234567890:ABC.../sendMessage
        -> https://api.telegram.org/bot1234567890:ABC....[MASKED]
      - https://r2.example.com/file?X-Amz-Signature=xyz&X-Amz-Algorithm=AWS4-HMAC-SHA256
        -> https://r2.example.com/file?[MASKED_SIGNATURE]
    """
    if not url:
        return "[MASKED_URL]"
    
    # Mask Telegram bot token in URL (pattern: /bot<token>/)
    url = re.sub(
        r'(telegram\.org/bot)([0-9]+:[^/]+)',
        lambda m: f"{m.group(1)}{mask_telegram_token(m.group(2))}",
        url
    )
    
    # Mask AWS presigned URL parameters (X-Amz-Signature, X-Amz-Credential, etc.)
    url = re.sub(
        r'([?&])(X-Amz-Signature|X-Amz-Credential|Authorization)=([^&]+)',
        r'\1\2=[MASKED]',
        url,
        flags=re.IGNORECASE
    )
    
    return url


def mask_exception_text(exception_text: str) -> str:
    """Mask sensitive data in exception/error messages.
    
    Masks:
    - Telegram bot tokens
    - AWS presigned URL signatures
    - OAuth tokens
    """
    if not exception_text:
        return "[MASKED_EXCEPTION]"
    
    # Mask Telegram tokens (format: digits:alphanumeric)
    exception_text = re.sub(
        r'\d{8,}:[a-zA-Z0-9_-]{30,}',
        '[MASKED_TELEGRAM_TOKEN]',
        exception_text
    )
    
    # Mask AWS signature patterns
    exception_text = re.sub(
        r'X-Amz-Signature[=:][\w/+=]+',
        'X-Amz-Signature=[MASKED]',
        exception_text,
        flags=re.IGNORECASE
    )
    
    # Mask presigned URLs
    exception_text = mask_sensitive_url(exception_text)
    
    return exception_text
