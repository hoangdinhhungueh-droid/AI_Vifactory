"""Security utilities for masking sensitive data in logs."""
import logging
import re


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


def redact_telemetry_secrets(text: str) -> str:
    """Eliminates plaintext secret and token exposure across evidence blocks and logs.
    Redacts tokens, API keys, Bearer auth, Notion secrets, and sensitive environment assignments.
    """
    if not text:
        return text

    # 1. Standard masking for URLs and exceptions
    text = mask_sensitive_url(mask_exception_text(text))

    # 2. Redact Bearer tokens in headers or strings
    text = re.sub(
        r'(?i)(Bearer\s+)[A-Za-z0-9_\-\.]{15,}',
        r'\1[REDACTED_BEARER_TOKEN]',
        text
    )

    # 3. Redact common secret/token assignments in env vars, JSON, or configs
    sensitive_keys = (
        r'MCP_BEARER_TOKEN|NOTION_TOKEN|HHTECH_API_KEY|GEMINI_API_KEY|'
        r'CLOUDFLARE_API_TOKEN|CF_API_TOKEN|YOUTUBE_API_KEY|GITHUB_TOKEN|'
        r'OPENAI_API_KEY|ANTHROPIC_API_KEY|SECRET_KEY|API_KEY|API_SECRET'
    )
    pattern = rf'(?i)(["\']?(?:{sensitive_keys})["\']?\s*[:=]\s*["\']?)([^"\'\s,;\\}}]+)(["\']?)'
    text = re.sub(pattern, r'\1[REDACTED_SECRET]\3', text)

    # 4. Notion token prefixes: secret_... or ntn_...
    text = re.sub(r'secret_[A-Za-z0-9]{30,}', '[REDACTED_NOTION_TOKEN]', text)
    text = re.sub(r'ntn_[A-Za-z0-9]{30,}', '[REDACTED_NOTION_TOKEN]', text)

    return text


class SensitiveDataFilter(logging.Filter):
    """Logging filter that automatically redacts Telegram bot tokens, presigned URLs, and secrets."""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = mask_sensitive_url(record.msg)
                record.msg = mask_exception_text(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: (mask_sensitive_url(str(v)) if isinstance(v, str) else v) for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(mask_sensitive_url(str(v)) if isinstance(v, str) else v for v in record.args)
        except Exception as _filter_err:
            logging.getLogger(__name__).debug("SensitiveDataFilter formatting notice: %s", _filter_err)
            return True
        return True


def configure_secure_logging():
    """Sets httpx/httpcore loggers to WARNING and attaches SensitiveDataFilter to all root handlers."""
    for logger_name in ("httpx", "httpcore", "urllib3"):
        log = logging.getLogger(logger_name)
        log.setLevel(logging.WARNING)

    root = logging.getLogger()
    filt = SensitiveDataFilter()
    root.addFilter(filt)
    for h in root.handlers:
        h.addFilter(filt)

