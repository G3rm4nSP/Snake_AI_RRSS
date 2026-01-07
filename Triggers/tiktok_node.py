# /Triggers/tiktok_node.py

def run_tiktok_node():
    import os
    import socket
    import json
    from triggers_mapping import get_key_from_comment, get_key_from_donation

    try:
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import CommentEvent, GiftEvent
    except ImportError:
        print("⚠️ TikTokLive no instalado, nodo TikTok no se iniciará")
        return

    # Leer entorno AQUÍ (no en import-time)
    HOST = os.getenv("TRIGGER_HOST", "127.0.0.1")
    PORT = int(os.getenv("TRIGGER_PORT", "8765"))

    # 👇 USAR EL NOMBRE CORRECTO
    TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")

    if not TIKTOK_USERNAME:
        print("⚠️ TIKTOK_USERNAME no definido, nodo TikTok no se iniciará")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

    def send_trigger(key):
        msg = {"source": "tiktok", "key": key}
        sock.sendall((json.dumps(msg) + "\n").encode())

    @client.on(CommentEvent)
    async def on_comment(event):
        key = get_key_from_comment(event.comment)
        if key is not None:
            send_trigger(key)

    @client.on(GiftEvent)
    async def on_gift(event):
        key = get_key_from_donation(event.gift.repeat_count)
        if key is not None:
            send_trigger(key)

    print(f"🎵 Nodo TikTok iniciado para {TIKTOK_USERNAME}")
    client.run()
