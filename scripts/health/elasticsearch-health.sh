#!/bin/sh

python3 -c "
import http.server
import socketserver
import urllib.request
import os

host = os.getenv('ELASTICSEARCH_HOST', 'elasticsearch')
port = os.getenv('ELASTICSEARCH_PORT', '9200')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req = urllib.request.Request(f'http://{host}:{port}/_cluster/health', method='GET')
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
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
