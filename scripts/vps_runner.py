import io
import json
import logging
import os
import ssl
import sys
import time
import urllib.request

logger = logging.getLogger("vps_runner")

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, io.UnsupportedOperation) as _reconf_err:
    logger.debug(f"Stdout reconfigure notice: {_reconf_err}")

def _load_env():
    """Load key-value pairs from .env in repository root if present without external dependencies."""
    from pathlib import Path
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception as _env_err:
            logger.debug(f"Could not load .env: {_env_err}")

_load_env()

DEFAULT_AG_URL = os.getenv("VPS_AG_URL", "https://ag.vifactory.com/mcp")
DEFAULT_AG_TOKEN = os.getenv("VPS_AG_TOKEN")
DEFAULT_MCP2_URL = os.getenv("VPS_MCP2_URL", "https://mcp2.vifactory.com/mcp")
DEFAULT_MCP2_TOKEN = os.getenv("VPS_MCP2_TOKEN")
DEFAULT_CF_ID = os.getenv("CF_ACCESS_CLIENT_ID")
DEFAULT_CF_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET")

# Primary endpoint is MCP2 (index 0), secondary fallback is AG (index 1)
ENDPOINTS = [
    {
        "name": "mcp2",
        "url": DEFAULT_MCP2_URL,
        "token": DEFAULT_MCP2_TOKEN,
        "cf_id": DEFAULT_CF_ID,
        "cf_secret": DEFAULT_CF_SECRET
    },
    {
        "name": "ag",
        "url": DEFAULT_AG_URL,
        "token": DEFAULT_AG_TOKEN,
        "cf_id": DEFAULT_CF_ID,
        "cf_secret": DEFAULT_CF_SECRET
    }
]

class FastVPSClient:
    def __init__(self, endpoint_idx=0, auto_connect=True, endpoints=None):
        self.endpoint_idx = endpoint_idx
        self.endpoints = endpoints if endpoints is not None else ENDPOINTS
        self.ep = self.endpoints[self.endpoint_idx]
        self.url = self.ep["url"]
        self.token = self.ep["token"]
        if not self.ep.get("cf_id") or not self.ep.get("cf_secret"):
            raise RuntimeError(
                "Missing Cloudflare Access credentials! Please set CF_ACCESS_CLIENT_ID and "
                "CF_ACCESS_CLIENT_SECRET in environment or .env file (fail-closed security policy). "
                "Recommendation: If service token credentials were previously exposed in git history, "
                "rotate the Cloudflare Access service token immediately in the Cloudflare Zero Trust dashboard."
            )
        if not self.token:
            raise RuntimeError(
                f"Missing bearer token for endpoint '{self.ep.get('name', self.url)}'! "
                f"Please set VPS_AG_TOKEN or VPS_MCP2_TOKEN in environment or .env file."
            )
        self.session_id = None
        self._req_id = 0
        self.ctx = ssl.create_default_context()
        if os.getenv("ALLOW_INSECURE_TLS", "").lower() in ("1", "true", "yes"):
            logger.warning("INSECURE TLS: Certificate verification disabled via ALLOW_INSECURE_TLS.")
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE
        if auto_connect:
            self.init_session()

    def _headers(self):
        h = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity/2.0"
        }
        if self.ep.get("cf_id"):
            h["CF-Access-Client-Id"] = self.ep["cf_id"]
        if self.ep.get("cf_secret"):
            h["CF-Access-Client-Secret"] = self.ep["cf_secret"]
        if self.session_id:
            h["mcp-session-id"] = self.session_id
        return h

    def close(self):
        self.session_id = None

    def switch_endpoint(self):
        self.endpoint_idx = (self.endpoint_idx + 1) % len(self.endpoints)
        self.ep = self.endpoints[self.endpoint_idx]
        self.url = self.ep["url"]
        self.token = self.ep["token"]
        self.session_id = None
        print(f"[vps_runner] Switching to endpoint {self.url}...", file=sys.stderr)

    def init_session(self, retries=3):
        for attempt in range(retries):
            try:
                self.session_id = None
                self._req_id += 1
                init_payload = {
                    "jsonrpc": "2.0",
                    "id": self._req_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "antigravity", "version": "2.0"}
                    }
                }
                req = urllib.request.Request(
                    self.url,
                    data=json.dumps(init_payload).encode('utf-8'),
                    headers=self._headers(),
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30, context=self.ctx) as resp:
                    self.session_id = resp.headers.get("mcp-session-id")

                if self.session_id:
                    try:
                        notif_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
                        req_notif = urllib.request.Request(
                            self.url,
                            data=json.dumps(notif_payload).encode('utf-8'),
                            headers=self._headers(),
                            method="POST"
                        )
                        with urllib.request.urlopen(req_notif, timeout=15, context=self.ctx) as _resp_notif:
                            _ = _resp_notif.read()
                    except Exception as _notif_err:
                        logger.debug(f"Notifications/initialized notice: {_notif_err}")
                    return self.session_id

            except Exception as e:
                print(f"[vps_runner] init_session attempt {attempt} error on {self.url}: {type(e).__name__}: {e}", file=sys.stderr)
                if len(self.endpoints) > 1:
                    self.switch_endpoint()
                time.sleep(0.1)
                if attempt == retries - 1:
                    raise e
        return self.session_id

    def call_tool(self, tool_name, arguments=None, timeout=300, retries=3):
        for attempt in range(retries):
            try:
                if not self.session_id:
                    self.init_session()
                self._req_id += 1
                payload = {
                    "jsonrpc": "2.0",
                    "id": self._req_id,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments or {}
                    }
                }
                req = urllib.request.Request(
                    self.url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=self._headers(),
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=timeout, context=self.ctx) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    for line in body.splitlines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            res = data.get("result", {})
                            content = res.get("content", [])
                            if content and isinstance(content, list):
                                try:
                                    return json.loads(content[0].get("text", "{}"))
                                except Exception:
                                    return content[0].get("text")
                            return res
                return {}
            except Exception as e:
                time.sleep(1)
                self.init_session()
                if attempt == retries - 1:
                    raise e
        return {}

    def run_command(self, cmd, timeout=300):
        return self.call_tool("run_command", {"command": cmd, "confirm": True, "timeout": timeout}, timeout=timeout)

_client = None

def get_client():
    global _client
    if _client is None:
        _client = FastVPSClient()
    return _client

def run_vps_cmd(cmd, confirm=True, timeout=300):
    return get_client().run_command(cmd, timeout=timeout)

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[-1].isdigit():
        cmd = " ".join(sys.argv[1:-1])
        timeout = int(sys.argv[-1])
    elif len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        timeout = 180
    else:
        cmd = "uname -a"
        timeout = 180
    client = get_client()
    try:
        res = client.run_command(cmd, timeout=timeout)
        if isinstance(res, dict):
            print("STDOUT:\n" + res.get("stdout", ""), flush=True)
            print("STDERR:\n" + res.get("stderr", ""), flush=True)
            print("EXIT_CODE:", res.get("exit_code", 0), flush=True)
        else:
            print(res, flush=True)
    finally:
        client.close()
