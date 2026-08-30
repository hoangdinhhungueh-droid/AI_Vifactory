"""Configure logging to suppress sensitive data exposure.

This module configures Python's logging system to prevent credential leakage
through verbose logs from httpx, urllib3, asyncpg, and other libraries.

Sensitive data that may leak:
- Telegram bot tokens in httpx logs
- Database connection strings in asyncpg logs
- AWS presigned URLs with SigV4 signatures
- API keys in HTTP request headers

Usage:
    from app.utils.logging_config import configure_logging
    configure_logging()

This should be called early in app startup, before any external requests.
"""
import logging


def configure_logging() -> None:
    """Disable verbose logging from libraries that may expose credentials.
    
    Sets the following loggers to WARNING level:
    - httpx: HTTP client (may log request URLs with tokens)
    - httpcore: HTTP transport layer
    - urllib3: HTTP utility library
    - asyncpg: PostgreSQL adapter (may log connection strings)
    - telegram: Telegram API client
    """
    # Suppress httpx INFO logs (which expose full URLs with tokens/API keys)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Suppress urllib3 logs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Suppress asyncpg connection logs (may contain DATABASE_URL)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    
    # Suppress telegram client verbose logs
    logging.getLogger("telegram").setLevel(logging.WARNING)
