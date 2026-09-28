#!/bin/sh

python3 -c "
import http.server
import socketserver
import urllib.request
import json
import signal

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            with urllib.request.urlopen('http://redpanda:9644/v1/cluster/health_overview', timeout=5) as response:
                health = json.load(response)
            
            if health.get('is_healthy'):
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