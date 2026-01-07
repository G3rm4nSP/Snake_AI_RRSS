# /Triggers/http_node.py

from http.server import BaseHTTPRequestHandler, HTTPServer
import socket, os, json, threading
from triggers_mapping import get_key_from_comment, get_key_from_donation

HOST = os.getenv("TRIGGER_HOST", "127.0.0.1")
PORT = int(os.getenv("TRIGGER_PORT", "8765"))
HTTP_PORT = int(os.getenv("HTTP_NODE_PORT", "8777"))

def send_trigger(key):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sock.sendall((json.dumps({"source": "local_http","key": key})+"\n").encode())
    sock.close()

class LocalHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
            key = None
            if "comment" in data:
                key = get_key_from_comment(data["comment"])
            elif "donation" in data:
                key = get_key_from_donation(data["donation"])
            if key is not None:
                send_trigger(key)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"INVALID")
        except:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"INVALID")

def run_http_node():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), LocalHandler)
    print(f"🌐 HTTP node listening on {HTTP_PORT}")
    server.serve_forever()
