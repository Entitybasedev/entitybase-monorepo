#!/bin/sh
pip install pymysql > /dev/null 2>&1

python3 -c "
import http.server
import socketserver
import pymysql
import os

password = os.getenv('MYSQL_ROOT_PASSWORD', '')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            conn = pymysql.connect(host='mysql', user='root', password=password, connect_timeout=2)
            conn.close()
            status = 200
            msg = b'healthy'
        except:
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
