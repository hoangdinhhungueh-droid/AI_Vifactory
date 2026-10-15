import io
import json
import os
import ssl
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, io.UnsupportedOperation):
    # Stdout already configured or doesn't support reconfigure
    pass

DEFAULT_MCP2_URL = os.getenv("VPS_MCP2_URL", "https://mcp2.vifactory.com/mcp")
DEFAULT_MCP2_TOKEN = os.getenv("VPS_MCP2_TOKEN", "8kV2nR9pL4mQ7wF3jB6vN1cY8tZ5hD0aS")
DEFAULT_AG_URL = os.getenv("VPS_AG_URL", "https://ag.vifactory.com/mcp")
DEFAULT_AG_TOKEN = os.getenv("VPS_AG_TOKEN", "AG_1GWQeTfEGoSlHSsKcC4rJ8O28wYrTsfj4AR4x7xY")
DEFAULT_CF_ID = os.getenv("CF_ACCESS_CLIENT_ID", "8b08f2a93e3c6b29d726695044d7297b.access")
DEFAULT_CF_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET", "911083c977c4e746f00156fdce8eb6633756cb5a0d815454431869991fac20d6")

ENDPOINTS = [
    {
        "url": DEFAULT_AG_URL,
        "token": DEFAULT_AG_TOKEN,
        "cf_id": DEFAULT_CF_ID,
        "cf_secret": DEFAULT_CF_SECRET
    },
    {
        "url": DEFAULT_MCP2_URL,
        "token": DEFAULT_MCP2_TOKEN,
        "cf_id": None,
        "cf_secret": None
    }
]

class FastVPSClient:
    def __init__(self, endpoint_idx=0):
        self.endpoint_idx = endpoint_idx
        self.ep = ENDPOINTS[self.endpoint_idx]
        self.url = self.ep["url"]
        self.token = self.ep["token"]
        self.session_id = None
        self._req_id = 0
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
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
        self.endpoint_idx = (self.endpoint_idx + 1) % len(ENDPOINTS)
        self.ep = ENDPOINTS[self.endpoint_idx]
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
                with urllib.request.urlopen(req, timeout=10, context=self.ctx) as resp:
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
                    except Exception:
                        pass
                    return self.session_id

            except Exception as e:
                print(f"[vps_runner] init_session attempt {attempt} error on {self.url}: {type(e).__name__}: {e}", file=sys.stderr)
                if len(ENDPOINTS) > 1:
                    self.switch_endpoint()
                time.sleep(1)
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
