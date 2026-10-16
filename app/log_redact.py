# app/log_redact.py - mask secrets (SerpApi api_key etc.) in logs. (b) 18/06.
# httpx logs full request URLs incl ?api_key=... -> redact at the httpx logger.
import logging
import re

_PATTERNS = [
    re.compile(r"(api_key=)[A-Za-z0-9_\-]+", re.I),
    re.compile(r"(X-API-Key:\s*)\S+", re.I),
    re.compile(r"(bot\d{6,12}:)[A-Za-z0-9_\-]+", re.I),
    re.compile(r"(https?://api\.telegram\.org/bot)[^/\s]+", re.I),
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{15,}", re.I),
]


def _redact(v: object) -> object:
    s = str(v)
    s_lower = s.lower()
    if any(k in s_lower for k in ("api_key", "bot", "bearer", "telegram")):
        for p in _PATTERNS:
            s = p.sub(lambda m: m.group(1) + "***", s)
        return s
    return v


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                msg_lower = record.msg.lower()
                if any(k in msg_lower for k in ("api_key", "bot", "bearer", "telegram")):
                    for p in _PATTERNS:
                        record.msg = p.sub(lambda m: m.group(1) + "***", record.msg)
            if isinstance(record.args, tuple) and record.args:
                record.args = tuple(_redact(a) for a in record.args)
        except Exception:
            pass
        return True


_f = RedactFilter()
for _name in ("", "httpx", "httpcore", "app", "uvicorn", "uvicorn.access"):
    _lg = logging.getLogger(_name)
    _lg.addFilter(_f)

# Explicitly suppress raw request/response line dumping by HTTP clients (Rule 118 & Security)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
