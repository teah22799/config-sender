import os
import json
from datetime import datetime, timedelta
from dateutil import tz
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

# paths
BASE_DIR = "posts"
RAW_DIR = "posts/raw"
HTML_SIMPLE_DIR = "posts/html_simple"
HTML_ADV_DIR = "posts/html_advanced"

for p in [BASE_DIR, RAW_DIR, HTML_SIMPLE_DIR, HTML_ADV_DIR]:
    if not os.path.exists(p):
        os.makedirs(p)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def fetch():
    await client.start()

    with open("channels.txt", "r", encoding="utf-8") as f:
        channels = [x.strip() for x in f if x.strip()]

    cutoff = datetime.now(tz.UTC) - timedelta(days=10)

    for channel in channels:
        entity = await client.get_entity(channel)
        async for msg in client.iter_messages(entity, limit=100):
            if msg.date < cutoff:
                break

            post_id = f"{entity.username}_{msg.id}"

            raw_path = f"{RAW_DIR}/{post_id}.json"
            html_simple_path = f"{HTML_SIMPLE_DIR}/{post_id}.html"
            html_adv_path = f"{HTML_ADV_DIR}/{post_id}.html"

            # save raw
            raw_data = {
                "channel": entity.username,
                "message_id": msg.id,
                "date": msg.date.isoformat(),
                "text": msg.text,
                "link": f"https://t.me/{entity.username}/{msg.id}"
            }

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)

            # simple HTML
            with open(html_simple_path, "w", encoding="utf-8") as f:
                f.write(
                    f"<html><body>"
                    f"<h3>Channel: @{entity.username}</h3>"
                    f"<p>{msg.text}</p>"
                    f"<a href='https://t.me/{entity.username}/{msg.id}'>View Source</a>"
                    f"</body></html>"
                )

            # advanced HTML
            with open(html_adv_path, "w", encoding="utf-8") as f:
                f.write(
                    f"<html><head><style>"
                    f"body {{ font-family: sans-serif; padding: 20px; }}"
                    f".card {{ border: 1px solid #ccc; padding: 15px; border-radius: 10px; }}"
                    f".link {{ margin-top: 10px; }}"
                    f"</style></head><body>"
                    f"<div class='card'>"
                    f"<h2>Channel: @{entity.username}</h2>"
                    f"<p>{msg.text}</p>"
                    f"<div class='link'><a href='https://t.me/{entity.username}/{msg.id}'>Open Post</a></div>"
                    f"</div></body></html>"
                )

    # delete old files
    delete_old(RAW_DIR)
    delete_old(HTML_SIMPLE_DIR)
    delete_old(HTML_ADV_DIR)

def delete_old(folder):
    now = datetime.now()
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        if os.path.isfile(path):
            t = datetime.fromtimestamp(os.path.getmtime(path))
            if now - t > timedelta(days=10):
                os.remove(path)

with client:
    client.loop.run_until_complete(fetch())
