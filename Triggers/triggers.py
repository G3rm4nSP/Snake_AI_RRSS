# /Triggers/triggers.py

from queue import Queue
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Cola compartida con el juego
trigger_queue = Queue()

# -------- HTTP SERVER --------
class TriggerHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/trigger":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            key = int(data.get("key"))

            if 0 <= key <= 9:
                trigger_queue.put(key)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                raise ValueError

        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"INVALID")

def start_server():
    server = HTTPServer(("0.0.0.0", 8765), TriggerHandler)
    print("🔥 Trigger server listening on port 8765")
    server.serve_forever()

def run_triggers():
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
