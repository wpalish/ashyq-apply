"""Loopback-only UI test proxy; arm one lost response with runtime/lost-response.arm.

Use only with the isolated synthetic UI database. It forwards an accepted profile
update, consumes the upstream reply, then drops that one downstream connection.
No request bodies, cookies or authentication headers are written to logs.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection
from pathlib import Path
import socket

ARM = Path(__file__).resolve().parents[5] / 'runtime' / 'lost-response.arm'
HOP = {'connection', 'transfer-encoding', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'upgrade'}
class Proxy(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def forward(self):
        if not self.path.startswith('/api/'):
            self.send_error(404); return
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        upstream = HTTPConnection('127.0.0.1', 18141, timeout=35)
        headers = {key: value for key, value in self.headers.items() if key.lower() not in HOP | {'host'}}
        headers['Host'] = '127.0.0.1:18141'
        try:
            upstream.request(self.command, self.path, body=data or None, headers=headers)
            reply = upstream.getresponse(); body = reply.read()
            drop = self.command == 'PUT' and self.path.startswith('/api/profiles/') and ARM.exists() and 200 <= reply.status < 300
            if drop:
                ARM.unlink(); print('Accepted synthetic profile update; intentionally dropping one response', flush=True)
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
            self.send_response(reply.status)
            for key, value in reply.getheaders():
                if key.lower() not in HOP | {'content-length'}: self.send_header(key, value)
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        finally: upstream.close()
    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = forward
    def log_message(self, *_args): pass
if __name__ == '__main__':
    print('UI test proxy: 127.0.0.1:18143 -> 127.0.0.1:18141; arm path', ARM, flush=True)
    ThreadingHTTPServer(('127.0.0.1', 18143), Proxy).serve_forever()
