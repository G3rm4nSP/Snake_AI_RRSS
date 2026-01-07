# /Triggers/twitch_node.py

import asyncio

def run_twitch_node():
    # 🔁 Crear event loop propio del thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    import os
    import socket
    import json

    TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
    TWITCH_BOT_TOKEN = os.getenv("TWITCH_BOT_TOKEN")

    if not (TWITCH_CHANNEL and TWITCH_BOT_TOKEN):
        print("⚠️ Parámetros de Twitch incompletos, nodo Twitch no se iniciará")
        return

    HOST = os.getenv("TRIGGER_HOST", "127.0.0.1")
    PORT = int(os.getenv("TRIGGER_PORT", "8765"))

    # 🔌 Conectar al nodo central de forma segura
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except Exception as e:
        print(f"❌ No se pudo conectar al nodo central ({HOST}:{PORT}): {e}")
        return

    def send_trigger(key):
        try:
            msg = {"source": "twitch", "key": key}
            sock.sendall((json.dumps(msg) + "\n").encode())
        except Exception as e:
            print(f"⚠️ Error enviando trigger Twitch: {e}")

    # Importes tardíos
    from twitchio.ext import commands
    from triggers_mapping import get_key_from_comment

    class Bot(commands.Bot):
        def __init__(self):
            super().__init__(
                token=TWITCH_BOT_TOKEN,
                prefix="!",
                initial_channels=[TWITCH_CHANNEL]
            )

        async def event_ready(self):
            print(f"🎮 Twitch listo en canal {TWITCH_CHANNEL}")

        async def event_message(self, message):
            if message.echo:
                return

            key = get_key_from_comment(message.content)
            if key is not None:
                send_trigger(key)

    bot = Bot()

    try:
        bot.run()
    finally:
        loop.close()
