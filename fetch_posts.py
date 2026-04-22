import os
import json
import datetime
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.photos import GetUserPhotosRequest

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION_STRING")

BASE_DIR = "posts"
RAW_DIR = "posts/raw"
HTML_DIR = "posts/html"
POST_PAGES_DIR = "posts/post_pages"
MEDIA_DIR = "posts/media"

GITHUB_USER = "teah22799"
GITHUB_REPO = "config-sender"
GITHUB_BRANCH = "main"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(POST_PAGES_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)


def safe_json(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    return str(o)


def github_media_url(channel, filename):
    return f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/posts/media/{channel}/{filename}"


async def download_channel_profile_photo(client, channel, save_path):
    try:
        photos = await client(GetUserPhotosRequest(
            user_id=channel,
            offset=0,
            max_id=0,
            limit=1
        ))
        if photos.photos:
            await client.download_media(photos.photos[0], save_path)
            return True
    except:
        pass
    return False


async def fetch_channel_posts(client, channel_username):
    channel = await client.get_entity(channel_username)
    channel_name = channel.username or channel.title or channel_username
    print(f"Fetching posts from {channel_name}")

    channel_dir = os.path.join(MEDIA_DIR, channel_name)
    os.makedirs(channel_dir, exist_ok=True)

    profile_photo_path = os.path.join(channel_dir, "profile.jpg")
    await download_channel_profile_photo(client, channel, profile_photo_path)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    limit_date = now - datetime.timedelta(days=10)

    all_posts = []
    offset = 0

    while True:
        history = await client(GetHistoryRequest(
            peer=channel,
            offset_id=offset,
            offset_date=None,
            add_offset=0,
            limit=100,
            max_id=0,
            min_id=0,
            hash=0
        ))

        if not history.messages:
            break

        for msg in history.messages:
            if not msg.date:
                continue

            msg_date = msg.date.replace(tzinfo=datetime.timezone.utc)
            if msg_date < limit_date:
                continue

            post_id = msg.id
            post_text = msg.message or ""
            media_files = []

            if msg.media:
                try:
                    file_name = f"{post_id}.jpg"
                    save_path = os.path.join(channel_dir, file_name)
                    await client.download_media(msg, save_path)
                    media_files.append(file_name)
                except:
                    pass

            all_posts.append({
                "post_id": post_id,
                "text": post_text,
                "date": msg_date.isoformat(),
                "media": media_files,
                "channel": channel_name
            })

        offset = history.messages[-1].id

    raw_path = os.path.join(RAW_DIR, f"{channel_name}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2, default=safe_json)

    return all_posts, profile_photo_path


def generate_post_page(post, channel_name):
    file_name = f"{post['post_id']}.html"
    path = os.path.join(POST_PAGES_DIR, file_name)

    safe_text = post["text"].replace("\n", "<br>")

    media_html = ""
    for m in post["media"]:
        url = github_media_url(channel_name, m)
        media_html += (
            f"<div><img src='{url}' style='max-width:500px;'><br>"
            f"<a href='{url}' target='_blank'>Download File</a></div><br>"
        )

    html = f"""
<html><head><meta charset='utf-8'><title>{channel_name} - {post['post_id']}</title></head>
<body>
<h2>{channel_name}</h2>
<p><b>Date:</b> {post['date']}</p>
<p>{safe_text}</p>
{media_html}
<a href='../html/{channel_name}.html'>Back to channel</a>
</body></html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return file_name


def generate_channel_html(channel_name, profile_path, posts):
    out_path = os.path.join(HTML_DIR, f"{channel_name}.html")

    if os.path.exists(profile_path):
        profile_url = github_media_url(channel_name, "profile.jpg")
    else:
        profile_url = ""

    post_cards = ""

    for post in posts:
        safe_text = post["text"].replace("\n", "<br>")

        media_html = ""
        for m in post["media"]:
            url = github_media_url(channel_name, m)
            media_html += (
                f"<div><img src='{url}' style='max-width:150px;'><br>"
                f"<a href='{url}' target='_blank'>Download</a></div>"
            )

        post_page = f"{post['post_id']}.html"

        card = (
            "<div style='border:1px solid #ccc;padding:10px;margin:10px;border-radius:8px;'>"
            f"<h3>Post {post['post_id']}</h3>"
            f"<p><b>Date:</b> {post['date']}</p>"
            f"<p>{safe_text}</p>"
            f"{media_html}"
            f"<br><a href='../post_pages/{post_page}' target='_blank'>Open Full Page</a>"
            "</div>"
        )

        post_cards += card

    html = (
        "<html><head><meta charset='utf-8'><title>" + channel_name + "</title></head><body>"
        "<div style='display:flex;align-items:center;gap:15px;margin:20px;'>"
        f"<img src='{profile_url}' style='width:60px;height:60px;border-radius:50%;'>"
        f"<h2>{channel_name}</h2>"
        "</div>"
        f"{post_cards}"
        "<a href='../index.html'>Back to Home</a>"
        "</body></html>"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def generate_index(all_channels_posts):
    out_path = "posts/index.html"

    channel_links = ""
    all_posts_html = ""

    for channel_name, posts in all_channels_posts.items():
        channel_links += f"<li><a href='html/{channel_name}.html'>{channel_name}</a></li>"

        for post in posts:
            preview = post["text"][:200].replace("\n", "<br>")
            all_posts_html += (
                "<div style='border:1px solid #aaa;margin:10px;padding:10px;border-radius:8px;'>"
                f"<h3>{channel_name} — Post {post['post_id']}</h3>"
                f"<p><b>Date:</b> {post['date']}</p>"
                f"<p>{preview}...</p>"
                f"<a href='post_pages/{post['post_id']}.html'>Open Post</a>"
                "</div>"
            )

    html = (
        "<html><head><meta charset='utf-8'><title>Telegram Archive</title></head><body>"
        "<h1>Telegram Channels Archive</h1>"
        "<h2>Channels</h2><ul>"
        f"{channel_links}"
        "</ul>"
        "<h2>All Posts</h2>"
        f"{all_posts_html}"
        "</body></html>"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


async def main():
    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()

    with open("channels.txt", "r", encoding="utf-8") as f:
        channels = [c.strip() for c in f.readlines() if c.strip()]

    all_channels_posts = {}

    for c in channels:
        posts, profile_photo = await fetch_channel_posts(client, c)

        for p in posts:
            generate_post_page(p, p["channel"])

        generate_channel_html(posts[0]["channel"], profile_photo, posts)

        all_channels_posts[posts[0]["channel"]] = posts

    generate_index(all_channels_posts)
    print("Completed.")


if __name__ == "__main__":
    asyncio.run(main())
