#!/bin/sh
apk add --no-cache busybox-extras > /dev/null 2>&1

python3 -c "
import http.server
import socketserver
import subprocess

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = subprocess.run(
                ['nc', '-z', 'valkey', '6379'],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                status = 200
                msg = b'healthy'
            else:
                status = 503
                msg = b'unhealthy'
        except Exception as e:
            status = 503
            msg = b'unhealthy'
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(msg)

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('', 8080), Handler) as httpd:
    httpd.serve_forever()
"