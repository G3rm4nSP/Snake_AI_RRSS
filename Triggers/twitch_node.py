# /Triggers/twitch_node.py

import asyncio
import threading
import os
import socket
import json

# Diccionario de triggers (comentarios y donaciones)
from triggers_mapping import get_key_from_comment, get_key_from_donation

def run_twitch_node():
    # Crear un loop de asyncio para este hilo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Leer variables de entorno AQUÍ (no en import-time)
    TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
    TWITCH_BOT_TOKEN = os.getenv("TWITCH_BOT_TOKEN")

    if not (TWITCH_CHANNEL and TWITCH_BOT_TOKEN):
        print("⚠️ Parámetros de Twitch incompletos, nodo Twitch no se iniciará")
        return

    # Conexión al nodo central
    HOST = os.getenv("TRIGGER_HOST", "127.0.0.1")
    PORT = int(os.getenv("TRIGGER_PORT", "8765"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    def send_trigger(key):
        msg = {"source": "twitch", "key": key}
        sock.sendall((json.dumps(msg) + "\n").encode())

    # Importes tardíos
    from twitchio.ext import commands

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
            # Comentarios
            key = get_key_from_comment(message.content)
            if key is not None:
                send_trigger(key)

        async def event_cheer(self, cheer):
            """
            Detecta bits (donaciones)
            """
            username = cheer.user.name
            amount = cheer.bits  # cantidad de bits donados
            print(f"🎉 {username} ha donado {amount} bits")

            # Ajustar escala: multiplica x10 si quieres más “peso” a cada donación
            scaled_amount = amount // 10  # cada 10 bits = 1 unidad de donación

            key = get_key_from_donation(scaled_amount)
            if key is not None:
                send_trigger(key)
                print(f"💰 Trigger activado por bits: {key}")

    bot = Bot()
    bot.run()