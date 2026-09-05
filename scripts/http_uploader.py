from http.server import BaseHTTPRequestHandler, HTTPServer
import os, sys

class Uploader(BaseHTTPRequestHandler):
    def do_POST(self):
        fname = os.path.basename(self.path.lstrip('/'))
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        dest = f'/var/vf/episodes/en-byzantine-empire-ep001/assets/raw/{fname}'
        with open(dest, 'wb') as f:
            f.write(data)
        print(f'HTTP Uploader received {fname}: {len(data)} bytes ✅')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, format, *args):
        return

print('Starting HTTP Uploader on 0.0.0.0:8999...')
HTTPServer(('0.0.0.0', 8999), Uploader).serve_forever()
