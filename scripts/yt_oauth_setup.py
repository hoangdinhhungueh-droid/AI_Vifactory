"""One-time helper to obtain a YouTube OAuth refresh_token (scope youtube.upload).
Stdlib only (no pip installs needed).

RUN IT ON A MACHINE WITH A BROWSER (your laptop is easiest), OR on the VPS via an
SSH tunnel:
    ssh -L 8765:localhost:8765 root@188.40.168.214
    # then inside the VPS:
    YT_OAUTH_CLIENT_ID=xxx YT_OAUTH_CLIENT_SECRET=yyy python3 scripts/yt_oauth_setup.py

It opens Google consent, captures the code on http://localhost:8765, exchanges it,
and prints the 3 env lines to paste into /root/secrets/.env.
"""
import os, sys, json, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

CID = os.getenv("YT_OAUTH_CLIENT_ID") or (sys.argv[1] if len(sys.argv) > 1 else "")
CSEC = os.getenv("YT_OAUTH_CLIENT_SECRET") or (sys.argv[2] if len(sys.argv) > 2 else "")
PORT = int(os.getenv("OAUTH_PORT", "8765"))
SCOPE = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly"
REDIRECT = "http://localhost:" + str(PORT)

if not CID or not CSEC:
    print("Usage: YT_OAUTH_CLIENT_ID=.. YT_OAUTH_CLIENT_SECRET=.. python3 scripts/yt_oauth_setup.py")
    sys.exit(2)

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": CID, "redirect_uri": REDIRECT, "response_type": "code",
    "scope": SCOPE, "access_type": "offline", "prompt": "consent"})

hold = {}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        hold["code"] = params.get("code", [None])[0]
        self.send_response(200); self.end_headers()
        self.wfile.write(b"OK - close this tab and return to the terminal.")

    def log_message(self, *a):
        pass


print("\n1) Open this URL in a browser and approve the YouTube channel:\n\n" + auth_url + "\n")
try:
    webbrowser.open(auth_url)
except Exception:
    pass
srv = HTTPServer(("localhost", PORT), H)
print("Waiting for Google redirect on " + REDIRECT + " ...")
srv.handle_request()
code = hold.get("code")
if not code:
    print("No code received."); sys.exit(1)

data = urllib.parse.urlencode({
    "code": code, "client_id": CID, "client_secret": CSEC,
    "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
with urllib.request.urlopen(req) as r:
    tok = json.loads(r.read())
refresh = tok.get("refresh_token")
if not refresh:
    print("No refresh_token returned. Revoke prior access at "
          "https://myaccount.google.com/permissions then retry (prompt=consent). Raw: " + str(tok))
    sys.exit(1)
print("\n=== SUCCESS - add these 3 lines to /root/secrets/.env ===\n")
print("YT_OAUTH_CLIENT_ID=" + CID)
print("YT_OAUTH_CLIENT_SECRET=" + CSEC)
print("YT_OAUTH_REFRESH_TOKEN=" + refresh)
print("\n(scope granted: youtube.upload)")
