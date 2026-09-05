#!/usr/bin/env python3
"""
vf_cf_auth_service.py — Tiny HTTP auth service for nginx auth_request (Zero Trust, secretless origin).
Listens 127.0.0.1:8902. Receives X-JWT + X-Expected-AUD headers, validates CF Access JWT.
200 = pass, 401 = deny. Run under pm2 with venv python:
  pm2 start /root/video_factory/venv/bin/python --name vf-cf-auth -- /root/video_factory/scripts/vf_cf_auth_service.py
Created 25/08/2026.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, "/root/video_factory/scripts")
from vf_cf_access_validator import validate_token  # noqa: E402

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        jwt_token = self.headers.get("X-JWT", "")
        expected_aud = self.headers.get("X-Expected-AUD", "")
        ok, reason = validate_token(jwt_token, expected_aud)
        self.send_response(200 if ok else 401)
        self.end_headers()
        self.wfile.write(reason.encode())

    def log_message(self, fmt, *args):
        sys.stdout.write("[vf-cf-auth] " + (fmt % args) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8902), Handler).serve_forever()
