# app/log_redact.py - mask secrets (SerpApi api_key etc.) in logs. (b) 18/06.
# httpx logs full request URLs incl ?api_key=... -> redact at the httpx logger.
import logging, re

_PATTERNS = [
    re.compile(r"(api_key=)[A-Za-z0-9_\-]+"),
    re.compile(r"(X-API-Key:\s*)\S+", re.I),
]


def _redact(v):
    s = str(v)
    if "api_key" in s.lower():
        for p in _PATTERNS:
            s = p.sub(lambda m: m.group(1) + "***", s)
        return s
    return v


class RedactFilter(logging.Filter):
    def filter(self, record):
        try:
            if isinstance(record.msg, str) and "api_key" in record.msg.lower():
                for p in _PATTERNS:
                    record.msg = p.sub(lambda m: m.group(1) + "***", record.msg)
            if isinstance(record.args, tuple) and record.args:
                record.args = tuple(_redact(a) for a in record.args)
        except Exception:
            pass
        return True


_f = RedactFilter()
for _name in ("", "httpx", "httpcore", "app", "uvicorn", "uvicorn.access"):
    logging.getLogger(_name).addFilter(_f)
