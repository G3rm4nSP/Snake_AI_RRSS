from TikTokLive import TikTokLiveClient
from TikTokLive.events import GiftEvent, LikeEvent, CommentEvent
import threading

# Esta cola la inyecta Snake.py
trigger_queue = None

def init_queue(shared_queue):
    global trigger_queue
    trigger_queue = shared_queue

# ⚠️ CAMBIA ESTO
TIKTOK_USER = "@germansp25"

client = TikTokLiveClient(unique_id=TIKTOK_USER)

# -------- EVENTOS --------

@client.on(GiftEvent)
async def on_gift(event: GiftEvent):
    if trigger_queue is None:
        return

    gift_name = event.gift.name
    amount = event.repeat_count or 1

    print(f"🎁 Gift: {gift_name} x{amount}")

    # Ejemplo de mapeo
    if amount >= 1:
        trigger_queue.put(6)   # crecer
    if amount >= 5:
        trigger_queue.put(5)   # fruta
    if amount >= 10:
        trigger_queue.put(7)  # mina
    if amount >= 50:
        trigger_queue.put(0)  # mega crecer


@client.on(LikeEvent)
async def on_like(event: LikeEvent):
    if trigger_queue is None:
        return

    if event.total_likes % 50 == 0:
        print("❤️ Likes trigger")
        trigger_queue.put(3)  # subir velocidad


@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    if trigger_queue is None:
        return

    text = event.comment.lower()

    if "boom" in text:
        trigger_queue.put(9)
    if "grow" in text:
        trigger_queue.put(6)

# -------- RUNNER --------

def _run():
    print("🎥 Conectando a TikTok Live...")
    client.run()

