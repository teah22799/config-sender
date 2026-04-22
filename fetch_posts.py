import os
import json
from datetime import datetime, timedelta
from dateutil import tz
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]

BASE_DIR = "posts"
RAW_DIR = "posts/raw"
HTML_DIR = "posts/html"
MEDIA_DIR = "posts/media"

for p in [BASE_DIR, RAW_DIR, HTML_DIR, MEDIA_DIR]:
    if not os.path.exists(p):
        os.makedirs(p)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def fetch():
    await client.start()

    with open("channels.txt", "r", encoding="utf-8") as f:
        channels = [line.strip() for line in f if line.strip()]

    cutoff = datetime.now(tz.UTC) - timedelta(days=10)
    channel_index_links = []

    for channel in channels:
        entity = await client.get_entity(channel)
        username = entity.username

        channel_html_path = f"{HTML_DIR}/{username}.html"
        media_path = f"{MEDIA_DIR}/{username}"

        if not os.path.exists(media_path):
            os.makedirs(media_path)

        posts_html = ""
        raw_posts = []

        async for msg in client.iter_messages(entity, limit=200):
            if msg.date < cutoff:
                break

            post_id = f"{username}_{msg.id}"
            raw_path = f"{RAW_DIR}/{post_id}.json"

            raw_data = {
                "channel": username,
                "message_id": msg.id,
                "date": msg.date.isoformat(),
                "text": msg.text or "",
                "link": f"https://t.me/{username}/{msg.id}",
                "media": []
            }

            media_links_html = ""

            if msg.media:
                file_name = f"{post_id}"
                saved_path = os.path.join(media_path, file_name)
                try:
                    saved_file = await msg.download_media(saved_path)
                    if saved_file:
                        github_path = f"{saved_file}".replace("\\", "/")
                        raw_data["media"].append(github_path)

                        media_links_html += f"<p><a href='/{github_path}'>Download media</a></p>"
                except:
                    pass

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)

            posts_html += f"""
            <div style="border:1px solid #ccc; padding:10px; margin-bottom:10px">
                <h3>Post ID: {msg.id}</h3>
                <p>{msg.text}</p>
                <p><a href="https://t.me/{username}/{msg.id}">View source</a></p>
                {media_links_html}
            </div>
            """

        with open(channel_html_path, "w", encoding="utf-8") as f:
            f.write(f"""
            <html><body>
            <h1>Channel: @{username}</h1>
            <p>Telegram: <a href="https://t.me/{username}">https://t.me/{username}</a></p>
            <hr>
            {posts_html}
            </body></html>
            """)

        channel_index_links.append(
            f"<li><a href='posts/html/{username}.html'>@{username}</a></li>"
        )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <html><body>
        <h1>Telegram Channel Archive</h1>
        <ul>
            {''.join(channel_index_links)}
        </ul>
        </body></html>
        """)

with client:
    client.loop.run_until_complete(fetch())
