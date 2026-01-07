# /Triggers/triggers.py

import threading
from queue import Queue
import socket, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))  # asegura que la carpeta Triggers esté en el path
TRIGGER_PORT = int(os.getenv("TRIGGER_PORT", "8765"))
trigger_queue = Queue()

# ---- Nodo TCP central ----
def handle_client(conn, addr):
    print(f"🔌 Conectado: {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n",1)
                event = json.loads(line)
                key = int(event.get("key",-1))
                source = event.get("source","unknown")
                if 0 <= key <= 10:
                    trigger_queue.put(key)
                    print(f"⚡ Trigger {key} desde {source}")
    except Exception as e:
        print("❌ Error cliente:", e)
    finally:
        conn.close()
        print(f"🔌 Desconectado: {addr}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", TRIGGER_PORT))
    server.listen()
    print(f"🔥 Trigger TCP server listening on {TRIGGER_PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def run_triggers():
    # iniciar nodo central TCP
    threading.Thread(target=start_server, daemon=True).start()

    # iniciar nodos externos
    import twitch_node, tiktok_node, http_node
    threading.Thread(target=twitch_node.run_twitch_node, daemon=True).start()
    threading.Thread(target=tiktok_node.run_tiktok_node, daemon=True).start()
    threading.Thread(target=http_node.run_http_node, daemon=True).start()
